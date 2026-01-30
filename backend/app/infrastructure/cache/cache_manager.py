# File: backend/app/infrastructure/cache/cache_manager.py
# Purpose: Cache manager for LLM responses and general caching with Redis
import json
import hashlib
import time
import fnmatch
from typing import Any, Optional, Union
from redis.asyncio import Redis
import structlog

logger = structlog.get_logger(__name__)


class CacheManager:
    """
    Production-grade cache manager with Redis backend.
    Supports LLM response caching, session caching, and general key-value caching.
    """
    
    def __init__(self, redis_client: Optional[Redis], default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Async Redis client instance
            default_ttl: Default TTL in seconds (default 1 hour)
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self._memory_store: dict[str, tuple[str, Optional[float]]] = {}
        self._memory_enabled = redis_client is None
        if self._memory_enabled:
            logger.warning("cache_fallback_in_memory_enabled")
    
    def _generate_key(self, prefix: str, *args: Any) -> str:
        """
        Generate cache key from prefix and arguments.
        Uses MD5 hash for consistent key generation.
        
        Args:
            prefix: Key prefix (e.g., 'llm', 'session', 'user')
            *args: Arguments to include in key
        
        Returns:
            Generated cache key
        """
        # Serialize arguments to JSON for consistent hashing
        key_data = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
        hash_suffix = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_suffix}"

    def _now(self) -> float:
        return time.time()

    def _get_memory(self, key: str) -> Optional[str]:
        item = self._memory_store.get(key)
        if not item:
            return None
        value, expire_at = item
        if expire_at is not None and expire_at <= self._now():
            self._memory_store.pop(key, None)
            return None
        return value

    def _set_memory(self, key: str, value: str, ttl: Optional[int]) -> bool:
        expire_at = self._now() + ttl if ttl else None
        self._memory_store[key] = (value, expire_at)
        return True

    def _delete_memory(self, key: str) -> bool:
        return self._memory_store.pop(key, None) is not None

    def _exists_memory(self, key: str) -> bool:
        return self._get_memory(key) is not None

    def _expire_memory(self, key: str, ttl: int) -> bool:
        value = self._get_memory(key)
        if value is None:
            return False
        self._memory_store[key] = (value, self._now() + ttl)
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        if self._memory_enabled:
            value = self._get_memory(key)
            if value:
                logger.debug("cache_hit", key=key)
                return value
            logger.debug("cache_miss", key=key)
            return None
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return value
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        
        Returns:
            True if set successfully, False otherwise
        """
        try:
            ttl = ttl or self.default_ttl
            if self._memory_enabled:
                result = self._set_memory(key, value, ttl)
            elif nx:
                result = await self.redis.set(key, value, ex=ttl, nx=True)
            elif xx:
                result = await self.redis.set(key, value, ex=ttl, xx=True)
            else:
                result = await self.redis.setex(key, ttl, value)
            if result:
                logger.debug("cache_set", key=key, ttl=ttl)
            return bool(result)
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            if self._memory_enabled:
                result = self._delete_memory(key)
                if result:
                    logger.debug("cache_delete", key=key)
                return result
            result = await self.redis.delete(key)
            if result:
                logger.debug("cache_delete", key=key)
            return result > 0
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if exists, False otherwise
        """
        try:
            if self._memory_enabled:
                return self._exists_memory(key)
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error("cache_exists_error", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
        
        Returns:
            True if expiration set, False otherwise
        """
        try:
            if self._memory_enabled:
                return self._expire_memory(key, ttl)
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error("cache_expire_error", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter.
        
        Args:
            key: Cache key
            amount: Amount to increment by
        
        Returns:
            New value after increment, or None on error
        """
        try:
            if self._memory_enabled:
                current = self._get_memory(key)
                if current is None:
                    new_value = amount
                else:
                    try:
                        new_value = int(current) + amount
                    except (TypeError, ValueError):
                        return None
                self._set_memory(key, str(new_value), None)
                return new_value
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error("cache_increment_error", key=key, error=str(e))
            return None
    
    async def get_many(self, keys: list[str]) -> dict[str, Optional[str]]:
        """
        Get multiple values at once.
        
        Args:
            keys: List of cache keys
        
        Returns:
            Dictionary of key-value pairs
        """
        try:
            if self._memory_enabled:
                return {key: self._get_memory(key) for key in keys}
            values = await self.redis.mget(keys)
            return {key: value for key, value in zip(keys, values)}
        except Exception as e:
            logger.error("cache_get_many_error", error=str(e))
            return {key: None for key in keys}
    
    async def set_many(self, mapping: dict[str, str], ttl: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs at once.
        
        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds
        
        Returns:
            True if all set successfully
        """
        try:
            if self._memory_enabled:
                for key, value in mapping.items():
                    self._set_memory(key, value, ttl or self.default_ttl)
                return True
            # Use pipeline for efficiency
            async with self.redis.pipeline() as pipe:
                for key, value in mapping.items():
                    pipe.setex(key, ttl or self.default_ttl, value)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error("cache_set_many_error", error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., 'llm:*')
        
        Returns:
            Number of keys deleted
        """
        try:
            if self._memory_enabled:
                keys = [key for key in self._memory_store.keys() if fnmatch.fnmatch(key, pattern)]
                deleted = 0
                for key in keys:
                    if self._delete_memory(key):
                        deleted += 1
                if deleted:
                    logger.info("cache_pattern_deleted", pattern=pattern, count=deleted)
                return deleted
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info("cache_pattern_deleted", pattern=pattern, count=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("cache_delete_pattern_error", pattern=pattern, error=str(e))
            return 0
    
    # LLM-specific caching methods
    
    def llm_cache_key(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate cache key for LLM responses.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            temperature: Temperature parameter
            **kwargs: Additional parameters
        
        Returns:
            Cache key for LLM response
        """
        # Include all parameters that affect the response
        cache_params = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            **kwargs
        }
        return self._generate_key("llm", cache_params)
    
    async def get_llm_response(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[dict]:
        """
        Get cached LLM response.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            temperature: Temperature parameter
            **kwargs: Additional parameters
        
        Returns:
            Cached response dictionary or None
        """
        key = self.llm_cache_key(messages, model, temperature, **kwargs)
        cached = await self.get(key)
        
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.error("llm_cache_decode_error", key=key)
                await self.delete(key)  # Remove corrupted cache
                return None
        return None
    
    async def set_llm_response(
        self,
        messages: list[dict],
        model: str,
        response: dict,
        temperature: float = 0.7,
        ttl: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Cache LLM response.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            response: Response dictionary to cache
            temperature: Temperature parameter
            ttl: Time to live in seconds
            **kwargs: Additional parameters
        
        Returns:
            True if cached successfully
        """
        key = self.llm_cache_key(messages, model, temperature, **kwargs)
        value = json.dumps(response, ensure_ascii=False)
        return await self.set(key, value, ttl=ttl)
    
    # Session-specific caching methods
    
    def session_cache_key(self, user_id: str, session_id: str) -> str:
        """Generate cache key for session data"""
        return f"session:{user_id}:{session_id}"
    
    async def get_session(self, user_id: str, session_id: str) -> Optional[dict]:
        """Get cached session data"""
        key = self.session_cache_key(user_id, session_id)
        cached = await self.get(key)
        
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.error("session_cache_decode_error", key=key)
                await self.delete(key)
                return None
        return None
    
    async def set_session(
        self,
        user_id: str,
        session_id: str,
        session_data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache session data"""
        key = self.session_cache_key(user_id, session_id)
        value = json.dumps(session_data, ensure_ascii=False)
        return await self.set(key, value, ttl=ttl)
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        pattern = f"session:{user_id}:*"
        return await self.delete_pattern(pattern)
    
    # User path caching methods
    
    def user_paths_cache_key(self, user_id: str) -> str:
        """Generate cache key for user paths"""
        return f"user_paths:{user_id}"
    
    async def get_user_paths(self, user_id: str) -> Optional[list[str]]:
        """Get cached user paths"""
        key = self.user_paths_cache_key(user_id)
        cached = await self.get(key)
        
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.error("user_paths_cache_decode_error", key=key)
                await self.delete(key)
                return None
        return None
    
    async def set_user_paths(
        self,
        user_id: str,
        paths: list[str],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache user paths"""
        key = self.user_paths_cache_key(user_id)
        value = json.dumps(paths, ensure_ascii=False)
        return await self.set(key, value, ttl=ttl or 3600)  # 1 hour default
    
    # Health check
    
    async def health_check(self) -> dict:
        """
        Check cache health and return statistics.
        
        Returns:
            Dictionary with health status and stats
        """
        if self._memory_enabled:
            return {
                "status": "degraded",
                "connected": False,
                "note": "in_memory_fallback"
            }
        try:
            # Test connection
            await self.redis.ping()
            # Get basic info
            info = await self.redis.info()
            return {
                "status": "healthy",
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except Exception as e:
            logger.error("cache_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
