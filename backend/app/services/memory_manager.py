# File: backend/app/services/memory_manager.py
# Purpose: Manage all types of memories with deduplication and retrieval
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete

from app.infrastructure.database.models import (
    PreferenceMemory,
    FactMemory,
    TaskMemory,
    RelationMemory,
    EpisodicMemory
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified manager for all memory types with intelligent deduplication"""

    def __init__(self, db_session: AsyncSession, cache_manager=None):
        """
        Initialize memory manager

        Args:
            db_session: SQLAlchemy async database session
            cache_manager: Optional cache manager for performance
        """
        self.db = db_session
        self.cache = cache_manager

    # ============ Preference Memory Methods ============

    async def add_preference(
        self,
        user_id: str,
        category: str,
        preference_key: str,
        preference_value: str,
        confidence: int = 5,
        source: str = "explicit",
        extra_metadata: Optional[Dict] = None
    ) -> PreferenceMemory:
        """
        Add or update a user preference with deduplication

        Args:
            user_id: User identifier
            category: Preference category (food, communication, etc.)
            preference_key: Specific preference key
            preference_value: Preference value
            confidence: Confidence level (1-10)
            source: Source of preference (explicit, inferred)
            extra_metadata: Additional metadata

        Returns:
            PreferenceMemory instance
        """
        try:
            # Check for existing preference with same key
            existing = await self._find_existing_preference(user_id, category, preference_key)

            if existing:
                # Update existing preference if confidence is higher or equal
                if confidence >= existing.confidence:
                    existing.preference_value = preference_value
                    existing.confidence = confidence
                    existing.source = source
                    existing.updated_at = datetime.utcnow()
                    existing.last_confirmed_at = datetime.utcnow()
                    if extra_metadata:
                        existing.extra_metadata = extra_metadata

                    await self.db.commit()
                    logger.info(f"Updated preference {preference_key} for user {user_id}")
                    return existing
                else:
                    logger.info(f"Skipped updating preference {preference_key} - lower confidence")
                    return existing
            else:
                # Create new preference
                pref = PreferenceMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    category=category,
                    preference_key=preference_key,
                    preference_value=preference_value,
                    confidence=confidence,
                    source=source,
                    extra_metadata=extra_metadata,
                    last_confirmed_at=datetime.utcnow()
                )
                self.db.add(pref)
                await self.db.commit()
                logger.info(f"Added new preference {preference_key} for user {user_id}")
                return pref

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding preference: {e}", exc_info=True)
            raise

    async def _find_existing_preference(
        self,
        user_id: str,
        category: str,
        preference_key: str
    ) -> Optional[PreferenceMemory]:
        """Find existing preference by user, category, and key"""
        result = await self.db.execute(
            select(PreferenceMemory).where(
                and_(
                    PreferenceMemory.user_id == user_id,
                    PreferenceMemory.category == category,
                    PreferenceMemory.preference_key == preference_key
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_preferences(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[PreferenceMemory]:
        """Get user preferences, optionally filtered by category"""
        query = select(PreferenceMemory).where(PreferenceMemory.user_id == user_id)

        if category:
            query = query.where(PreferenceMemory.category == category)

        query = query.order_by(PreferenceMemory.confidence.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============ Fact Memory Methods ============

    async def add_fact(
        self,
        user_id: str,
        fact_type: str,
        subject: str,
        fact_value: str,
        confidence: int = 5,
        source: str = "direct_statement",
        extra_metadata: Optional[Dict] = None
    ) -> FactMemory:
        """
        Add or update a user fact with deduplication

        Args:
            user_id: User identifier
            fact_type: Type of fact (personal, professional, etc.)
            subject: Subject of the fact (name, job_title, etc.)
            fact_value: The fact value
            confidence: Confidence level (1-10)
            source: Source of fact
            extra_metadata: Additional metadata

        Returns:
            FactMemory instance
        """
        try:
            # Check for existing fact with same subject
            existing = await self._find_existing_fact(user_id, fact_type, subject)

            if existing:
                # Update if confidence is higher or value has changed
                if confidence >= existing.confidence or fact_value != existing.fact_value:
                    existing.fact_value = fact_value
                    existing.confidence = max(confidence, existing.confidence)
                    existing.source = source
                    existing.updated_at = datetime.utcnow()
                    existing.verified_at = datetime.utcnow()
                    if extra_metadata:
                        existing.extra_metadata = extra_metadata

                    await self.db.commit()
                    logger.info(f"Updated fact {subject} for user {user_id}")
                    return existing
                else:
                    logger.info(f"Skipped updating fact {subject} - no change")
                    return existing
            else:
                # Create new fact
                fact = FactMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    fact_type=fact_type,
                    subject=subject,
                    fact_value=fact_value,
                    confidence=confidence,
                    source=source,
                    extra_metadata=extra_metadata,
                    verified_at=datetime.utcnow()
                )
                self.db.add(fact)
                await self.db.commit()
                logger.info(f"Added new fact {subject} for user {user_id}")
                return fact

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding fact: {e}", exc_info=True)
            raise

    async def _find_existing_fact(
        self,
        user_id: str,
        fact_type: str,
        subject: str
    ) -> Optional[FactMemory]:
        """Find existing fact by user, type, and subject"""
        result = await self.db.execute(
            select(FactMemory).where(
                and_(
                    FactMemory.user_id == user_id,
                    FactMemory.fact_type == fact_type,
                    FactMemory.subject == subject
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_facts(
        self,
        user_id: str,
        fact_type: Optional[str] = None,
        limit: int = 100
    ) -> List[FactMemory]:
        """Get user facts, optionally filtered by type"""
        query = select(FactMemory).where(FactMemory.user_id == user_id)

        if fact_type:
            query = query.where(FactMemory.fact_type == fact_type)

        query = query.order_by(FactMemory.confidence.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============ Task Memory Methods ============

    @staticmethod
    def _clamp_progress(progress: int) -> int:
        """Clamp task progress to the inclusive range [0, 100]."""
        return max(0, min(100, progress))

    async def add_task(
        self,
        user_id: str,
        task_type: str,
        title: str,
        description: Optional[str] = None,
        status: str = "active",
        progress: int = 0,
        priority: str = "medium",
        context: Optional[Dict] = None,
        extra_metadata: Optional[Dict] = None,
        session_id: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> TaskMemory:
        """
        Add a new task

        Args:
            user_id: User identifier
            task_type: Type of task (project, todo, goal, etc.)
            title: Task title
            description: Task description
            status: Task status (active, completed, cancelled, on_hold)
            progress: Progress percentage (0-100)
            priority: Priority (low, medium, high, urgent)
            context: Related context (files, links, etc.)
            extra_metadata: Additional metadata
            session_id: Associated session ID
            due_date: Due date if any

        Returns:
            TaskMemory instance
        """
        try:
            # Check for duplicate active task with same title
            existing = await self._find_similar_task(user_id, title)

            if existing and existing.status == "active":
                logger.info(f"Task '{title}' already exists for user {user_id}")
                return existing

            # Clamp progress to valid range
            clamped_progress = self._clamp_progress(progress)

            # Create new task
            task = TaskMemory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                task_type=task_type,
                title=title,
                description=description,
                status=status,
                progress=clamped_progress,
                priority=priority,
                context=context,
                extra_metadata=extra_metadata,
                due_date=due_date
            )
            self.db.add(task)
            await self.db.commit()
            logger.info(f"Added new task '{title}' for user {user_id}")
            return task

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding task: {e}", exc_info=True)
            raise

    async def update_task(
        self,
        task_id: str,
        user_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        description: Optional[str] = None
    ) -> Optional[TaskMemory]:
        """Update an existing task (with user_id authorization check)"""
        try:
            result = await self.db.execute(
                select(TaskMemory).where(
                    and_(
                        TaskMemory.id == task_id,
                        TaskMemory.user_id == user_id
                    )
                )
            )
            task = result.scalar_one_or_none()

            if not task:
                return None

            if status:
                task.status = status
                if status == "completed":
                    task.completed_at = datetime.utcnow()
                    task.progress = 100

            if progress is not None:
                task.progress = self._clamp_progress(progress)

            if description:
                task.description = description

            task.updated_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Updated task {task_id} for user {user_id}")
            return task

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating task: {e}", exc_info=True)
            raise

    async def _find_similar_task(
        self,
        user_id: str,
        title: str
    ) -> Optional[TaskMemory]:
        """Find similar task by title"""
        result = await self.db.execute(
            select(TaskMemory).where(
                and_(
                    TaskMemory.user_id == user_id,
                    TaskMemory.title == title
                )
            ).order_by(TaskMemory.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskMemory]:
        """Get user tasks with optional filters"""
        query = select(TaskMemory).where(TaskMemory.user_id == user_id)

        if status:
            query = query.where(TaskMemory.status == status)

        if task_type:
            query = query.where(TaskMemory.task_type == task_type)

        query = query.order_by(TaskMemory.updated_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============ Relation Memory Methods ============

    async def add_relation(
        self,
        user_id: str,
        subject_entity: str,
        subject_type: str,
        relation_type: str,
        object_entity: str,
        object_type: str,
        confidence: int = 5,
        bidirectional: bool = False,
        extra_metadata: Optional[Dict] = None
    ) -> RelationMemory:
        """
        Add or update a relation between entities

        Args:
            user_id: User identifier
            subject_entity: First entity (e.g., "Alice")
            subject_type: Type of subject (person, project, etc.)
            relation_type: Type of relation (is_manager_of, works_on, etc.)
            object_entity: Second entity (e.g., "Bob")
            object_type: Type of object
            confidence: Confidence level (1-10)
            bidirectional: Whether relation works both ways
            extra_metadata: Additional metadata

        Returns:
            RelationMemory instance
        """
        try:
            # Check for existing relation
            existing = await self._find_existing_relation(
                user_id, subject_entity, relation_type, object_entity
            )

            if existing:
                # Update confidence if higher
                if confidence > existing.confidence:
                    existing.confidence = confidence
                    existing.updated_at = datetime.utcnow()
                    if extra_metadata:
                        existing.extra_metadata = extra_metadata

                    await self.db.commit()
                    logger.info(f"Updated relation: {subject_entity} {relation_type} {object_entity}")
                return existing
            else:
                # Create new relation
                relation = RelationMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    subject_entity=subject_entity,
                    subject_type=subject_type,
                    relation_type=relation_type,
                    object_entity=object_entity,
                    object_type=object_type,
                    confidence=confidence,
                    bidirectional=1 if bidirectional else 0,
                    metadata=metadata
                )
                self.db.add(relation)
                await self.db.commit()
                logger.info(f"Added new relation: {subject_entity} {relation_type} {object_entity}")
                return relation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding relation: {e}", exc_info=True)
            raise

    async def _find_existing_relation(
        self,
        user_id: str,
        subject_entity: str,
        relation_type: str,
        object_entity: str
    ) -> Optional[RelationMemory]:
        """Find existing relation"""
        result = await self.db.execute(
            select(RelationMemory).where(
                and_(
                    RelationMemory.user_id == user_id,
                    RelationMemory.subject_entity == subject_entity,
                    RelationMemory.relation_type == relation_type,
                    RelationMemory.object_entity == object_entity
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_relations(
        self,
        user_id: str,
        entity: Optional[str] = None,
        relation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[RelationMemory]:
        """Get relations, optionally filtered by entity or relation type"""
        query = select(RelationMemory).where(RelationMemory.user_id == user_id)

        if entity:
            query = query.where(
                or_(
                    RelationMemory.subject_entity == entity,
                    RelationMemory.object_entity == entity
                )
            )

        if relation_type:
            query = query.where(RelationMemory.relation_type == relation_type)

        query = query.order_by(RelationMemory.confidence.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============ Batch Operations ============

    async def add_extracted_memories(
        self,
        extracted: Dict[str, List[Dict[str, Any]]],
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Add all extracted memories in batch

        Args:
            extracted: Dictionary with preferences, facts, tasks, relations
            user_id: User identifier
            session_id: Optional session ID

        Returns:
            Dictionary with counts of added memories
        """
        counts = {
            "preferences": 0,
            "facts": 0,
            "tasks": 0,
            "relations": 0
        }

        # Add preferences
        for pref_data in extracted.get("preferences", []):
            await self.add_preference(
                user_id=user_id,
                category=pref_data.get("category", "general"),
                preference_key=pref_data.get("key", "unknown"),
                preference_value=pref_data.get("value", ""),
                confidence=pref_data.get("confidence", 5),
                source=pref_data.get("source", "explicit"),
                extra_metadata={"session_id": session_id} if session_id else None
            )
            counts["preferences"] += 1

        # Add facts
        for fact_data in extracted.get("facts", []):
            await self.add_fact(
                user_id=user_id,
                fact_type=fact_data.get("type", "general"),
                subject=fact_data.get("subject", "unknown"),
                fact_value=fact_data.get("value", ""),
                confidence=fact_data.get("confidence", 5),
                source=fact_data.get("source", "direct_statement"),
                extra_metadata={"session_id": session_id} if session_id else None
            )
            counts["facts"] += 1

        # Add tasks
        for task_data in extracted.get("tasks", []):
            await self.add_task(
                user_id=user_id,
                task_type=task_data.get("type", "todo"),
                title=task_data.get("title", ""),
                description=task_data.get("description"),
                status=task_data.get("status", "active"),
                priority=task_data.get("priority", "medium"),
                session_id=session_id
            )
            counts["tasks"] += 1

        # Add relations
        for rel_data in extracted.get("relations", []):
            await self.add_relation(
                user_id=user_id,
                subject_entity=rel_data.get("subject", ""),
                subject_type=rel_data.get("subject_type", "entity"),
                relation_type=rel_data.get("relation", "related_to"),
                object_entity=rel_data.get("object", ""),
                object_type=rel_data.get("object_type", "entity"),
                confidence=rel_data.get("confidence", 5),
                extra_metadata={"session_id": session_id} if session_id else None
            )
            counts["relations"] += 1

        logger.info(f"Added batch memories for user {user_id}: {counts}")
        return counts

    # ============ Context Retrieval for Agent ============

    async def get_user_context(
        self,
        user_id: str,
        max_items_per_type: int = 10
    ) -> Dict[str, Any]:
        """
        Get comprehensive user context for agent injection

        Args:
            user_id: User identifier
            max_items_per_type: Maximum items to retrieve per memory type

        Returns:
            Dictionary with all relevant user context
        """
        # Get all memory types in parallel
        preferences = await self.get_preferences(user_id, limit=max_items_per_type)
        facts = await self.get_facts(user_id, limit=max_items_per_type)
        active_tasks = await self.get_tasks(user_id, status="active", limit=max_items_per_type)
        relations = await self.get_relations(user_id, limit=max_items_per_type)

        # Format for agent consumption
        context = {
            "user_id": user_id,
            "preferences": [
                {
                    "category": p.category,
                    "key": p.preference_key,
                    "value": p.preference_value,
                    "confidence": p.confidence
                }
                for p in preferences
            ],
            "facts": [
                {
                    "type": f.fact_type,
                    "subject": f.subject,
                    "value": f.fact_value,
                    "confidence": f.confidence
                }
                for f in facts
            ],
            "active_tasks": [
                {
                    "type": t.task_type,
                    "title": t.title,
                    "status": t.status,
                    "progress": t.progress,
                    "priority": t.priority
                }
                for t in active_tasks
            ],
            "relations": [
                {
                    "subject": r.subject_entity,
                    "relation": r.relation_type,
                    "object": r.object_entity,
                    "confidence": r.confidence
                }
                for r in relations
            ]
        }

        return context
