"""
Transaction service for core business logic.
Responsible only for transaction management and storage.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger

from core.observability import record_transaction_operation
from core.workflows.base import WorkflowStatus


class TransactionService:
    """
    Core transaction management service.

    Responsibilities:
    - Store and retrieve transaction data
    - Check for duplicate transactions
    - Track workflow running state
    - Handle both Redis and in-memory storage
    """

    def __init__(self, redis_url: Optional[str] = None, use_redis: bool = False):
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None

        # Initialize Redis if enabled
        if use_redis and redis_url:
            try:
                from core.infrastructure.redis_client import RedisClient

                self._redis_client = RedisClient(redis_url)
                logger.info("Using Redis for transaction storage")
            except Exception as e:
                logger.warning(f"Redis failed, using memory: {e}")
                self._redis_client = None
        else:
            logger.info("Using in-memory transaction storage")

    async def check_duplicate(self, transaction_hash: str) -> Optional[str]:
        """Check if transaction hash already exists. Returns exchange_id if found."""

        if self._redis_client:
            try:
                # Use hash lookup for fast indexing
                existing_id = await self._redis_client.get_hash_field(
                    "transaction_hashes", transaction_hash
                )
                if existing_id:
                    # Record duplicate transaction metric
                    record_transaction_operation("duplicate_check", "duplicate")
                else:
                    # Record successful duplicate check metric
                    record_transaction_operation("duplicate_check", "success")
                return existing_id
            except Exception as e:
                logger.error(f"Redis error checking duplicate: {e}")
                return None
        else:
            # Memory storage
            for exchange_id, data in self._transactions.items():
                if data.get("transaction_hash") == transaction_hash:
                    # Record duplicate transaction metric
                    record_transaction_operation("duplicate_check", "duplicate")
                    return exchange_id
            # Record successful duplicate check metric
            record_transaction_operation("duplicate_check", "success")
            return None

    async def create_transaction(
        self,
        exchange_id: str,
        transaction_hash: str,
        request_data: Dict[str, Any],
        ttl_seconds: int,
    ) -> bool:
        """Create new transaction record."""

        transaction_data = {
            "status": WorkflowStatus.CREATED.value,
            "transaction_hash": transaction_hash,
            "exchange_id": exchange_id,
            "created_at": datetime.now().isoformat(),
            "request_data": request_data,
            "ttl_seconds": ttl_seconds,  # Store original TTL for later use
        }

        if self._redis_client:
            try:
                # Use pipeline for atomic operations
                async def pipeline_ops(pipe):
                    # Store transaction data as hash
                    await pipe.hset(
                        f"transaction:{exchange_id}",
                        mapping={
                            k: (
                                json.dumps(v, default=str)
                                if isinstance(v, dict)
                                else str(v)
                            )
                            for k, v in transaction_data.items()
                        },
                    )
                    await pipe.expire(f"transaction:{exchange_id}", ttl_seconds)

                    # Store hash->exchange_id mapping
                    await pipe.hset("transaction_hashes", transaction_hash, exchange_id)
                    await pipe.expire("transaction_hashes", ttl_seconds)

                success = await self._redis_client.pipeline_execute([pipeline_ops])
                if success:
                    # Record transaction creation success metric
                    record_transaction_operation("creation", "success")
                else:
                    # Record transaction creation failure metric
                    record_transaction_operation("creation", "failed")
                return success
            except Exception as e:
                logger.error(f"Redis error creating transaction: {e}")
                return False
        else:
            self._transactions[exchange_id] = transaction_data
            # Record transaction creation success metric
            record_transaction_operation("creation", "success")
            return True

    async def update_status(
        self, exchange_id: str, status: str, results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update transaction status and optionally add results."""
        if self._redis_client:
            try:
                # Check if transaction exists first
                key_exists = await self._redis_client.exists(
                    f"transaction:{exchange_id}"
                )
                logger.info(f"Transaction {exchange_id} key exists: {key_exists}")
                if not key_exists:
                    logger.warning(f"Transaction {exchange_id} not found in Redis")
                    return False

                # Get existing data for TTL and result merging
                existing_data = await self._redis_client.get_hash(
                    f"transaction:{exchange_id}"
                )

                # Update fields directly in hash
                updates = {"status": status, "updated_at": datetime.now().isoformat()}
                if results:
                    # Merge results with existing results to preserve retry count
                    existing_results = {}
                    if "results" in existing_data:
                        try:
                            existing_results = json.loads(existing_data["results"])
                        except (json.JSONDecodeError, TypeError):
                            pass

                    # Merge new results with existing results
                    merged_results = {**existing_results, **results}
                    updates["results"] = json.dumps(merged_results, default=str)

                logger.info(f"Updating transaction {exchange_id} with: {updates}")

                # Use stored TTL from creation
                ttl_seconds = int(existing_data.get("ttl_seconds", 3600))

                # Use pipeline for atomic updates
                async def pipeline_ops(pipe):
                    for field, value in updates.items():
                        await pipe.hset(f"transaction:{exchange_id}", field, value)
                    await pipe.expire(f"transaction:{exchange_id}", ttl_seconds)

                success = await self._redis_client.pipeline_execute([pipeline_ops])
                logger.info(f"Redis update success for {exchange_id}: {success}")
                return success
            except Exception as e:
                logger.error(f"Redis error updating status: {e}")
                return False
        else:
            if exchange_id in self._transactions:
                self._transactions[exchange_id]["status"] = status
                if results:
                    # Merge results with existing results to preserve retry count
                    existing_results = self._transactions[exchange_id].get(
                        "results", {}
                    )
                    merged_results = {**existing_results, **results}
                    self._transactions[exchange_id]["results"] = merged_results
                self._transactions[exchange_id][
                    "updated_at"
                ] = datetime.now().isoformat()
                return True
            return False

    def get_transaction(self, exchange_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by exchange_id (sync method for status endpoints)."""
        if self._redis_client:
            try:
                return self._redis_client.get_hash_sync(f"transaction:{exchange_id}")
            except Exception as e:
                logger.error(f"Redis error getting transaction: {e}")
                return None
        else:
            return self._transactions.get(exchange_id)

    async def set_workflow_status(self, exchange_id: str, status: WorkflowStatus):
        """Update workflow status - persisted in Redis/storage."""
        await self.update_status(exchange_id, status.value)

    def is_workflow_running(self, exchange_id: str) -> bool:
        """Check if workflow is currently running based on persisted status."""
        transaction_data = self.get_transaction(exchange_id)
        if not transaction_data:
            return False

        current_status = transaction_data.get("status", "")
        return current_status == WorkflowStatus.RUNNING.value

    async def cleanup(self):
        """Cleanup resources."""
        if self._redis_client:
            await self._redis_client.close()

    async def get_transactions_by_status(
        self, status: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all transactions with a specific status.

        Args:
            status: Status to filter by

        Returns:
            Dictionary of transactions with the specified status
        """
        matching_transactions = {}

        if self._redis_client:
            try:
                # Get all transaction keys
                pattern = "transaction:*"
                keys = await self._redis_client.keys(pattern)

                # Check each transaction
                for key in keys:
                    transaction_data = await self._redis_client.get_hash(key)
                    if transaction_data and transaction_data.get("status") == status:
                        exchange_id = key.replace("transaction:", "")
                        matching_transactions[exchange_id] = transaction_data
            except Exception as e:
                logger.error(f"Error getting transactions by status: {e}")
        else:
            # For in-memory storage
            for exchange_id, transaction_data in self._transactions.items():
                if transaction_data.get("status") == status:
                    matching_transactions[exchange_id] = transaction_data

        return matching_transactions
