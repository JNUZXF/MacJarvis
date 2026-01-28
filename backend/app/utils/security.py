# File: backend/app/utils/security.py
# Purpose: Security utilities for input validation and sanitization
import re
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)


class InputValidator:
    """
    Input validation utilities to prevent security vulnerabilities.
    """
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.
        
        Args:
            value: Input string
            max_length: Maximum allowed length
        
        Returns:
            Sanitized string
        """
        if not value:
            return ""
        
        # Truncate to max length
        sanitized = value[:max_length]
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        return sanitized.strip()
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """
        Validate user ID format.
        
        Args:
            user_id: User ID to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not user_id or len(user_id) > 100:
            return False
        
        # Allow alphanumeric, hyphens, and underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, user_id))
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Validate session ID format (UUID).
        
        Args:
            session_id: Session ID to validate
        
        Returns:
            True if valid UUID format
        """
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, session_id, re.IGNORECASE))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        from pathlib import Path
        
        # Get basename only (remove any path components)
        filename = Path(filename).name
        
        # Remove dangerous characters
        dangerous_chars = ['/', '\\', '..', '\x00', '|', '<', '>', ':', '"', '?', '*']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name_part = filename[:200]
            ext_part = Path(filename).suffix
            filename = name_part + ext_part
        
        return filename or "unnamed_file"
    
    @staticmethod
    def validate_model_name(model: str, allowed_models: list[str]) -> bool:
        """
        Validate model name against whitelist.
        
        Args:
            model: Model name to validate
            allowed_models: List of allowed models
        
        Returns:
            True if model is allowed
        """
        return model in allowed_models
    
    @staticmethod
    def redact_sensitive_data(data: Any) -> Any:
        """
        Redact sensitive information from data structures.
        
        Args:
            data: Data to redact (dict, list, or primitive)
        
        Returns:
            Data with sensitive fields redacted
        """
        sensitive_keys = {
            "password", "passwd", "pwd", "secret", "api_key", "apikey",
            "token", "access_token", "refresh_token", "authorization",
            "auth", "credit_card", "ssn", "private_key", "key"
        }
        
        if isinstance(data, dict):
            return {
                key: "***REDACTED***" if any(s in key.lower() for s in sensitive_keys)
                else InputValidator.redact_sensitive_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [InputValidator.redact_sensitive_data(item) for item in data]
        else:
            return data


class RateLimiter:
    """
    Simple in-memory rate limiter.
    In production, use Redis-based rate limiting.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {key: [(timestamp, count)]}
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key (e.g., user_id, IP address)
        
        Returns:
            True if allowed, False if rate limited
        """
        import time
        
        now = time.time()
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                (ts, count) for ts, count in self.requests[key]
                if now - ts < self.window_seconds
            ]
        else:
            self.requests[key] = []
        
        # Count requests in window
        total_requests = sum(count for _, count in self.requests[key])
        
        if total_requests >= self.max_requests:
            logger.warning(
                "rate_limit_exceeded",
                key=key,
                requests=total_requests,
                max_requests=self.max_requests
            )
            return False
        
        # Add current request
        self.requests[key].append((now, 1))
        return True
    
    def reset(self, key: str):
        """Reset rate limit for a key"""
        if key in self.requests:
            del self.requests[key]


class SecurityHeaders:
    """Security headers for HTTP responses"""
    
    @staticmethod
    def get_security_headers() -> dict:
        """
        Get recommended security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
        }
