# File: backend/app/infrastructure/logging/setup.py
# Purpose: Production-grade structured logging setup with rotation and archiving
import structlog
import logging
import logging.handlers
from pathlib import Path
from pythonjsonlogger import jsonlogger
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    app_name: str = "mac_agent"
) -> structlog.BoundLogger:
    """
    Setup production-grade structured logging with:
    - JSON formatting for machine parsing
    - File rotation (daily for app logs, size-based for errors)
    - Separate handlers for different log levels
    - Context variables support for request tracking
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        app_name: Application name for logger identification
    
    Returns:
        Configured structlog logger instance
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog processors
    structlog.configure(
        processors=[
            # Add context variables (like request_id)
            structlog.contextvars.merge_contextvars,
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Format positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Render as JSON
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # JSON formatter for all handlers
    json_formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger"
        }
    )
    
    # Console handler - for development and Docker logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # File handler - Application logs (rotated daily, keep 30 days)
    app_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_path / f"{app_name}.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    app_handler.setFormatter(json_formatter)
    app_handler.setLevel(logging.INFO)
    app_handler.suffix = "%Y-%m-%d"  # Add date suffix to rotated files
    root_logger.addHandler(app_handler)
    
    # File handler - Error logs (rotated by size, keep 10 files)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"{app_name}_error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setFormatter(json_formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # File handler - Access logs (for HTTP requests)
    access_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_path / f"{app_name}_access.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    access_handler.setFormatter(json_formatter)
    access_handler.setLevel(logging.INFO)
    access_handler.suffix = "%Y-%m-%d"
    
    # Create separate logger for access logs
    access_logger = logging.getLogger("access")
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False  # Don't propagate to root logger
    
    # Return configured structlog logger
    logger = structlog.get_logger(app_name)
    logger.info(
        "logging_initialized",
        log_level=log_level,
        log_dir=str(log_path),
        handlers=["console", "app_file", "error_file", "access_file"]
    )
    
    return logger


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structlog logger instance.
    
    Args:
        name: Optional logger name. If None, returns the root logger.
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def get_access_logger() -> logging.Logger:
    """
    Get the access logger for HTTP request logging.
    
    Returns:
        Standard logging.Logger instance for access logs
    """
    return logging.getLogger("access")
