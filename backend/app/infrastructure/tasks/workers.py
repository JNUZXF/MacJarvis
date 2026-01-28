# File: backend/app/infrastructure/tasks/workers.py
# Purpose: Celery worker tasks for background processing
from pathlib import Path
from typing import List, Dict
import structlog

from app.infrastructure.tasks.celery_app import celery_app
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_large_file(self, file_path: str, user_id: str) -> Dict:
    """
    Process large files in background.
    Useful for heavy document processing, OCR, etc.
    
    Args:
        self: Task instance (bound)
        file_path: Path to file
        user_id: User ID
    
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(
            "file_processing_started",
            file_path=file_path,
            user_id=user_id,
            task_id=self.request.id
        )
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Simulate processing (replace with actual logic)
        # - Extract text
        # - Generate embeddings
        # - Store in database
        # - etc.
        
        result = {
            "status": "completed",
            "file_path": file_path,
            "user_id": user_id,
            "task_id": self.request.id,
        }
        
        logger.info(
            "file_processing_completed",
            task_id=self.request.id,
            file_path=file_path
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "file_processing_failed",
            task_id=self.request.id,
            file_path=file_path,
            error=str(exc),
            error_type=type(exc).__name__
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_summary(self, session_id: str, messages: List[Dict]) -> Dict:
    """
    Generate session summary in background.
    
    Args:
        self: Task instance (bound)
        session_id: Session ID
        messages: List of messages to summarize
    
    Returns:
        Summary result dictionary
    """
    try:
        logger.info(
            "summary_generation_started",
            session_id=session_id,
            task_id=self.request.id,
            message_count=len(messages)
        )
        
        # Build text from messages
        text_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content:
                text_parts.append(f"{role}: {content}")
        
        full_text = "\n".join(text_parts)
        
        # Generate summary using LLM (synchronous version)
        # In production, use the LLM service
        summary = full_text[:200] + "..." if len(full_text) > 200 else full_text
        
        result = {
            "status": "completed",
            "session_id": session_id,
            "summary": summary,
            "task_id": self.request.id,
        }
        
        logger.info(
            "summary_generation_completed",
            task_id=self.request.id,
            session_id=session_id
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "summary_generation_failed",
            task_id=self.request.id,
            session_id=session_id,
            error=str(exc)
        )
        
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=2)
def extract_file_text(self, file_path: str) -> Dict:
    """
    Extract text from file in background.
    
    Args:
        self: Task instance (bound)
        file_path: Path to file
    
    Returns:
        Extraction result dictionary
    """
    try:
        logger.info(
            "text_extraction_started",
            file_path=file_path,
            task_id=self.request.id
        )
        
        from app.services.file_service import FileService
        
        file_service = FileService(settings)
        text = file_service.extract_text(Path(file_path))
        
        result = {
            "status": "completed",
            "file_path": file_path,
            "text": text,
            "text_length": len(text),
            "task_id": self.request.id,
        }
        
        logger.info(
            "text_extraction_completed",
            task_id=self.request.id,
            text_length=len(text)
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "text_extraction_failed",
            task_id=self.request.id,
            file_path=file_path,
            error=str(exc)
        )
        
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True)
def cleanup_old_files(self, days: int = 30) -> Dict:
    """
    Clean up old uploaded files.
    Should be run periodically (e.g., daily via Celery Beat).
    
    Args:
        self: Task instance (bound)
        days: Delete files older than this many days
    
    Returns:
        Cleanup result dictionary
    """
    try:
        from datetime import datetime, timedelta
        
        logger.info(
            "file_cleanup_started",
            task_id=self.request.id,
            days=days
        )
        
        upload_dir = Path(settings.UPLOAD_DIR)
        if not upload_dir.exists():
            return {
                "status": "completed",
                "deleted_count": 0,
                "message": "Upload directory does not exist"
            }
        
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                # Check file age
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(
                            "file_deletion_failed",
                            file_path=str(file_path),
                            error=str(e)
                        )
        
        result = {
            "status": "completed",
            "deleted_count": deleted_count,
            "days": days,
            "task_id": self.request.id,
        }
        
        logger.info(
            "file_cleanup_completed",
            task_id=self.request.id,
            deleted_count=deleted_count
        )
        
        return result
        
    except Exception as exc:
        logger.error(
            "file_cleanup_failed",
            task_id=self.request.id,
            error=str(exc)
        )
        raise


# Periodic tasks configuration (Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-old-files-daily": {
        "task": "app.infrastructure.tasks.workers.cleanup_old_files",
        "schedule": 86400.0,  # Every 24 hours
        "args": (30,),  # Delete files older than 30 days
    },
}
