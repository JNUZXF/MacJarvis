# File: backend/app/services/user_service.py
# Purpose: User management service for paths and preferences
from typing import List, Optional
from pathlib import Path
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.infrastructure.database.repositories import UserRepository, UserPathRepository
from app.infrastructure.cache.cache_manager import CacheManager
from app.config import Settings

logger = structlog.get_logger(__name__)


class UserService:
    """
    Service for managing user data and preferences.
    Handles user paths, settings, and user lifecycle.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        cache: CacheManager,
        settings: Settings
    ):
        """
        Initialize user service.
        
        Args:
            db: Database session
            cache: Cache manager
            settings: Application settings
        """
        self.db = db
        self.cache = cache
        self.settings = settings
        self.user_repo = UserRepository(db)
        self.path_repo = UserPathRepository(db)
    
    async def get_or_create_user(self, user_id: str) -> dict:
        """
        Get existing user or create new one.
        
        Args:
            user_id: User ID
        
        Returns:
            User dictionary
        """
        user = await self.user_repo.get_or_create(user_id)
        
        return {
            "id": user.id,
            "created_at": int(user.created_at.timestamp() * 1000),
            "updated_at": int(user.updated_at.timestamp() * 1000),
        }
    
    async def get_user_paths(self, user_id: str) -> List[str]:
        """
        Get allowed file system paths for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of allowed paths
        """
        # Try cache first
        cached_paths = await self.cache.get_user_paths(user_id)
        if cached_paths is not None:
            logger.debug("user_paths_cache_hit", user_id=user_id)
            return cached_paths
        
        # Load from database
        paths = await self.path_repo.list_by_user(user_id)
        
        # Cache the result
        await self.cache.set_user_paths(user_id, paths, ttl=3600)
        
        return paths
    
    async def set_user_paths(
        self,
        user_id: str,
        paths: List[str]
    ) -> List[str]:
        """
        Set allowed file system paths for a user.
        Validates and normalizes paths before saving.
        
        Args:
            user_id: User ID
            paths: List of paths to allow
        
        Returns:
            List of normalized paths that were saved
        """
        # Ensure user exists
        await self.user_repo.get_or_create(user_id)
        
        # Normalize and validate paths
        normalized_paths = self._normalize_paths(paths)
        
        # Save to database
        saved_paths = await self.path_repo.set_paths(user_id, normalized_paths)
        
        # Update cache
        await self.cache.set_user_paths(user_id, saved_paths, ttl=3600)
        
        logger.info(
            "user_paths_updated",
            user_id=user_id,
            path_count=len(saved_paths)
        )
        
        return saved_paths
    
    async def add_user_path(
        self,
        user_id: str,
        path: str
    ) -> bool:
        """
        Add a single path to user's allowed paths.
        
        Args:
            user_id: User ID
            path: Path to add
        
        Returns:
            True if added, False if already exists
        """
        # Normalize path
        normalized = self._normalize_single_path(path)
        if not normalized:
            return False
        
        # Add to database
        added = await self.path_repo.add_path(user_id, normalized)
        
        if added:
            # Invalidate cache
            await self.cache.delete(
                self.cache.user_paths_cache_key(user_id)
            )
            
            logger.info(
                "user_path_added",
                user_id=user_id,
                path=normalized
            )
        
        return added
    
    def _normalize_paths(self, raw_paths: List[str]) -> List[str]:
        """
        Normalize and validate a list of paths.
        
        Args:
            raw_paths: List of raw path strings
        
        Returns:
            List of normalized valid paths
        """
        normalized = []
        seen = set()
        
        for raw in raw_paths:
            path_str = self._normalize_single_path(raw)
            if path_str and path_str not in seen:
                normalized.append(path_str)
                seen.add(path_str)
        
        return normalized
    
    def _normalize_single_path(self, raw_path: str) -> str:
        """
        Normalize and validate a single path.
        
        Args:
            raw_path: Raw path string
        
        Returns:
            Normalized path string or empty string if invalid
        """
        if not raw_path or not raw_path.strip():
            return ""
        
    def _proxy_cache_key(self, user_id: str) -> str:
        return f"user_proxy:{user_id}"

    def _validate_proxy_url(self, proxy_url: Optional[str]) -> Optional[str]:
        if proxy_url is None:
            return None
        trimmed = proxy_url.strip()
        if not trimmed:
            return None
        if trimmed.startswith("http://") or trimmed.startswith("https://"):
            return trimmed
        raise ValueError("代理地址格式错误，必须以 http:// 或 https:// 开头")

    async def get_user_proxy_config(self, user_id: str) -> dict:
        """
        Get user proxy configuration.
        Returns empty values if not configured.
        """
        cache_key = self._proxy_cache_key(user_id)
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                return {
                    "user_id": user_id,
                    "http_proxy": payload.get("http_proxy"),
                    "https_proxy": payload.get("https_proxy"),
                }
            except json.JSONDecodeError:
                await self.cache.delete(cache_key)

        return {"user_id": user_id, "http_proxy": None, "https_proxy": None}

    async def set_user_proxy_config(
        self,
        user_id: str,
        http_proxy: Optional[str] = None,
        https_proxy: Optional[str] = None
    ) -> dict:
        """
        Set user proxy configuration.
        """
        await self.user_repo.get_or_create(user_id)

        normalized_http = self._validate_proxy_url(http_proxy)
        normalized_https = self._validate_proxy_url(https_proxy)

        payload = {
            "http_proxy": normalized_http,
            "https_proxy": normalized_https,
        }
        cache_key = self._proxy_cache_key(user_id)
        await self.cache.set(cache_key, json.dumps(payload, ensure_ascii=False), ttl=86400 * 30)

        logger.info(
            "user_proxy_updated",
            user_id=user_id,
            http_proxy=normalized_http or "",
            https_proxy=normalized_https or ""
        )

        return {"user_id": user_id, **payload}

        try:
            path = Path(raw_path.strip()).resolve()
            
            # Reject root path
            if path.as_posix() == "/":
                logger.warning("rejected_root_path", raw_path=raw_path)
                return ""
            
            # Check if path exists and is a directory
            if not path.exists():
                logger.warning("path_not_exists", path=str(path))
                return ""
            
            if not path.is_dir():
                logger.warning("path_not_directory", path=str(path))
                return ""
            
            return str(path)
            
        except Exception as e:
            logger.warning(
                "path_normalization_failed",
                raw_path=raw_path,
                error=str(e)
            )
            return ""
    
    async def get_effective_allowed_roots(self, user_id: str) -> List[Path]:
        """
        Get effective allowed root paths for a user.
        Combines user-specific paths with system-wide allowed roots.
        
        Args:
            user_id: User ID
        
        Returns:
            List of Path objects
        """
        # Get user-specific paths
        user_paths = await self.get_user_paths(user_id)
        
        # Get system-wide allowed roots
        system_roots = self.settings.get_allowed_roots()
        
        # Combine and deduplicate
        all_paths = user_paths + system_roots
        unique_paths = []
        seen = set()
        
        for path_str in all_paths:
            if path_str and path_str not in seen:
                try:
                    path = Path(path_str).resolve()
                    if path.exists() and path.is_dir():
                        unique_paths.append(path)
                        seen.add(path_str)
                except Exception:
                    continue
        
        return unique_paths
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user and all associated data.
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted successfully
        """
        success = await self.user_repo.delete(user_id)
        
        if success:
            # Invalidate all user caches
            await self.cache.invalidate_user_sessions(user_id)
            await self.cache.delete(
                self.cache.user_paths_cache_key(user_id)
            )
            
            logger.info("user_deleted", user_id=user_id)
        
        return success
