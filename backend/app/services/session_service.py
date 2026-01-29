# File: backend/app/services/session_service.py
# Purpose: Session management service with business logic
import uuid
from typing import Optional, List
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import (
    SessionRepository, MessageRepository, UserRepository
)
from app.infrastructure.cache.cache_manager import CacheManager
from app.config import Settings

logger = structlog.get_logger(__name__)


class SessionService:
    """
    Service for managing chat sessions.
    Handles session creation, retrieval, updates, and message management.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        cache: CacheManager,
        settings: Settings
    ):
        """
        Initialize session service.
        
        Args:
            db: Database session
            cache: Cache manager
            settings: Application settings
        """
        self.db = db
        self.cache = cache
        self.settings = settings
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.user_repo = UserRepository(db)
    
    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> dict:
        """
        Create a new chat session.
        
        Args:
            user_id: User ID
            title: Optional session title
        
        Returns:
            Session dictionary
        """
        # Ensure user exists
        user = await self.user_repo.get_or_create(user_id)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create title
        if not title or not title.strip():
            title = "新会话"
        
        # Create session in database
        session = await self.session_repo.create(
            user_id=user_id,
            title=title,
            session_id=session_id
        )
        
        # Convert to dict
        session_dict = {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "messages": [],
            "created_at": int(session.created_at.timestamp() * 1000),
            "updated_at": int(session.updated_at.timestamp() * 1000),
        }
        
        # Cache the session
        await self.cache.set_session(
            user_id=user_id,
            session_id=session_id,
            session_data=session_dict,
            ttl=3600  # 1 hour
        )
        
        logger.info(
            "session_created",
            user_id=user_id,
            session_id=session_id,
            title=title
        )
        
        return session_dict
    
    async def get_session(
        self,
        user_id: str,
        session_id: str,
        load_messages: bool = True
    ) -> Optional[dict]:
        """
        Get session by ID.
        
        Args:
            user_id: User ID
            session_id: Session ID
            load_messages: Whether to load messages
        
        Returns:
            Session dictionary or None if not found
        """
        # Try cache first
        cached = await self.cache.get_session(user_id, session_id)
        if cached and not load_messages:
            return cached
        
        # Load from database
        session = await self.session_repo.get_by_id(
            session_id,
            load_messages=load_messages
        )
        
        if not session:
            return None
        
        # Verify user owns this session
        if session.user_id != user_id:
            logger.warning(
                "session_access_denied",
                user_id=user_id,
                session_id=session_id,
                owner_id=session.user_id
            )
            return None
        
        # Convert to dict
        session_dict = {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": int(session.created_at.timestamp() * 1000),
            "updated_at": int(session.updated_at.timestamp() * 1000),
        }
        
        # Add messages if loaded
        if load_messages and session.messages:
            session_dict["messages"] = [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls or [],
                    "created_at": int(msg.created_at.timestamp() * 1000),
                }
                for msg in session.messages
            ]
        else:
            session_dict["messages"] = []
        
        # Update cache
        await self.cache.set_session(
            user_id=user_id,
            session_id=session_id,
            session_data=session_dict,
            ttl=3600
        )
        
        return session_dict
    
    async def list_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        List sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            offset: Offset for pagination
        
        Returns:
            List of session dictionaries
        """
        sessions = await self.session_repo.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return [
            {
                "id": session.id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": int(session.created_at.timestamp() * 1000),
                "updated_at": int(session.updated_at.timestamp() * 1000),
            }
            for session in sessions
        ]
    
    async def update_session_title(
        self,
        user_id: str,
        session_id: str,
        title: str
    ) -> bool:
        """
        Update session title.
        
        Args:
            user_id: User ID
            session_id: Session ID
            title: New title
        
        Returns:
            True if updated successfully
        """
        # Verify ownership
        session = await self.get_session(user_id, session_id, load_messages=False)
        if not session:
            return False
        
        # Update in database
        success = await self.session_repo.update_title(session_id, title)
        
        if success:
            # Invalidate cache
            await self.cache.delete(
                self.cache.session_cache_key(user_id, session_id)
            )
            
            logger.info(
                "session_title_updated",
                user_id=user_id,
                session_id=session_id,
                new_title=title
            )
        
        return success
    
    async def delete_session(
        self,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Delete a session.
        
        Args:
            user_id: User ID
            session_id: Session ID
        
        Returns:
            True if deleted successfully
        """
        # Verify ownership
        session = await self.get_session(user_id, session_id, load_messages=False)
        if not session:
            return False
        
        # Delete from database
        success = await self.session_repo.delete(session_id)
        
        if success:
            # Invalidate cache
            await self.cache.delete(
                self.cache.session_cache_key(user_id, session_id)
            )
            
            logger.info(
                "session_deleted",
                user_id=user_id,
                session_id=session_id
            )
        
        return success
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_call_results: Optional[list] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system, tool)
            content: Message content
            tool_calls: Optional tool calls
            tool_call_results: Optional tool call results
            metadata: Optional metadata

        Returns:
            Message dictionary
        """
        message_id = str(uuid.uuid4())

        message = await self.message_repo.create(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_results=tool_call_results,
            metadata=metadata
        )

        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "tool_calls": message.tool_calls or [],
            "tool_call_results": message.tool_call_results,
            "metadata": message.metadata,
            "created_at": int(message.created_at.timestamp() * 1000),
        }
    
    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[dict]:
        """
        Get recent messages from a session.
        
        Args:
            session_id: Session ID
            count: Number of messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        messages = await self.message_repo.get_recent_messages(
            session_id=session_id,
            count=count
        )
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls or [],
                "created_at": int(msg.created_at.timestamp() * 1000),
            }
            for msg in messages
        ]
    
    async def cleanup_old_messages(
        self,
        session_id: str,
        keep_last: int = 8
    ) -> int:
        """
        Clean up old messages in a session.
        
        Args:
            session_id: Session ID
            keep_last: Number of recent messages to keep
        
        Returns:
            Number of messages deleted
        """
        deleted_count = await self.message_repo.delete_old_messages(
            session_id=session_id,
            keep_last=keep_last
        )
        
        if deleted_count > 0:
            logger.info(
                "messages_cleaned_up",
                session_id=session_id,
                deleted_count=deleted_count,
                kept_count=keep_last
            )
        
        return deleted_count
    
    def create_session_title(self, content: str) -> str:
        """
        Create a session title from message content.
        
        Args:
            content: Message content
        
        Returns:
            Session title
        """
        trimmed = content.strip()
        if not trimmed:
            return "新会话"
        return trimmed[:24] + "..." if len(trimmed) > 24 else trimmed
