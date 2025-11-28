"""
Redis client service - handles only Redis connection management.
"""

import json
from typing import Any, Dict, Optional

import redis.asyncio as redis
from loguru import logger


class RedisClient:
    """Simple Redis client wrapper - only handles connection and basic operations."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._sync_client: Optional[redis.Redis] = None

    async def get_async_client(self) -> redis.Redis:
        """Get async Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url, decode_responses=True, health_check_interval=30
            )
        return self._client

    def get_sync_client(self):
        """Get sync Redis client."""
        if self._sync_client is None:
            import redis as sync_redis

            self._sync_client = sync_redis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._sync_client

    async def set_hash(self, key: str, data: Dict[str, Any], ex: int = 86400) -> bool:
        """Set hash data with expiry - much more efficient than JSON strings."""
        try:
            client = await self.get_async_client()
            # Convert all values to strings for Redis hash storage
            string_data = {
                k: json.dumps(v, default=str) if isinstance(v, (dict, list)) else str(v)
                for k, v in data.items()
            }

            await client.hset(key, mapping=string_data)
            await client.expire(key, ex)
            return True
        except Exception as e:
            logger.error(f"Error setting hash {key}: {e}")
            return False

    async def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """Get hash data - returns dict directly."""
        try:
            client = await self.get_async_client()
            data = await client.hgetall(key)
            if not data:
                return None

            # Convert back from strings, handling JSON fields
            result = {}
            for k, v in data.items():
                try:
                    # Try to parse as JSON first (for dicts/lists)
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not JSON
                    result[k] = v
            return result
        except Exception as e:
            logger.error(f"Error getting hash {key}: {e}")
            return None

    def get_hash_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """Get hash data synchronously."""
        try:
            client = self.get_sync_client()
            data = client.hgetall(key)
            if not data:
                return None

            # Convert back from strings, handling JSON fields
            result = {}
            for k, v in data.items():
                try:
                    # Try to parse as JSON first (for dicts/lists)
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if not JSON
                    result[k] = v
            return result
        except Exception as e:
            logger.error(f"Error getting hash {key}: {e}")
            return None

    async def get_hash_field(self, key: str, field: str) -> Optional[str]:
        """Get single field from hash - very fast for lookups."""
        try:
            client = await self.get_async_client()
            return await client.hget(key, field)
        except Exception as e:
            logger.error(f"Error getting field {field} from hash {key}: {e}")
            return None

    async def set_hash_field(
        self, key: str, field: str, value: Any, ex: int = 86400
    ) -> bool:
        """Set single field in hash."""
        try:
            client = await self.get_async_client()
            str_value = (
                json.dumps(value, default=str)
                if isinstance(value, (dict, list))
                else str(value)
            )
            await client.hset(key, field, str_value)
            await client.expire(key, ex)
            return True
        except Exception as e:
            logger.error(f"Error setting field {field} in hash {key}: {e}")
            return False

    async def set_string(self, key: str, value: str, ex: int = 86400) -> bool:
        """Set string value with expiry."""
        try:
            client = await self.get_async_client()
            await client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            return False

    async def get_string(self, key: str) -> Optional[str]:
        """Get string value."""
        try:
            client = await self.get_async_client()
            return await client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            client = await self.get_async_client()
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking if key {key} exists: {e}")
            return False

    async def pipeline_execute(self, operations):
        """Execute operations in pipeline."""
        try:
            client = await self.get_async_client()
            async with client.pipeline() as pipe:
                for op in operations:
                    await op(pipe)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Error executing pipeline: {e}")
            return False

    async def close(self):
        """Close connections."""
        if self._client:
            await self._client.close()
        if self._sync_client:
            self._sync_client.close()
