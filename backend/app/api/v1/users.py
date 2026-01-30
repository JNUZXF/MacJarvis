# File: backend/app/api/v1/users.py
# Purpose: User management API endpoints
from fastapi import APIRouter, Depends, Query, HTTPException
import structlog

from app.api.schemas.user import (
    UserPathsRequest,
    UserPathsResponse,
    UserProxyConfigRequest,
    UserProxyConfigResponse
)
from app.services.user_service import UserService
from app.dependencies import get_user_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/user/paths", response_model=UserPathsResponse)
async def get_user_paths(
    user_id: str = Query(..., description="User ID"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get allowed file system paths for a user.
    """
    paths = await user_service.get_user_paths(user_id)
    
    return {
        "user_id": user_id,
        "paths": paths
    }


@router.post("/user/paths", response_model=UserPathsResponse)
async def set_user_paths(
    request: UserPathsRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Set allowed file system paths for a user.
    Paths are validated and normalized before saving.
    """
    normalized_paths = await user_service.set_user_paths(
        user_id=request.user_id,
        paths=request.paths
    )
    
    return {
        "user_id": request.user_id,
        "paths": normalized_paths
    }


@router.post("/user/paths/add")
async def add_user_path(
    user_id: str = Query(..., description="User ID"),
    path: str = Query(..., description="Path to add"),
    user_service: UserService = Depends(get_user_service)
):
    """Add a single path to user's allowed paths"""
    added = await user_service.add_user_path(
        user_id=user_id,
        path=path
    )
    
    if not added:
        return {
            "status": "already_exists",
            "message": "Path already in allowed list or invalid"
        }
    
    return {
        "status": "added",
        "path": path
    }


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user and all associated data.
    WARNING: This is a destructive operation!
    """
    success = await user_service.delete_user(user_id)
    
    if not success:
        return {
            "status": "not_found",
            "message": "User not found"
        }
    
    return {
        "status": "deleted",
        "user_id": user_id
    }


@router.get("/user/proxy", response_model=UserProxyConfigResponse)
async def get_user_proxy_config(
    user_id: str = Query(..., description="User ID"),
    user_service: UserService = Depends(get_user_service)
):
    """Get user proxy configuration"""
    return await user_service.get_user_proxy_config(user_id)


@router.post("/user/proxy", response_model=UserProxyConfigResponse)
async def set_user_proxy_config(
    request: UserProxyConfigRequest,
    user_service: UserService = Depends(get_user_service)
):
    """Set user proxy configuration"""
    try:
        return await user_service.set_user_proxy_config(
            user_id=request.user_id,
            http_proxy=request.http_proxy,
            https_proxy=request.https_proxy
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
