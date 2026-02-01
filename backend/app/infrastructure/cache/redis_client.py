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


async def get_redis_client(settings: Settings = None) -> AsyncGenerator[Optional[Redis], None]:
    """
    Dependency for getting Redis client.
    Automatically handles connection lifecycle.
    
    Args:
        settings: Application settings (will be injected by FastAPI)
    
    Yields:
        Redis client instance, or None if connection fails
    """
    if settings is None:
        from app.config import get_settings
        settings = get_settings()
    
    # 重要：不要在每个请求结束时关闭共享的 ConnectionPool。
    # redis-py 的 close() 可能会关闭/断开连接池，导致后续请求出现卡住或连接异常。
    # 我们在进程生命周期内复用一个全局 Redis client，并只在应用 shutdown 时统一关闭。
    global _redis_client

    if _redis_client is not None:
        yield _redis_client
        return

    pool = get_redis_pool(settings)
    redis = Redis(connection_pool=pool)

    try:
        await redis.ping()
        _redis_client = redis
        yield _redis_client
    except Exception as e:
        logger.error("redis_connection_error", error=str(e))
        # 确保失败时不缓存坏的 client
        try:
            await redis.close(close_connection_pool=False)  # type: ignore[call-arg]
        except Exception:
            pass
        yield None


async def init_redis(settings: Settings):
    """
    Initialize Redis connection.
    Should be called on application startup.
    
    Args:
        settings: Application settings
    """
    global _redis_client

    pool = get_redis_pool(settings)
    redis = Redis(connection_pool=pool)

    try:
        await redis.ping()
        _redis_client = redis
        logger.info("redis_initialized")
    except Exception as e:
        logger.error("redis_init_failed", error=str(e))
        try:
            await redis.close(close_connection_pool=False)  # type: ignore[call-arg]
        except Exception:
            pass
        raise


async def close_redis():
    """
    Close Redis connections.
    Should be called on application shutdown.
    """
    global _redis_pool, _redis_client

    try:
        if _redis_client is not None:
            try:
                await _redis_client.close(close_connection_pool=False)  # type: ignore[call-arg]
            except TypeError:
                # 兼容旧版本 redis-py（没有 close_connection_pool 参数）
                await _redis_client.close()
    finally:
        _redis_client = None

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("redis_connections_closed")
