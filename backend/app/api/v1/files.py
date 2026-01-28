# File: backend/app/api/v1/files.py
# Purpose: File upload and management API endpoints
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import structlog

from app.api.schemas.user import FileUploadResponse
from app.services.file_service import FileService
from app.dependencies import get_file_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/files", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service)
):
    """
    Upload a file for use in chat attachments.
    
    Supports:
    - PDF, Word, Excel documents
    - Images (PNG, JPG, WEBP, GIF)
    - Plain text files
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save file
        metadata = await file_service.save_upload(
            filename=file.filename or "unnamed",
            content=content,
            content_type=file.content_type
        )
        
        return metadata
        
    except ValueError as e:
        # File too large or other validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "file_upload_failed",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get("/files/{file_id}")
async def get_file_info(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """Get file information by ID"""
    # In production, this would query the database
    # For now, return basic info
    return {
        "id": file_id,
        "status": "available"
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """Delete an uploaded file"""
    # In production, this would:
    # 1. Query database for file path
    # 2. Verify user ownership
    # 3. Delete file
    # 4. Update database
    
    return {
        "status": "deleted",
        "file_id": file_id
    }
