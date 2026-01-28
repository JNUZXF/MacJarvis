# File: backend/app/api/schemas/session.py
# Purpose: Pydantic schemas for session-related API endpoints
from pydantic import BaseModel, Field
from typing import Optional, List


class SessionInitRequest(BaseModel):
    """Request schema for session initialization"""
    user_id: Optional[str] = Field(None, description="User identifier")
    active_session_id: Optional[str] = Field(None, description="Active session ID")


class SessionCreateRequest(BaseModel):
    """Request schema for creating new session"""
    user_id: str = Field(..., description="User identifier")
    title: Optional[str] = Field(None, description="Session title")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "title": "新的对话"
            }
        }


class MessageResponse(BaseModel):
    """Response schema for a single message"""
    id: str
    role: str
    content: str
    tool_calls: List[dict] = []
    created_at: int


class SessionResponse(BaseModel):
    """Response schema for session data"""
    id: str
    user_id: str
    title: str
    messages: List[MessageResponse] = []
    created_at: int
    updated_at: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session456",
                "user_id": "user123",
                "title": "新的对话",
                "messages": [],
                "created_at": 1706400000000,
                "updated_at": 1706400000000
            }
        }


class SessionListResponse(BaseModel):
    """Response schema for session list"""
    id: str
    user_id: str
    title: str
    created_at: int
    updated_at: int


class SessionInitResponse(BaseModel):
    """Response schema for session initialization"""
    user_id: str
    active_session_id: str
    sessions: List[SessionListResponse]
