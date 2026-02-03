# File: backend/app/infrastructure/database/repositories.py
# Purpose: Repository pattern implementation for data access layer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import asyncio
import structlog
from sqlalchemy.exc import OperationalError

from app.infrastructure.database.models import (
    User, Session as DBSession, Message, UserPath,
    UploadedFile
)

logger = structlog.get_logger(__name__)


def _is_sqlite_locked_error(err: OperationalError) -> bool:
    # SQLAlchemy 会包装底层 sqlite3.OperationalError
    msg = str(err).lower()
    return "database is locked" in msg or ("sqlite" in msg and "locked" in msg)


async def _run_with_sqlite_write_retry(action_name: str, fn, *, retries: int = 5) -> object:
    """
    SQLite 在并发写入下可能出现短暂锁冲突；这里做小幅重试，避免直接 500。
    生产更推荐 PostgreSQL；SQLite 下建议配合单 worker + busy_timeout/WAL。
    """
    delay_s = 0.05
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except OperationalError as e:
            if not _is_sqlite_locked_error(e):
                raise
            last_err = e
            logger.warning(
                "sqlite_database_locked_retrying",
                action=action_name,
                attempt=attempt,
                retries=retries,
                delay_ms=int(delay_s * 1000),
            )
            await asyncio.sleep(delay_s)
            delay_s = min(delay_s * 2, 0.8)
    assert last_err is not None
    raise last_err


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
        async def _op():
            session = DBSession(id=session_id, user_id=user_id, title=title)
            self.db.add(session)
            await self.db.flush()
            return session

        session = await _run_with_sqlite_write_retry("session_create", _op)
        logger.info("session_created", session_id=session_id, user_id=user_id)
        return session  # type: ignore[return-value]
    
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
        async def _op():
            result = await self.db.execute(
                update(DBSession)
                .where(DBSession.id == session_id)
                .values(title=title, updated_at=datetime.utcnow())
            )
            await self.db.flush()
            return result.rowcount > 0

        return bool(await _run_with_sqlite_write_retry("session_update_title", _op))
    
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
        tool_calls: Optional[list] = None,
        tool_call_results: Optional[list] = None,
        metadata: Optional[dict] = None
    ) -> Message:
        """Create new message"""
        async def _op():
            message = Message(
                id=message_id,
                session_id=session_id,
                role=role,
                content=content,
                tool_calls=tool_calls or [],
                tool_call_results=tool_call_results,
                message_metadata=metadata
            )
            self.db.add(message)
            await self.db.flush()
            return message

        return await _run_with_sqlite_write_retry("message_create", _op)  # type: ignore[return-value]
    
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
