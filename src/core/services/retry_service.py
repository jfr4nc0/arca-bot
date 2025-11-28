"""
Retry service for handling failed transactions due to retryable errors.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger

from core.logging import clear_exchange_id, set_exchange_id
from core.orchestrator import WorkflowOrchestrator
from core.services.transaction_service import TransactionService
from core.utils.error_classifier import has_retryable_error, is_retryable_error
from core.workflows.base import WorkflowStatus


class RetryService:
    """Service for retrying failed transactions with retryable errors."""

    def __init__(
        self,
        transaction_service: TransactionService,
        workflow_orchestrator: WorkflowOrchestrator,
    ):
        """
        Initialize retry service.

        Args:
            transaction_service: Transaction service instance
            workflow_orchestrator: Workflow orchestrator instance
        """
        self.transaction_service = transaction_service
        self.workflow_orchestrator = workflow_orchestrator

    async def get_retryable_transactions(
        self, max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions with retryable failures that haven't exceeded max retries.

        Args:
            max_retries: Maximum number of retry attempts allowed

        Returns:
            List of retryable transactions
        """
        retryable_transactions = []

        try:
            # If using Redis, we need to scan all transaction keys
            if self.transaction_service._redis_client:
                retryable_transactions = await self._get_retryable_transactions_redis(
                    max_retries
                )
            else:
                # For in-memory storage, check all transactions
                retryable_transactions = self._get_retryable_transactions_memory(
                    max_retries
                )

        except Exception as e:
            logger.error(f"Error getting retryable transactions: {e}")

        return retryable_transactions

    def _get_retryable_transactions_memory(
        self, max_retries: int
    ) -> List[Dict[str, Any]]:
        """Get retryable transactions from in-memory storage."""
        retryable_transactions = []

        for (
            exchange_id,
            transaction_data,
        ) in self.transaction_service._transactions.items():
            if self._is_transaction_retryable(transaction_data, max_retries):
                retryable_transactions.append(
                    {"exchange_id": exchange_id, "data": transaction_data}
                )

        return retryable_transactions

    async def _get_retryable_transactions_redis(
        self, max_retries: int
    ) -> List[Dict[str, Any]]:
        """Get retryable transactions from Redis storage."""
        retryable_transactions = []

        try:
            # Get all transaction keys
            pattern = "transaction:*"
            keys = await self.transaction_service._redis_client.keys(pattern)

            # Check each transaction
            for key in keys:
                transaction_data = (
                    await self.transaction_service._redis_client.get_hash(key)
                )
                if transaction_data:
                    exchange_id = key.replace("transaction:", "")
                    if self._is_transaction_retryable(transaction_data, max_retries):
                        retryable_transactions.append(
                            {"exchange_id": exchange_id, "data": transaction_data}
                        )
        except Exception as e:
            logger.error(f"Error scanning Redis for retryable transactions: {e}")

        return retryable_transactions

    def _is_transaction_retryable(
        self, transaction_data: Dict[str, Any], max_retries: int
    ) -> bool:
        """
        Check if a transaction is retryable.

        Args:
            transaction_data: Transaction data dictionary
            max_retries: Maximum retry attempts allowed

        Returns:
            bool: True if transaction is retryable, False otherwise
        """
        # Check if transaction is in failed status
        status = transaction_data.get("status")
        if status != WorkflowStatus.FAILED.value:
            return False

        # Check retry count
        retry_count = transaction_data.get("retry_count", 0)
        if retry_count >= max_retries:
            return False

        # Check if any error is retryable
        results = transaction_data.get("results", {})
        errors = results.get("errors", {})

        return has_retryable_error(errors)

    async def retry_transaction(self, exchange_id: str) -> bool:
        """
        Retry a specific transaction.

        Args:
            exchange_id: Exchange ID of transaction to retry

        Returns:
            bool: True if retry was initiated successfully, False otherwise
        """
        set_exchange_id(exchange_id)
        try:
            # Get transaction data
            transaction_data = self.transaction_service.get_transaction(exchange_id)
            if not transaction_data:
                logger.warning(f"Transaction {exchange_id} not found")
                return False

            # Increment retry count
            retry_count = transaction_data.get("retry_count", 0) + 1

            # Update transaction with new retry count
            await self.transaction_service.update_status(
                exchange_id=exchange_id,
                status=WorkflowStatus.PENDING.value,
                results={"retry_count": retry_count},
            )

            # Get original request data to recreate workflow
            request_data = transaction_data.get("request_data", {})

            # Extract workflow type from transaction data or infer from exchange_id
            # This would need to be enhanced based on how you track workflow types
            workflow_type = self._infer_workflow_type(exchange_id, transaction_data)

            if not workflow_type:
                logger.error(
                    f"Could not determine workflow type for transaction {exchange_id}"
                )
                return False

            # Extract workflow parameters
            workflow_params = self._extract_workflow_params(request_data, workflow_type)

            # Execute workflow asynchronously
            success = await self.workflow_orchestrator.execute_workflow_async(
                workflow_type=workflow_type,
                workflow_params=workflow_params,
                exchange_id=UUID(exchange_id),
            )

            if success:
                logger.info(
                    f"Retry initiated successfully for transaction {exchange_id}"
                )
                return True
            else:
                logger.error(f"Failed to initiate retry for transaction {exchange_id}")
                return False

        except Exception as e:
            logger.error(f"Error retrying transaction {exchange_id}: {e}")
            return False
        finally:
            clear_exchange_id()

    def _infer_workflow_type(
        self, exchange_id: str, transaction_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Infer workflow type from transaction data.

        Args:
            exchange_id: Exchange ID
            transaction_data: Transaction data

        Returns:
            Workflow type or None if cannot be determined
        """
        # This is a simplified implementation
        # In a real implementation, you might store the workflow type explicitly
        request_data = transaction_data.get("request_data", {})

        # Check for CCMA workflow indicators
        if "data" in request_data and "period_from" in request_data["data"]:
            return "ccma_workflow"

        # Check for DDJJ workflow indicators
        if "data" in request_data and "entries" in request_data["data"]:
            return "ddjj_workflow"

        return None

    def _extract_workflow_params(
        self, request_data: Dict[str, Any], workflow_type: str
    ) -> Dict[str, Any]:
        """
        Extract workflow parameters from request data.

        Args:
            request_data: Request data dictionary
            workflow_type: Type of workflow

        Returns:
            Dictionary of workflow parameters
        """
        params = {}

        if workflow_type == "ccma_workflow":
            # Extract CCMA parameters
            credentials = request_data.get("credentials", {})
            data = request_data.get("data", {})

            params.update(
                {
                    "cuit": credentials.get("cuit"),
                    "password": credentials.get("password"),
                    "period_from": data.get("period_from"),
                    "period_to": data.get("period_to"),
                    "calculation_date": data.get("calculation_date"),
                    "tipo_contribuyente": data.get("tipo_contribuyente"),
                    "impuesto": data.get("impuesto"),
                    "form_payment": data.get("form_payment"),
                    "headless": data.get("headless", False),
                }
            )

        elif workflow_type == "ddjj_workflow":
            # Extract DDJJ parameters
            credentials = request_data.get("credentials", {})
            data = request_data.get("data", {})

            params.update(
                {
                    "cuit": credentials.get("cuit"),
                    "password": credentials.get("password"),
                    "vep_data": data.get("entries", []),
                    "form_payment": data.get("form_payment"),
                    "headless": data.get("headless", False),
                }
            )

        return {k: v for k, v in params.items() if v is not None}

    async def process_retryable_transactions(
        self, max_retries: int = 3
    ) -> Dict[str, int]:
        """
        Process all retryable transactions.

        Args:
            max_retries: Maximum number of retry attempts allowed

        Returns:
            Dictionary with processing statistics
        """
        stats = {"total_found": 0, "retry_initiated": 0, "retry_failed": 0}

        try:
            # Get retryable transactions
            retryable_transactions = await self.get_retryable_transactions(max_retries)
            stats["total_found"] = len(retryable_transactions)

            logger.info(f"Found {stats['total_found']} retryable transactions")

            # Process each transaction
            for transaction in retryable_transactions:
                exchange_id = transaction["exchange_id"]

                try:
                    success = await self.retry_transaction(exchange_id)
                    if success:
                        stats["retry_initiated"] += 1
                    else:
                        stats["retry_failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing transaction {exchange_id}: {e}")
                    stats["retry_failed"] += 1

        except Exception as e:
            logger.error(f"Error processing retryable transactions: {e}")

        return stats
