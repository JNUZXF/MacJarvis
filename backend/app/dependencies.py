# File: backend/app/dependencies.py
# Purpose: Dependency injection for FastAPI with proper lifecycle management
from typing import AsyncGenerator, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import structlog

from app.config import Settings, get_settings
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.cache.cache_manager import CacheManager
from app.infrastructure.llm.openai_client import OpenAIClient
from app.services.llm_service import LLMService
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.services.file_service import FileService
from app.services.chat_service import ChatService
from app.services.conversation_history_service import ConversationHistoryService
from app.services.markdown_exporter import MarkdownExporter

logger = structlog.get_logger(__name__)


# ============================================================================
# Configuration Dependencies
# ============================================================================

def get_app_settings() -> Settings:
    """
    Get application settings (singleton).
    
    Returns:
        Settings instance
    """
    return get_settings()


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db(
    settings: Settings = Depends(get_app_settings)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with automatic lifecycle management.
    
    Args:
        settings: Application settings
    
    Yields:
        Database session
    """
    async for session in get_db_session(settings):
        yield session


# ============================================================================
# Cache Dependencies
# ============================================================================

async def get_redis(
    settings: Settings = Depends(get_app_settings)
) -> AsyncGenerator[Optional[Redis], None]:
    """
    Get Redis client with automatic lifecycle management.
    
    Args:
        settings: Application settings
    
    Yields:
        Redis client or None if unavailable
    """
    async for redis in get_redis_client(settings):
        yield redis


async def get_cache_manager(
    redis: Optional[Redis] = Depends(get_redis),
    settings: Settings = Depends(get_app_settings)
) -> CacheManager:
    """
    Get cache manager instance.
    
    Args:
        redis: Redis client
        settings: Application settings
    
    Returns:
        Cache manager
    """
    if redis is None:
        logger.warning("cache_manager_using_in_memory_fallback")
    return CacheManager(redis, settings.LLM_CACHE_TTL)


# ============================================================================
# LLM Dependencies
# ============================================================================

def get_llm_client(
    settings: Settings = Depends(get_app_settings)
) -> OpenAIClient:
    """
    Get LLM client instance.
    
    Args:
        settings: Application settings
    
    Returns:
        OpenAI-compatible client
    """
    llm_config = settings.effective_llm_config
    
    return OpenAIClient(
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        timeout=llm_config["timeout_s"]
    )


async def get_llm_service(
    client: OpenAIClient = Depends(get_llm_client),
    cache: CacheManager = Depends(get_cache_manager),
    settings: Settings = Depends(get_app_settings)
) -> LLMService:
    """
    Get LLM service instance.
    
    Args:
        client: LLM client
        cache: Cache manager
        settings: Application settings
    
    Returns:
        LLM service
    """
    return LLMService(client, cache, settings)


# ============================================================================
# Business Service Dependencies
# ============================================================================

async def get_session_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache_manager),
    settings: Settings = Depends(get_app_settings)
) -> SessionService:
    """
    Get session service instance.
    
    Args:
        db: Database session
        cache: Cache manager
        settings: Application settings
    
    Returns:
        Session service
    """
    return SessionService(db, cache, settings)


async def get_user_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache_manager),
    settings: Settings = Depends(get_app_settings)
) -> UserService:
    """
    Get user service instance.
    
    Args:
        db: Database session
        cache: Cache manager
        settings: Application settings
    
    Returns:
        User service
    """
    return UserService(db, cache, settings)


def get_file_service(
    settings: Settings = Depends(get_app_settings)
) -> FileService:
    """
    Get file service instance.

    Args:
        settings: Application settings

    Returns:
        File service
    """
    return FileService(settings)


async def get_conversation_history_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings)
) -> ConversationHistoryService:
    """
    Get conversation history service instance.

    Args:
        db: Database session
        settings: Application settings

    Returns:
        Conversation history service
    """
    markdown_exporter = MarkdownExporter(base_path="files")
    return ConversationHistoryService(db, markdown_exporter, base_path="files")


async def get_chat_service(
    llm_service: LLMService = Depends(get_llm_service),
    session_service: SessionService = Depends(get_session_service),
    file_service: FileService = Depends(get_file_service),
    conversation_history_service: ConversationHistoryService = Depends(get_conversation_history_service),
    settings: Settings = Depends(get_app_settings)
) -> ChatService:
    """
    Get chat service instance (top-level orchestrator).

    Args:
        llm_service: LLM service
        session_service: Session service
        file_service: File service
        conversation_history_service: Conversation history service
        settings: Application settings

    Returns:
        Chat service
    """
    return ChatService(
        llm_service,
        session_service,
        file_service,
        conversation_history_service,
        settings
    )


# ============================================================================
# Utility Dependencies
# ============================================================================

async def get_current_user_id(
    # In production, this would extract user_id from JWT token or session
    # For now, we'll accept it from request parameters
) -> str:
    """
    Get current user ID from request context.
    
    In production, this should:
    - Validate JWT token
    - Extract user ID from token
    - Verify user exists
    
    Returns:
        User ID
    """
    # TODO: Implement proper authentication
    # For now, return a placeholder
    return "default_user"


# ============================================================================
# Health Check Dependencies
# ============================================================================

async def check_database_health(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Check database health.
    
    Args:
        db: Database session
    
    Returns:
        Health status dictionary
    """
    try:
        # Simple query to test connection
        await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


async def check_cache_health(
    cache: CacheManager = Depends(get_cache_manager)
) -> dict:
    """
    Check cache health.
    
    Args:
        cache: Cache manager
    
    Returns:
        Health status dictionary
    """
    return await cache.health_check()


async def check_llm_health(
    llm_service: LLMService = Depends(get_llm_service)
) -> dict:
    """
    Check LLM service health.
    
    Args:
        llm_service: LLM service
    
    Returns:
        Health status dictionary
    """
    return await llm_service.health_check()


# ============================================================================
# Dependency Overrides for Testing
# ============================================================================

# This dictionary can be used to override dependencies in tests
# Example: app.dependency_overrides[get_db] = get_test_db

_dependency_overrides = {}


def override_dependency(original, override):
    """
    Override a dependency for testing.
    
    Args:
        original: Original dependency function
        override: Override dependency function
    """
    _dependency_overrides[original] = override


def clear_dependency_overrides():
    """Clear all dependency overrides."""
    _dependency_overrides.clear()


def get_dependency_overrides() -> dict:
    """Get current dependency overrides."""
    return _dependency_overrides.copy()
