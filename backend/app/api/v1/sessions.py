# File: backend/app/api/v1/sessions.py
# Purpose: Session management API endpoints
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
import structlog

from app.api.schemas.session import (
    SessionInitRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionListResponse,
    SessionInitResponse
)
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.dependencies import get_session_service, get_user_service
from app.core.machine_id import get_machine_id

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/session/init", response_model=SessionInitResponse)
async def init_session(
    request: SessionInitRequest,
    session_service: SessionService = Depends(get_session_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Initialize session for a user.
    Creates user if doesn't exist, returns active session or creates new one.
    
    如果未提供user_id，将自动使用机器硬件ID作为用户标识，
    确保同一台机器的数据持久化。
    """
    # 使用机器ID作为用户标识（如果未提供user_id）
    user_id = request.user_id or get_machine_id()
    user = await user_service.get_or_create_user(user_id)
    
    # Get sessions
    sessions = await session_service.list_sessions(user_id, limit=50)
    
    # Determine active session
    active_session_id = request.active_session_id
    
    if not sessions:
        # Create first session
        new_session = await session_service.create_session(user_id, "新会话")
        active_session_id = new_session["id"]
        sessions = [new_session]
    elif active_session_id:
        # Verify active session exists
        session_ids = {s["id"] for s in sessions}
        if active_session_id not in session_ids:
            # Create new session if active one doesn't exist
            new_session = await session_service.create_session(user_id, "新会话")
            active_session_id = new_session["id"]
            sessions.insert(0, new_session)
    else:
        # Use most recent session
        active_session_id = sessions[0]["id"]
    
    logger.info(
        "session_initialized",
        user_id=user_id,
        active_session_id=active_session_id,
        session_count=len(sessions)
    )
    
    return {
        "user_id": user_id,
        "active_session_id": active_session_id,
        "sessions": sessions
    }


@router.post("/session/new", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    session_service: SessionService = Depends(get_session_service)
):
    """Create a new chat session"""
    session = await session_service.create_session(
        user_id=request.user_id,
        title=request.title
    )
    
    return session


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: str = Query(..., description="User ID"),
    load_messages: bool = Query(True, description="Load messages"),
    session_service: SessionService = Depends(get_session_service)
):
    """Get session by ID with optional message loading"""
    session = await session_service.get_session(
        user_id=user_id,
        session_id=session_id,
        load_messages=load_messages
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.get("/sessions", response_model=List[SessionListResponse])
async def list_sessions(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum sessions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session_service: SessionService = Depends(get_session_service)
):
    """List sessions for a user"""
    sessions = await session_service.list_sessions(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return sessions


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Query(..., description="User ID"),
    session_service: SessionService = Depends(get_session_service)
):
    """Delete a session"""
    success = await session_service.delete_session(
        user_id=user_id,
        session_id=session_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


@router.patch("/session/{session_id}/title")
async def update_session_title(
    session_id: str,
    user_id: str = Query(..., description="User ID"),
    title: str = Query(..., description="New title"),
    session_service: SessionService = Depends(get_session_service)
):
    """Update session title"""
    success = await session_service.update_session_title(
        user_id=user_id,
        session_id=session_id,
        title=title
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "updated", "session_id": session_id, "title": title}


@router.delete("/sessions/clear")
async def clear_all_sessions(
    user_id: str = Query(..., description="User ID"),
    session_service: SessionService = Depends(get_session_service)
):
    """
    清除用户的所有聊天记录
    
    此操作将删除用户的所有会话和消息，不可恢复。
    建议在前端添加二次确认提示。
    """
    deleted_count = await session_service.clear_all_sessions(user_id)
    
    logger.info(
        "all_sessions_cleared",
        user_id=user_id,
        deleted_count=deleted_count
    )
    
    return {
        "status": "cleared",
        "user_id": user_id,
        "deleted_count": deleted_count,
        "message": f"已清除 {deleted_count} 个会话的所有聊天记录"
    }
