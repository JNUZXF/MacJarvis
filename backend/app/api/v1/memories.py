# File: backend/app/api/v1/memories.py
# Purpose: API endpoints for memory management
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import structlog

from app.api.schemas.memory import (
    MemoryContextResponse,
    MemoryStatisticsResponse,
    PreferenceResponse,
    FactResponse,
    TaskResponse,
    RelationResponse,
    ConsolidationResponse
)
from app.services.memory_manager import MemoryManager
from app.services.memory_consolidator import MemoryConsolidator
from app.services.memory_integration_service import MemoryIntegrationService
from app.infrastructure.database.connection import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


@router.get("/{user_id}/context", response_model=MemoryContextResponse)
async def get_user_memory_context(
    user_id: str,
    max_items: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user's memory context for display or debugging

    Args:
        user_id: User identifier
        max_items: Maximum items per memory type
        db: Database session

    Returns:
        User's memory context
    """
    try:
        memory_manager = MemoryManager(db)
        context = await memory_manager.get_user_context(
            user_id=user_id,
            max_items_per_type=max_items
        )

        return MemoryContextResponse(
            user_id=user_id,
            preferences=context["preferences"],
            facts=context["facts"],
            active_tasks=context["active_tasks"],
            relations=context["relations"]
        )

    except Exception as e:
        logger.error("get_memory_context_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/preferences", response_model=List[PreferenceResponse])
async def get_user_preferences(
    user_id: str,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user preferences

    Args:
        user_id: User identifier
        category: Optional category filter
        limit: Maximum number of preferences
        db: Database session

    Returns:
        List of user preferences
    """
    try:
        memory_manager = MemoryManager(db)
        preferences = await memory_manager.get_preferences(
            user_id=user_id,
            category=category,
            limit=limit
        )

        return [
            PreferenceResponse(
                id=p.id,
                category=p.category,
                key=p.preference_key,
                value=p.preference_value,
                confidence=p.confidence,
                source=p.source,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in preferences
        ]

    except Exception as e:
        logger.error("get_preferences_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/facts", response_model=List[FactResponse])
async def get_user_facts(
    user_id: str,
    fact_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user facts

    Args:
        user_id: User identifier
        fact_type: Optional fact type filter
        limit: Maximum number of facts
        db: Database session

    Returns:
        List of user facts
    """
    try:
        memory_manager = MemoryManager(db)
        facts = await memory_manager.get_facts(
            user_id=user_id,
            fact_type=fact_type,
            limit=limit
        )

        return [
            FactResponse(
                id=f.id,
                fact_type=f.fact_type,
                subject=f.subject,
                value=f.fact_value,
                confidence=f.confidence,
                source=f.source,
                created_at=f.created_at,
                updated_at=f.updated_at
            )
            for f in facts
        ]

    except Exception as e:
        logger.error("get_facts_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/tasks", response_model=List[TaskResponse])
async def get_user_tasks(
    user_id: str,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user tasks

    Args:
        user_id: User identifier
        status: Optional status filter (active, completed, etc.)
        task_type: Optional task type filter
        limit: Maximum number of tasks
        db: Database session

    Returns:
        List of user tasks
    """
    try:
        memory_manager = MemoryManager(db)
        tasks = await memory_manager.get_tasks(
            user_id=user_id,
            status=status,
            task_type=task_type,
            limit=limit
        )

        return [
            TaskResponse(
                id=t.id,
                task_type=t.task_type,
                title=t.title,
                description=t.description,
                status=t.status,
                progress=t.progress,
                priority=t.priority,
                created_at=t.created_at,
                updated_at=t.updated_at
            )
            for t in tasks
        ]

    except Exception as e:
        logger.error("get_tasks_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/relations", response_model=List[RelationResponse])
async def get_user_relations(
    user_id: str,
    entity: Optional[str] = None,
    relation_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user relations

    Args:
        user_id: User identifier
        entity: Optional entity filter
        relation_type: Optional relation type filter
        limit: Maximum number of relations
        db: Database session

    Returns:
        List of user relations
    """
    try:
        memory_manager = MemoryManager(db)
        relations = await memory_manager.get_relations(
            user_id=user_id,
            entity=entity,
            relation_type=relation_type,
            limit=limit
        )

        return [
            RelationResponse(
                id=r.id,
                subject_entity=r.subject_entity,
                subject_type=r.subject_type,
                relation_type=r.relation_type,
                object_entity=r.object_entity,
                object_type=r.object_type,
                confidence=r.confidence,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
            for r in relations
        ]

    except Exception as e:
        logger.error("get_relations_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/statistics", response_model=MemoryStatisticsResponse)
async def get_memory_statistics(
    user_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get memory statistics for a user

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Memory statistics
    """
    try:
        consolidator = MemoryConsolidator(db)
        stats = await consolidator.get_memory_statistics(user_id)

        return MemoryStatisticsResponse(**stats)

    except Exception as e:
        logger.error("get_memory_statistics_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/consolidate", response_model=ConsolidationResponse)
async def consolidate_user_memories(
    user_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Manually trigger memory consolidation for a user

    Args:
        user_id: User identifier
        db: Database session

    Returns:
        Consolidation results
    """
    try:
        consolidator = MemoryConsolidator(db)
        stats = await consolidator.consolidate_user_memories(user_id)

        return ConsolidationResponse(
            user_id=user_id,
            preferences_decayed=stats["preferences_decayed"],
            preferences_removed=stats["preferences_removed"],
            facts_decayed=stats["facts_decayed"],
            facts_removed=stats["facts_removed"],
            tasks_completed=stats["tasks_completed"],
            tasks_removed=stats["tasks_removed"],
            relations_decayed=stats["relations_decayed"],
            relations_removed=stats["relations_removed"]
        )

    except Exception as e:
        logger.error("consolidate_memories_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}/preferences/{preference_id}")
async def delete_preference(
    user_id: str,
    preference_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a specific preference"""
    try:
        from sqlalchemy import delete
        from app.infrastructure.database.models import PreferenceMemory

        result = await db.execute(
            delete(PreferenceMemory).where(
                PreferenceMemory.id == preference_id,
                PreferenceMemory.user_id == user_id
            )
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Preference not found")

        return {"status": "deleted", "id": preference_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_preference_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}/facts/{fact_id}")
async def delete_fact(
    user_id: str,
    fact_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a specific fact"""
    try:
        from sqlalchemy import delete
        from app.infrastructure.database.models import FactMemory

        result = await db.execute(
            delete(FactMemory).where(
                FactMemory.id == fact_id,
                FactMemory.user_id == user_id
            )
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fact not found")

        return {"status": "deleted", "id": fact_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_fact_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{user_id}/tasks/{task_id}")
async def update_task_status(
    user_id: str,
    task_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Update task status or progress"""
    try:
        memory_manager = MemoryManager(db)
        task = await memory_manager.update_task(
            task_id=task_id,
            status=status,
            progress=progress
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        return {
            "status": "updated",
            "id": task_id,
            "new_status": task.status,
            "new_progress": task.progress
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_task_failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
