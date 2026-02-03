# File: backend/app/services/memory_manager.py
# Purpose: Simplified memory manager for text-based memory storage
import structlog
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.infrastructure.database.models import User

logger = structlog.get_logger(__name__)


class MemoryManager:
    """Simplified memory manager for text-based memory storage"""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize memory manager

        Args:
            db_session: SQLAlchemy async database session
        """
        self.db = db_session

    async def get_user_memory(self, user_id: str) -> Dict[str, str]:
        """
        Get all memory types for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with 5 memory types as keys and their content as values
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.warning("user_not_found", user_id=user_id)
                return {
                    "preferences": "",
                    "facts": "",
                    "episodes": "",
                    "tasks": "",
                    "relations": ""
                }

            return {
                "preferences": user.memory_preferences or "",
                "facts": user.memory_facts or "",
                "episodes": user.memory_episodes or "",
                "tasks": user.memory_tasks or "",
                "relations": user.memory_relations or ""
            }

        except Exception as e:
            logger.error("get_user_memory_failed", user_id=user_id, error=str(e))
            raise

    async def update_user_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str
    ) -> bool:
        """
        Update a specific memory type for a user

        Args:
            user_id: User identifier
            memory_type: One of: preferences, facts, episodes, tasks, relations
            content: New memory content (natural language text)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate memory type
            valid_types = ["preferences", "facts", "episodes", "tasks", "relations"]
            if memory_type not in valid_types:
                logger.error("invalid_memory_type", memory_type=memory_type)
                return False

            # Map memory type to column name
            column_map = {
                "preferences": User.memory_preferences,
                "facts": User.memory_facts,
                "episodes": User.memory_episodes,
                "tasks": User.memory_tasks,
                "relations": User.memory_relations
            }

            # Update the specific memory field
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values({column_map[memory_type]: content})
            )
            await self.db.commit()

            logger.info(
                "memory_updated",
                user_id=user_id,
                memory_type=memory_type,
                content_length=len(content)
            )
            return True

        except Exception as e:
            logger.error(
                "update_user_memory_failed",
                user_id=user_id,
                memory_type=memory_type,
                error=str(e)
            )
            await self.db.rollback()
            return False
