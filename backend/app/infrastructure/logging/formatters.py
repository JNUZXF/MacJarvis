# File: backend/app/infrastructure/logging/formatters.py
# Purpose: Custom log formatters for different output formats
import json
from typing import Any, Dict
from datetime import datetime


class SensitiveDataFilter:
    """
    Filter to redact sensitive information from logs.
    Prevents accidental logging of passwords, API keys, tokens, etc.
    """
    
    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "auth",
        "credit_card",
        "ssn",
        "private_key",
    }
    
    @classmethod
    def redact(cls, data: Any) -> Any:
        """
        Recursively redact sensitive data from dictionaries and lists.
        
        Args:
            data: Data to redact (dict, list, or primitive)
        
        Returns:
            Data with sensitive fields redacted
        """
        if isinstance(data, dict):
            return {
                key: "***REDACTED***" if cls._is_sensitive_key(key) else cls.redact(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [cls.redact(item) for item in data]
        else:
            return data
    
    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        """Check if a key name indicates sensitive data"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in cls.SENSITIVE_KEYS)


def format_log_event(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format log event with additional metadata and sensitive data filtering.
    
    Args:
        event_dict: Raw log event dictionary
    
    Returns:
        Formatted log event
    """
    # Add timestamp if not present
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.utcnow().isoformat()
    
    # Redact sensitive data
    event_dict = SensitiveDataFilter.redact(event_dict)
    
    # Add environment marker
    event_dict["_source"] = "mac_agent_backend"
    
    return event_dict


def format_exception(exc_info: tuple) -> Dict[str, Any]:
    """
    Format exception information for structured logging.
    
    Args:
        exc_info: Exception info tuple (type, value, traceback)
    
    Returns:
        Formatted exception dictionary
    """
    if not exc_info or exc_info == (None, None, None):
        return {}
    
    exc_type, exc_value, exc_traceback = exc_info
    
    return {
        "exception_type": exc_type.__name__ if exc_type else None,
        "exception_message": str(exc_value) if exc_value else None,
        "exception_traceback": _format_traceback(exc_traceback) if exc_traceback else None,
    }


def _format_traceback(tb) -> list:
    """Format traceback as a list of frame dictionaries"""
    import traceback
    
    frames = []
    for frame in traceback.extract_tb(tb):
        frames.append({
            "filename": frame.filename,
            "line": frame.lineno,
            "function": frame.name,
            "code": frame.line,
        })
    return frames


def format_http_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str = None,
    user_id: str = None,
    **extra
) -> Dict[str, Any]:
    """
    Format HTTP request log entry.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        request_id: Optional request ID
        user_id: Optional user ID
        **extra: Additional fields
    
    Returns:
        Formatted HTTP request log
    """
    log_entry = {
        "event": "http_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if request_id:
        log_entry["request_id"] = request_id
    if user_id:
        log_entry["user_id"] = user_id
    
    # Add extra fields
    log_entry.update(extra)
    
    return log_entry
