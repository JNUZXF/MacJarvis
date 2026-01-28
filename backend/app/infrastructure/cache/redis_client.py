# File: backend/app/infrastructure/cache/redis_client.py
# Purpose: Redis client configuration and connection management
from redis.asyncio import Redis, ConnectionPool
from typing import AsyncGenerator, Optional
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def get_redis_pool(settings: Settings) -> ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Args:
        settings: Application settings
    
    Returns:
        Redis connection pool
    """
    global _redis_pool
    
    if _redis_pool is not None:
        return _redis_pool
    
    _redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,  # Automatically decode bytes to strings
        encoding="utf-8",
    )
    
    logger.info(
        "redis_pool_created",
        redis_url=settings.REDIS_URL.split("@")[-1],  # Hide password
        max_connections=settings.REDIS_MAX_CONNECTIONS
    )
    
    return _redis_pool


async def get_redis_client(settings: Settings = None) -> AsyncGenerator[Redis, None]:
    """
    Dependency for getting Redis client.
    Automatically handles connection lifecycle.
    
    Args:
        settings: Application settings (will be injected by FastAPI)
    
    Yields:
        Redis client instance
    """
    if settings is None:
        from app.config import get_settings
        settings = get_settings()
    
    pool = get_redis_pool(settings)
    redis = Redis(connection_pool=pool)
    
    try:
        # Test connection
        await redis.ping()
        yield redis
    except Exception as e:
        logger.error("redis_connection_error", error=str(e))
        raise
    finally:
        await redis.close()


async def init_redis(settings: Settings):
    """
    Initialize Redis connection.
    Should be called on application startup.
    
    Args:
        settings: Application settings
    """
    pool = get_redis_pool(settings)
    redis = Redis(connection_pool=pool)
    
    try:
        # Test connection
        await redis.ping()
        logger.info("redis_initialized")
    except Exception as e:
        logger.error("redis_init_failed", error=str(e))
        raise
    finally:
        await redis.close()


async def close_redis():
    """
    Close Redis connections.
    Should be called on application shutdown.
    """
    global _redis_pool, _redis_client
    
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        _redis_client = None
        logger.info("redis_connections_closed")
