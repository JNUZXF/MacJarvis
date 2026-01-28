# File: backend/app/infrastructure/database/repositories.py
# Purpose: Repository pattern implementation for data access layer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import structlog

from app.infrastructure.database.models import (
    User, Session as DBSession, Message, UserPath,
    EpisodicMemory, SemanticMemory, UploadedFile
)

logger = structlog.get_logger(__name__)


class UserRepository:
    """Repository for User model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, user_id: str) -> User:
        """Create new user"""
        user = User(id=user_id)
        self.db.add(user)
        await self.db.flush()
        logger.info("user_created", user_id=user_id)
        return user
    
    async def get_or_create(self, user_id: str) -> User:
        """Get existing user or create new one"""
        user = await self.get_by_id(user_id)
        if not user:
            user = await self.create(user_id)
        return user
    
    async def delete(self, user_id: str) -> bool:
        """Delete user and all related data"""
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
        await self.db.flush()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("user_deleted", user_id=user_id)
        return deleted


class SessionRepository:
    """Repository for Session model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, session_id: str, load_messages: bool = False) -> Optional[DBSession]:
        """Get session by ID with optional message loading"""
        query = select(DBSession).where(DBSession.id == session_id)
        
        if load_messages:
            query = query.options(selectinload(DBSession.messages))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, user_id: str, title: str, session_id: str) -> DBSession:
        """Create new session"""
        session = DBSession(id=session_id, user_id=user_id, title=title)
        self.db.add(session)
        await self.db.flush()
        logger.info("session_created", session_id=session_id, user_id=user_id)
        return session
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DBSession]:
        """List sessions for a user, ordered by update time"""
        result = await self.db.execute(
            select(DBSession)
            .where(DBSession.user_id == user_id)
            .order_by(DBSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def update_title(self, session_id: str, title: str) -> bool:
        """Update session title"""
        result = await self.db.execute(
            update(DBSession)
            .where(DBSession.id == session_id)
            .values(title=title, updated_at=datetime.utcnow())
        )
        await self.db.flush()
        return result.rowcount > 0
    
    async def delete(self, session_id: str) -> bool:
        """Delete session and all messages"""
        result = await self.db.execute(
            delete(DBSession).where(DBSession.id == session_id)
        )
        await self.db.flush()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("session_deleted", session_id=session_id)
        return deleted
    
    async def count_by_user(self, user_id: str) -> int:
        """Count sessions for a user"""
        result = await self.db.execute(
            select(func.count(DBSession.id)).where(DBSession.user_id == user_id)
        )
        return result.scalar_one()


class MessageRepository:
    """Repository for Message model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None
    ) -> Message:
        """Create new message"""
        message = Message(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls or []
        )
        self.db.add(message)
        await self.db.flush()
        return message
    
    async def list_by_session(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """List messages for a session"""
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
        )
        
        if limit is not None:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[Message]:
        """Get most recent messages from a session"""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(count)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))  # Return in chronological order
    
    async def delete_old_messages(
        self,
        session_id: str,
        keep_last: int = 8
    ) -> int:
        """Delete old messages, keeping only the most recent ones"""
        # Get IDs of messages to keep
        keep_result = await self.db.execute(
            select(Message.id)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(keep_last)
        )
        keep_ids = [row[0] for row in keep_result.all()]
        
        if not keep_ids:
            return 0
        
        # Delete messages not in keep list
        result = await self.db.execute(
            delete(Message)
            .where(Message.session_id == session_id)
            .where(Message.id.not_in(keep_ids))
        )
        await self.db.flush()
        deleted_count = result.rowcount
        
        if deleted_count > 0:
            logger.info(
                "old_messages_deleted",
                session_id=session_id,
                deleted_count=deleted_count,
                kept_count=keep_last
            )
        
        return deleted_count


class UserPathRepository:
    """Repository for UserPath model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_by_user(self, user_id: str) -> List[str]:
        """Get all paths for a user"""
        result = await self.db.execute(
            select(UserPath.path).where(UserPath.user_id == user_id)
        )
        return [row[0] for row in result.all()]
    
    async def set_paths(self, user_id: str, paths: List[str]) -> List[str]:
        """Replace all paths for a user"""
        # Delete existing paths
        await self.db.execute(
            delete(UserPath).where(UserPath.user_id == user_id)
        )
        
        # Add new paths
        for path in paths:
            user_path = UserPath(user_id=user_id, path=path)
            self.db.add(user_path)
        
        await self.db.flush()
        logger.info("user_paths_updated", user_id=user_id, path_count=len(paths))
        return paths
    
    async def add_path(self, user_id: str, path: str) -> bool:
        """Add a single path for a user"""
        # Check if path already exists
        result = await self.db.execute(
            select(UserPath)
            .where(UserPath.user_id == user_id)
            .where(UserPath.path == path)
        )
        if result.scalar_one_or_none():
            return False
        
        user_path = UserPath(user_id=user_id, path=path)
        self.db.add(user_path)
        await self.db.flush()
        return True


class EpisodicMemoryRepository:
    """Repository for EpisodicMemory model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        memory_id: str,
        user_id: str,
        session_id: Optional[str],
        episode_type: str,
        summary: str,
        content: dict,
        metadata: Optional[dict] = None
    ) -> EpisodicMemory:
        """Create new episodic memory"""
        memory = EpisodicMemory(
            id=memory_id,
            user_id=user_id,
            session_id=session_id,
            episode_type=episode_type,
            summary=summary,
            content=content,
            metadata=metadata or {}
        )
        self.db.add(memory)
        await self.db.flush()
        return memory
    
    async def search_by_keywords(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[EpisodicMemory]:
        """Search episodic memories by keywords (simple text matching)"""
        # Simple keyword search - in production, use full-text search
        result = await self.db.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.user_id == user_id)
            .where(EpisodicMemory.summary.contains(query))
            .order_by(EpisodicMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class SemanticMemoryRepository:
    """Repository for SemanticMemory model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        memory_id: str,
        user_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[dict] = None
    ) -> SemanticMemory:
        """Create new semantic memory"""
        memory = SemanticMemory(
            id=memory_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        self.db.add(memory)
        await self.db.flush()
        return memory
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[SemanticMemory]:
        """List semantic memories for a user"""
        result = await self.db.execute(
            select(SemanticMemory)
            .where(SemanticMemory.user_id == user_id)
            .order_by(SemanticMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
