# File: backend/app/infrastructure/database/connection.py
# Purpose: Database connection management with async support and connection pooling
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)

# Global engine and session maker
_engine = None
_async_session_maker = None


def get_engine(settings: Settings):
    """
    Create and configure async database engine with connection pooling.
    
    Args:
        settings: Application settings
    
    Returns:
        Configured async engine
    """
    global _engine
    
    if _engine is not None:
        return _engine
    
    # Determine pool class based on database URL
    if settings.DATABASE_URL.startswith("sqlite"):
        # SQLite doesn't support connection pooling
        pool_class = NullPool
        pool_kwargs = {}
    else:
        # PostgreSQL/MySQL use connection pooling
        pool_class = QueuePool
        pool_kwargs = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }
    
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        poolclass=pool_class,
        **pool_kwargs
    )
    
    logger.info(
        "database_engine_created",
        database_url=settings.DATABASE_URL.split("://")[0] + "://***",  # Hide credentials
        pool_size=pool_kwargs.get("pool_size"),
        max_overflow=pool_kwargs.get("max_overflow"),
    )
    
    return _engine


def get_session_maker(settings: Settings) -> async_sessionmaker:
    """
    Get or create async session maker.
    
    Args:
        settings: Application settings
    
    Returns:
        Configured async session maker
    """
    global _async_session_maker
    
    if _async_session_maker is not None:
        return _async_session_maker
    
    engine = get_engine(settings)
    
    _async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autocommit=False,
        autoflush=False,
    )
    
    return _async_session_maker


async def get_db_session(settings: Settings = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    Automatically handles session lifecycle (commit/rollback/close).
    
    Args:
        settings: Application settings (will be injected by FastAPI)
    
    Yields:
        Async database session
    """
    if settings is None:
        from app.config import get_settings
        settings = get_settings()
    
    session_maker = get_session_maker(settings)
    
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("database_session_error", error=str(e), error_type=type(e).__name__)
            raise
        finally:
            await session.close()


async def init_db(settings: Settings):
    """
    Initialize database (create tables if they don't exist).
    Should be called on application startup.
    
    Args:
        settings: Application settings
    """
    from app.infrastructure.database.models import Base
    
    engine = get_engine(settings)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("database_initialized", tables=list(Base.metadata.tables.keys()))


async def close_db():
    """
    Close database connections.
    Should be called on application shutdown.
    """
    global _engine, _async_session_maker
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("database_connections_closed")
