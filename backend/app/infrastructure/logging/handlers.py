# File: backend/app/infrastructure/logging/handlers.py
# Purpose: Custom log handlers for specialized logging needs
import logging
from typing import Optional
from pathlib import Path


class PerformanceLogHandler(logging.Handler):
    """
    Custom handler for performance metrics logging.
    Logs slow operations, database queries, LLM calls, etc.
    """
    
    def __init__(self, log_file: Path, threshold_ms: float = 1000.0):
        """
        Initialize performance log handler.
        
        Args:
            log_file: Path to performance log file
            threshold_ms: Threshold in milliseconds for logging (default 1000ms)
        """
        super().__init__()
        self.log_file = log_file
        self.threshold_ms = threshold_ms
        
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        self.file_handler = logging.FileHandler(log_file, encoding="utf-8")
        self.file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
    
    def emit(self, record: logging.LogRecord):
        """Emit log record if it meets performance threshold"""
        # Check if record has duration_ms attribute
        duration_ms = getattr(record, 'duration_ms', None)
        
        if duration_ms is not None and duration_ms >= self.threshold_ms:
            self.file_handler.emit(record)


class MetricsHandler(logging.Handler):
    """
    Handler for collecting metrics from logs.
    Can be used to aggregate statistics for monitoring.
    """
    
    def __init__(self):
        super().__init__()
        self.metrics = {
            "http_requests": 0,
            "errors": 0,
            "llm_calls": 0,
            "tool_executions": 0,
        }
    
    def emit(self, record: logging.LogRecord):
        """Collect metrics from log records"""
        event = getattr(record, 'event', None)
        
        if event == "http_request":
            self.metrics["http_requests"] += 1
        elif event == "llm_call_success" or event == "llm_call_failed":
            self.metrics["llm_calls"] += 1
        elif event == "tool_start":
            self.metrics["tool_executions"] += 1
        
        if record.levelno >= logging.ERROR:
            self.metrics["errors"] += 1
    
    def get_metrics(self) -> dict:
        """Get collected metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics to zero"""
        for key in self.metrics:
            self.metrics[key] = 0


class ErrorAggregationHandler(logging.Handler):
    """
    Handler that aggregates similar errors to prevent log flooding.
    Useful for production environments with high error rates.
    """
    
    def __init__(self, max_similar_errors: int = 10):
        """
        Initialize error aggregation handler.
        
        Args:
            max_similar_errors: Maximum number of similar errors to log
        """
        super().__init__()
        self.max_similar_errors = max_similar_errors
        self.error_counts = {}
    
    def emit(self, record: logging.LogRecord):
        """Aggregate similar errors"""
        if record.levelno < logging.ERROR:
            return
        
        # Create error signature
        error_sig = f"{record.pathname}:{record.lineno}:{record.msg}"
        
        # Increment count
        self.error_counts[error_sig] = self.error_counts.get(error_sig, 0) + 1
        
        # Only log if under threshold
        if self.error_counts[error_sig] <= self.max_similar_errors:
            # Log normally
            pass
        elif self.error_counts[error_sig] == self.max_similar_errors + 1:
            # Log aggregation message
            record.msg = f"[AGGREGATED] Similar error occurred {self.max_similar_errors}+ times: {record.msg}"
