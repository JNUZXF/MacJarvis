# File: backend/app/services/memory_consolidator.py
# Purpose: Consolidate, optimize and clean up memories periodically
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete

from app.infrastructure.database.models import (
    PreferenceMemory,
    FactMemory,
    TaskMemory,
    RelationMemory
)

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    Consolidate and optimize memories periodically

    This service:
    1. Merges similar memories
    2. Decays confidence of old memories
    3. Removes low-confidence memories
    4. Completes old stale tasks
    5. Identifies contradictions
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize memory consolidator

        Args:
            db_session: SQLAlchemy async database session
        """
        self.db = db_session

        # Configuration
        self.confidence_decay_rate = 0.1  # Decay 10% per month
        self.min_confidence_threshold = 2  # Remove memories below this
        self.task_stale_days = 90  # Mark tasks as stale after this
        self.old_memory_days = 180  # Consider memories old after this

    # ============ Main Consolidation Entry Point ============

    async def consolidate_user_memories(self, user_id: str) -> Dict[str, int]:
        """
        Run full consolidation process for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with consolidation statistics
        """
        logger.info(f"Starting memory consolidation for user {user_id}")

        stats = {
            "preferences_decayed": 0,
            "preferences_removed": 0,
            "facts_decayed": 0,
            "facts_removed": 0,
            "tasks_marked_stale": 0,
            "relations_decayed": 0,
            "relations_removed": 0
        }

        # 1. Decay confidence of old memories
        decay_stats = await self._decay_old_memories(user_id)
        stats.update(decay_stats)

        # 2. Remove low-confidence memories
        removal_stats = await self._remove_low_confidence_memories(user_id)
        stats.update(removal_stats)

        # 3. Complete or remove stale tasks
        task_stats = await self._handle_stale_tasks(user_id)
        stats.update(task_stats)

        # 4. Deduplicate similar memories (additional cleanup)
        dedup_stats = await self._deduplicate_memories(user_id)
        stats.update(dedup_stats)

        logger.info(f"Completed memory consolidation for user {user_id}: {stats}")

        return stats

    # ============ Confidence Decay ============

    async def _decay_old_memories(self, user_id: str) -> Dict[str, int]:
        """Decay confidence of old memories based on age"""
        stats = {
            "preferences_decayed": 0,
            "facts_decayed": 0,
            "relations_decayed": 0
        }

        cutoff_date = datetime.utcnow() - timedelta(days=self.old_memory_days)

        # Decay preferences
        pref_result = await self.db.execute(
            select(PreferenceMemory).where(
                and_(
                    PreferenceMemory.user_id == user_id,
                    PreferenceMemory.updated_at < cutoff_date,
                    PreferenceMemory.confidence > self.min_confidence_threshold
                )
            )
        )
        old_prefs = list(pref_result.scalars().all())

        for pref in old_prefs:
            # Calculate decay based on months since last update
            months_old = (datetime.utcnow() - pref.updated_at).days / 30
            decay_amount = int(months_old * self.confidence_decay_rate)

            new_confidence = max(self.min_confidence_threshold, pref.confidence - decay_amount)

            if new_confidence != pref.confidence:
                pref.confidence = new_confidence
                pref.updated_at = datetime.utcnow()
                stats["preferences_decayed"] += 1

        # Decay facts
        fact_result = await self.db.execute(
            select(FactMemory).where(
                and_(
                    FactMemory.user_id == user_id,
                    FactMemory.updated_at < cutoff_date,
                    FactMemory.confidence > self.min_confidence_threshold
                )
            )
        )
        old_facts = list(fact_result.scalars().all())

        for fact in old_facts:
            months_old = (datetime.utcnow() - fact.updated_at).days / 30
            decay_amount = int(months_old * self.confidence_decay_rate)

            new_confidence = max(self.min_confidence_threshold, fact.confidence - decay_amount)

            if new_confidence != fact.confidence:
                fact.confidence = new_confidence
                fact.updated_at = datetime.utcnow()
                stats["facts_decayed"] += 1

        # Decay relations
        rel_result = await self.db.execute(
            select(RelationMemory).where(
                and_(
                    RelationMemory.user_id == user_id,
                    RelationMemory.updated_at < cutoff_date,
                    RelationMemory.confidence > self.min_confidence_threshold
                )
            )
        )
        old_rels = list(rel_result.scalars().all())

        for rel in old_rels:
            months_old = (datetime.utcnow() - rel.updated_at).days / 30
            decay_amount = int(months_old * self.confidence_decay_rate)

            new_confidence = max(self.min_confidence_threshold, rel.confidence - decay_amount)

            if new_confidence != rel.confidence:
                rel.confidence = new_confidence
                rel.updated_at = datetime.utcnow()
                stats["relations_decayed"] += 1

        await self.db.commit()

        return stats

    # ============ Low Confidence Removal ============

    async def _remove_low_confidence_memories(self, user_id: str) -> Dict[str, int]:
        """Remove memories with very low confidence"""
        stats = {
            "preferences_removed": 0,
            "facts_removed": 0,
            "relations_removed": 0
        }

        # Remove low-confidence preferences
        pref_result = await self.db.execute(
            delete(PreferenceMemory).where(
                and_(
                    PreferenceMemory.user_id == user_id,
                    PreferenceMemory.confidence < self.min_confidence_threshold
                )
            )
        )
        stats["preferences_removed"] = pref_result.rowcount

        # Remove low-confidence facts
        fact_result = await self.db.execute(
            delete(FactMemory).where(
                and_(
                    FactMemory.user_id == user_id,
                    FactMemory.confidence < self.min_confidence_threshold
                )
            )
        )
        stats["facts_removed"] = fact_result.rowcount

        # Remove low-confidence relations
        rel_result = await self.db.execute(
            delete(RelationMemory).where(
                and_(
                    RelationMemory.user_id == user_id,
                    RelationMemory.confidence < self.min_confidence_threshold
                )
            )
        )
        stats["relations_removed"] = rel_result.rowcount

        await self.db.commit()

        return stats

    # ============ Task Management ============

    async def _handle_stale_tasks(self, user_id: str) -> Dict[str, int]:
        """Mark stale tasks as on_hold or cancelled"""
        stats = {
            "tasks_marked_stale": 0
        }

        cutoff_date = datetime.utcnow() - timedelta(days=self.task_stale_days)

        # Get stale active tasks
        result = await self.db.execute(
            select(TaskMemory).where(
                and_(
                    TaskMemory.user_id == user_id,
                    TaskMemory.status == "active",
                    TaskMemory.updated_at < cutoff_date
                )
            )
        )
        stale_tasks = list(result.scalars().all())

        for task in stale_tasks:
            # If task has some progress, mark as on_hold
            # If no progress, mark as cancelled
            if task.progress > 0:
                task.status = "on_hold"
            else:
                task.status = "cancelled"

            task.updated_at = datetime.utcnow()
            stats["tasks_marked_stale"] += 1

        await self.db.commit()

        return stats

    # ============ Deduplication ============

    async def _deduplicate_memories(self, user_id: str) -> Dict[str, int]:
        """Remove exact duplicates (additional safety net)"""
        stats = {
            "duplicates_removed": 0
        }

        # This is a simplified deduplication
        # More sophisticated similarity detection could be added

        # Deduplicate preferences by key
        pref_result = await self.db.execute(
            select(PreferenceMemory).where(
                PreferenceMemory.user_id == user_id
            ).order_by(
                PreferenceMemory.preference_key,
                PreferenceMemory.confidence.desc(),
                PreferenceMemory.updated_at.desc()
            )
        )
        prefs = list(pref_result.scalars().all())

        seen_keys = set()
        to_delete = []

        for pref in prefs:
            key = f"{pref.category}:{pref.preference_key}"
            if key in seen_keys:
                to_delete.append(pref.id)
            else:
                seen_keys.add(key)

        # Delete duplicates
        if to_delete:
            await self.db.execute(
                delete(PreferenceMemory).where(
                    PreferenceMemory.id.in_(to_delete)
                )
            )
            stats["duplicates_removed"] += len(to_delete)

        await self.db.commit()

        return stats

    # ============ Memory Analysis ============

    async def get_memory_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about user's memories

        Args:
            user_id: User identifier

        Returns:
            Dictionary with memory statistics
        """
        # Count preferences
        pref_count = await self.db.execute(
            select(func.count(PreferenceMemory.id)).where(
                PreferenceMemory.user_id == user_id
            )
        )
        pref_total = pref_count.scalar()

        # Count facts
        fact_count = await self.db.execute(
            select(func.count(FactMemory.id)).where(
                FactMemory.user_id == user_id
            )
        )
        fact_total = fact_count.scalar()

        # Count tasks by status
        active_tasks = await self.db.execute(
            select(func.count(TaskMemory.id)).where(
                and_(
                    TaskMemory.user_id == user_id,
                    TaskMemory.status == "active"
                )
            )
        )
        active_task_count = active_tasks.scalar()

        completed_tasks = await self.db.execute(
            select(func.count(TaskMemory.id)).where(
                and_(
                    TaskMemory.user_id == user_id,
                    TaskMemory.status == "completed"
                )
            )
        )
        completed_task_count = completed_tasks.scalar()

        # Count relations
        rel_count = await self.db.execute(
            select(func.count(RelationMemory.id)).where(
                RelationMemory.user_id == user_id
            )
        )
        rel_total = rel_count.scalar()

        # Get average confidence scores
        avg_pref_conf = await self.db.execute(
            select(func.avg(PreferenceMemory.confidence)).where(
                PreferenceMemory.user_id == user_id
            )
        )
        avg_pref_confidence = avg_pref_conf.scalar() or 0

        avg_fact_conf = await self.db.execute(
            select(func.avg(FactMemory.confidence)).where(
                FactMemory.user_id == user_id
            )
        )
        avg_fact_confidence = avg_fact_conf.scalar() or 0

        return {
            "user_id": user_id,
            "total_preferences": pref_total,
            "total_facts": fact_total,
            "active_tasks": active_task_count,
            "completed_tasks": completed_task_count,
            "total_relations": rel_total,
            "avg_preference_confidence": round(avg_pref_confidence, 2),
            "avg_fact_confidence": round(avg_fact_confidence, 2),
            "total_memories": pref_total + fact_total + active_task_count + rel_total
        }

    # ============ Periodic Consolidation Task ============

    async def consolidate_all_users(self, limit: int = 100) -> Dict[str, Any]:
        """
        Run consolidation for all users (for scheduled task)

        Args:
            limit: Maximum number of users to process

        Returns:
            Dictionary with overall statistics
        """
        # This would be called by a Celery periodic task

        logger.info(f"Starting consolidation for all users (limit: {limit})")

        # Get active users (users with recent activity)
        # For now, we'll just get all users
        # In production, you'd want to filter by recent activity

        from app.infrastructure.database.models import User

        result = await self.db.execute(
            select(User.id).limit(limit)
        )
        user_ids = [row[0] for row in result.all()]

        total_stats = {
            "users_processed": 0,
            "total_memories_removed": 0,
            "total_memories_decayed": 0
        }

        for user_id in user_ids:
            try:
                stats = await self.consolidate_user_memories(user_id)

                total_stats["users_processed"] += 1
                total_stats["total_memories_removed"] += (
                    stats["preferences_removed"] +
                    stats["facts_removed"] +
                    stats["relations_removed"]
                )
                # tasks_marked_stale are not removed, just marked
                total_stats["total_tasks_marked_stale"] = total_stats.get("total_tasks_marked_stale", 0) + stats.get("tasks_marked_stale", 0)
                total_stats["total_memories_decayed"] += (
                    stats["preferences_decayed"] +
                    stats["facts_decayed"] +
                    stats["relations_decayed"]
                )

            except Exception as e:
                logger.error(f"Error consolidating memories for user {user_id}: {e}")
                continue

        logger.info(f"Completed consolidation for all users: {total_stats}")

        return total_stats
