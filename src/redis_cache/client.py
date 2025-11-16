"""Redis cache client with async operations."""

import json
from typing import Any

from loguru import logger
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from .config import redis_settings


class RedisCacheClient:
    """Async Redis cache client with key-value operations."""

    def __init__(self, settings=None):
        """Initialize Redis client with connection pool.

        Args:
            settings: Optional RedisCacheSettings instance. Uses global settings if None.
        """
        self._settings = settings or redis_settings
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Create connection pool and Redis client."""
        if self._client is not None:
            logger.warning('Redis client is already connected')
            return

        try:
            self._pool = ConnectionPool.from_url(
                self._settings.get_redis_url(),
                max_connections=self._settings.MAX_CONNECTIONS,
                socket_connect_timeout=self._settings.SOCKET_CONNECT_TIMEOUT,
                socket_timeout=self._settings.SOCKET_TIMEOUT,
                decode_responses=True,  # Automatically decode bytes to str
            )
            self._client = Redis(connection_pool=self._pool)
            # Test connection
            await self._client.ping()
            logger.info(f'Redis cache client connected to {self._settings.HOST}:{self._settings.PORT}')
        except RedisError as e:
            logger.error(f'Failed to connect to Redis: {e}')
            raise

    async def close(self) -> None:
        """Close Redis connection and cleanup."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info('Redis cache client disconnected')
        if self._pool:
            await self._pool.aclose()
            self._pool = None

    # def _make_key(self, key: str) -> str:
    #     """Add prefix to key.

    #     Args:
    #         key: Original key name

    #     Returns:
    #         Prefixed key name
    #     """
    #     return f'{self._settings.KEY_PREFIX}{key}'

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        *,
        serialize: bool = True,
    ) -> bool:
        """Set a key-value pair in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds. Uses default if None.
            serialize: If True, serialize value to JSON

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            final_value = json.dumps(value) if serialize else value
            ttl_seconds = ttl if ttl is not None else self._settings.DEFAULT_TTL

            await self._client.set(key, final_value, ex=ttl_seconds)
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.error(f'Failed to set cache key {key}: {e}')
            return False

    async def get(
        self,
        key: str,
        *,
        deserialize: bool = True,
    ) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key
            deserialize: If True, deserialize JSON value

        Returns:
            Cached value or None if not found
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            value = await self._client.get(key)

            if value is None:
                logger.info(f'Cache MISS: {key}')
                return None

            logger.info(f'Cache HIT: {key}')
            return json.loads(value) if deserialize else value
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f'Failed to get cache key {key}: {e}')
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f'Failed to delete cache key {key}: {e}')
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f'Failed to check cache key {key}: {e}')
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if expiration was set, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.expire(key, ttl)
            logger.debug(f'Cache EXPIRE: {key} (ttl={ttl}s)')
            return result
        except RedisError as e:
            logger.error(f'Failed to set expiration for cache key {key}: {e}')
            return False

    # async def ttl(self, key: str) -> int:
    #     """Get remaining time to live for a key.(key에 대한 만료시간 조회)

    #     Args:
    #         key: Cache key

    #     Returns:
    #         TTL in seconds, -1 if key has no expiration, -2 if key doesn't exist
    #     """
    #     if not self._client:
    #         raise RuntimeError('Redis client not connected. Call connect() first.')

    #     try:
    #         final_key = self._make_key(key)
    #         return await self._client.ttl(final_key)
    #     except RedisError as e:
    #         logger.error(f'Failed to get TTL for cache key {key}: {e}')
    #         return -2

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.(pattern에 해당하는 모든 키 삭제)

        Args:
            pattern: Redis key pattern (e.g., 'user:*')

        Returns:
            Number of keys deleted
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f'Cache CLEAR: deleted {deleted} keys matching {pattern}')
                return deleted
            return 0
        except RedisError as e:
            logger.error(f'Failed to clear cache pattern {pattern}: {e}')
            return 0

    # ============ JSON Data Type Methods ============

    async def json_set(
        self,
        key: str,
        value: Any,
        path: str = '$',
        ttl: int | None = None,
    ) -> bool:
        """Set a value using Redis JSON data type.

        Args:
            key: Cache key
            value: Python object to store (dict, list, etc.)
            path: JSON path (default: '$' for root)
            ttl: Time to live in seconds. Uses default if None.

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            # Use Redis JSON.SET command
            await self._client.json().set(key, path, value)

            # Set TTL if provided
            if ttl is not None:
                await self._client.expire(key, ttl)
            elif self._settings.DEFAULT_TTL:
                await self._client.expire(key, self._settings.DEFAULT_TTL)

            logger.debug(f'JSON SET: {key} at path {path}')
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.error(f'Failed to set JSON key {key}: {e}')
            return False

    async def json_get(
        self,
        key: str,
        path: str = '$',
    ) -> Any | None:
        """Get value using Redis JSON data type.

        Args:
            key: Cache key
            path: JSON path (default: '$' for root)

        Returns:
            Python object or None if not found
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            value = await self._client.json().get(key, path)

            if value is None:
                logger.info(f'JSON Cache MISS: {key}')
                return None

            logger.info(f'JSON Cache HIT: {key}')
            # JSONPath '$' returns a list, get first element if path is '$'
            if path == '$' and isinstance(value, list) and len(value) > 0:
                return value[0]
            return value
        except RedisError as e:
            logger.error(f'Failed to get JSON key {key}: {e}')
            return None

    async def json_mget(
        self,
        keys: list[str],
        path: str = '$',
    ) -> list[Any | None]:
        """Get multiple values using Redis JSON data type.

        Args:
            keys: List of cache keys
            path: JSON path (default: '$' for root)

        Returns:
            List of Python objects or None for keys not found
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            values = await self._client.json().mget(keys, path)

            # JSONPath '$' returns a list, unwrap if needed
            if path == '$':
                return [v[0] if v and isinstance(v, list) and len(v) > 0 else v for v in values]
            return values
        except RedisError as e:
            logger.error(f'Failed to get multiple JSON keys: {e}')
            return [None] * len(keys)

    async def json_delete(
        self,
        key: str,
        path: str = '$',
    ) -> bool:
        """Delete value at path using Redis JSON data type.

        Args:
            key: Cache key
            path: JSON path (default: '$' for root, which deletes the entire key)

        Returns:
            True if deleted, False otherwise
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.json().delete(key, path)
            logger.debug(f'JSON DELETE: {key} at path {path}')
            return result > 0
        except RedisError as e:
            logger.error(f'Failed to delete JSON key {key}: {e}')
            return False

    async def json_arrappend(
        self,
        key: str,
        path: str,
        *values: Any,
    ) -> int | None:
        """Append values to a JSON array.

        Args:
            key: Cache key
            path: JSON path to the array
            values: Values to append

        Returns:
            New length of array or None on error
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.json().arrappend(key, path, *values)
            logger.debug(f'JSON ARRAPPEND: {key} at path {path}')
            # Result is a list of lengths for each matched path
            return result[0] if isinstance(result, list) and len(result) > 0 else result
        except RedisError as e:
            logger.error(f'Failed to append to JSON array {key}: {e}')
            return None

    async def json_objkeys(
        self,
        key: str,
        path: str = '$',
    ) -> list[str] | None:
        """Get keys of a JSON object.

        Args:
            key: Cache key
            path: JSON path to the object

        Returns:
            List of keys or None on error
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.json().objkeys(key, path)
            # Result is a list of key lists for each matched path
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
        except RedisError as e:
            logger.error(f'Failed to get JSON object keys {key}: {e}')
            return None

    async def json_type(
        self,
        key: str,
        path: str = '$',
    ) -> str | None:
        """Get the type of value at path.

        Args:
            key: Cache key
            path: JSON path

        Returns:
            Type name ('object', 'array', 'string', 'number', 'boolean', 'null') or None
        """
        if not self._client:
            raise RuntimeError('Redis client not connected. Call connect() first.')

        try:
            result = await self._client.json().type(key, path)
            # Result is a list of types for each matched path
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
        except RedisError as e:
            logger.error(f'Failed to get JSON type {key}: {e}')
            return None

    # ============ End of JSON Methods ============

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
