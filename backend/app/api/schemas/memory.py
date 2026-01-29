# File: backend/app/api/schemas/memory.py
# Purpose: Pydantic schemas for memory API responses
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class PreferenceResponse(BaseModel):
    """Response model for preference memory"""
    id: str
    category: str
    key: str
    value: str
    confidence: int
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FactResponse(BaseModel):
    """Response model for fact memory"""
    id: str
    fact_type: str
    subject: str
    value: str
    confidence: int
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Response model for task memory"""
    id: str
    task_type: str
    title: str
    description: Optional[str] = None
    status: str
    progress: int
    priority: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RelationResponse(BaseModel):
    """Response model for relation memory"""
    id: str
    subject_entity: str
    subject_type: str
    relation_type: str
    object_entity: str
    object_type: str
    confidence: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryContextResponse(BaseModel):
    """Response model for full user memory context"""
    user_id: str
    preferences: List[Dict[str, Any]]
    facts: List[Dict[str, Any]]
    active_tasks: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]


class MemoryStatisticsResponse(BaseModel):
    """Response model for memory statistics"""
    user_id: str
    total_preferences: int
    total_facts: int
    active_tasks: int
    completed_tasks: int
    total_relations: int
    avg_preference_confidence: float
    avg_fact_confidence: float
    total_memories: int


class ConsolidationResponse(BaseModel):
    """Response model for memory consolidation"""
    user_id: str
    preferences_decayed: int
    preferences_removed: int
    facts_decayed: int
    facts_removed: int
    tasks_completed: int
    tasks_removed: int
    relations_decayed: int
    relations_removed: int
