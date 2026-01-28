# File: backend/app/services/file_service.py
# Purpose: File upload and processing service
import uuid
from pathlib import Path
from typing import Optional, BinaryIO
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)


class FileService:
    """
    Service for handling file uploads and processing.
    Supports various file types: PDF, Word, Excel, images, etc.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize file service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_size = settings.MAX_UPLOAD_SIZE
        self.text_limit = settings.ATTACHMENT_TEXT_LIMIT
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_upload(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> dict:
        """
        Save uploaded file to disk.
        
        Args:
            filename: Original filename
            content: File content as bytes
            content_type: MIME type
        
        Returns:
            File metadata dictionary
        
        Raises:
            ValueError: If file is too large
        """
        # Check file size
        if len(content) > self.max_size:
            raise ValueError(
                f"File too large: {len(content)} bytes (max: {self.max_size})"
            )
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Create file path
        file_path = self.upload_dir / f"{file_id}_{safe_filename}"
        
        # Save file
        file_path.write_bytes(content)
        
        metadata = {
            "id": file_id,
            "filename": safe_filename,
            "content_type": content_type,
            "path": str(file_path),
            "size": len(content),
            "created_at": self._now_ms(),
        }
        
        logger.info(
            "file_uploaded",
            file_id=file_id,
            filename=safe_filename,
            size=len(content),
            content_type=content_type
        )
        
        return metadata
    
    def is_image_file(self, path: Path, content_type: Optional[str] = None) -> bool:
        """
        Check if file is an image.
        
        Args:
            path: File path
            content_type: MIME type
        
        Returns:
            True if image, False otherwise
        """
        if content_type and content_type.startswith("image/"):
            return True
        
        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        return path.suffix.lower() in image_extensions
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from various file types.
        
        Args:
            file_path: Path to file
        
        Returns:
            Extracted text (truncated if too long)
        """
        ext = file_path.suffix.lower()
        
        try:
            if ext == ".pdf":
                return self._extract_from_pdf(file_path)
            elif ext in {".docx", ".doc"}:
                return self._extract_from_word(file_path)
            elif ext in {".xlsx", ".xls"}:
                return self._extract_from_excel(file_path)
            elif ext == ".txt":
                return self._extract_from_text(file_path)
            else:
                logger.warning("unsupported_file_type", extension=ext)
                return ""
        except Exception as e:
            logger.error(
                "text_extraction_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__
            )
            return ""
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            
            text_parts = []
            with file_path.open("rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            
            full_text = "\n\n".join(text_parts)
            return self._truncate_text(full_text)
        except ImportError:
            logger.error("pypdf2_not_installed")
            return ""
    
    def _extract_from_word(self, file_path: Path) -> str:
        """Extract text from Word document"""
        try:
            import docx
            
            doc = docx.Document(str(file_path))
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text])
            return self._truncate_text(text)
        except ImportError:
            logger.error("python_docx_not_installed")
            return ""
    
    def _extract_from_excel(self, file_path: Path) -> str:
        """Extract text from Excel file"""
        try:
            import pandas as pd
            
            df = pd.read_excel(str(file_path))
            text = df.to_string()
            return self._truncate_text(text)
        except ImportError:
            logger.error("pandas_not_installed")
            return ""
    
    def _extract_from_text(self, file_path: Path) -> str:
        """Extract text from plain text file"""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return self._truncate_text(text)
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to configured limit"""
        if len(text) > self.text_limit:
            return text[:self.text_limit] + "\n\n[文本已截断...]"
        return text
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks.
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = Path(filename).name
        
        # Remove or replace dangerous characters
        dangerous_chars = ['/', '\\', '..', '\x00']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name_part = filename[:200]
            ext_part = Path(filename).suffix
            filename = name_part + ext_part
        
        return filename or "unnamed_file"
    
    def _now_ms(self) -> int:
        """Get current timestamp in milliseconds"""
        import time
        return int(time.time() * 1000)
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete uploaded file.
        
        Args:
            file_path: Path to file
        
        Returns:
            True if deleted successfully
        """
        try:
            path = Path(file_path)
            
            # Security check: ensure file is in upload directory
            if not str(path.resolve()).startswith(str(self.upload_dir.resolve())):
                logger.error(
                    "file_deletion_security_violation",
                    file_path=file_path,
                    upload_dir=str(self.upload_dir)
                )
                return False
            
            if path.exists():
                path.unlink()
                logger.info("file_deleted", file_path=file_path)
                return True
            
            return False
        except Exception as e:
            logger.error(
                "file_deletion_failed",
                file_path=file_path,
                error=str(e)
            )
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get file information.
        
        Args:
            file_path: Path to file
        
        Returns:
            File info dictionary or None if not found
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                "path": str(path),
                "filename": path.name,
                "size": stat.st_size,
                "created_at": int(stat.st_ctime * 1000),
                "modified_at": int(stat.st_mtime * 1000),
                "is_image": self.is_image_file(path),
            }
        except Exception as e:
            logger.error(
                "get_file_info_failed",
                file_path=file_path,
                error=str(e)
            )
            return None
