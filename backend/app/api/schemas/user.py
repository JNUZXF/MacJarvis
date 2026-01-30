# File: backend/app/api/schemas/user.py
# Purpose: Pydantic schemas for user-related API endpoints
from pydantic import BaseModel, Field
from typing import List, Optional


class UserPathsRequest(BaseModel):
    """Request schema for setting user paths"""
    user_id: str = Field(..., description="User identifier")
    paths: List[str] = Field(..., description="List of allowed paths")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "paths": [
                    "/Users/username/Documents",
                    "/Users/username/Projects"
                ]
            }
        }


class UserPathsResponse(BaseModel):
    """Response schema for user paths"""
    user_id: str
    paths: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "paths": [
                    "/Users/username/Documents",
                    "/Users/username/Projects"
                ]
            }
        }


class UserProxyConfigRequest(BaseModel):
    """Request schema for user proxy configuration"""
    user_id: str = Field(..., description="User identifier")
    http_proxy: Optional[str] = Field(None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(None, description="HTTPS proxy URL")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "http_proxy": "http://127.0.0.1:7897",
                "https_proxy": "http://127.0.0.1:7897"
            }
        }


class UserProxyConfigResponse(BaseModel):
    """Response schema for user proxy configuration"""
    user_id: str
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "http_proxy": "http://127.0.0.1:7897",
                "https_proxy": "http://127.0.0.1:7897"
            }
        }


class FileUploadResponse(BaseModel):
    """Response schema for file upload"""
    id: str = Field(..., description="File identifier")
    filename: str = Field(..., description="Original filename")
    content_type: Optional[str] = Field(None, description="MIME type")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    created_at: int = Field(..., description="Upload timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "file789",
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "path": "/uploads/file789_document.pdf",
                "size": 1024000,
                "created_at": 1706400000000
            }
        }
