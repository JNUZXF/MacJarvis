# File: backend/app/infrastructure/llm/retry_policy.py
# Purpose: Retry policies for LLM API calls with exponential backoff
import asyncio
from typing import Callable, TypeVar, Any
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class RetryPolicy:
    """
    Configurable retry policy with exponential backoff.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry policy.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            import random
            # Add jitter: random value between 0 and delay
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: Exception that was raised
        
        Returns:
            True if should retry, False otherwise
        """
        # Retry on timeout and connection errors
        if isinstance(exception, (asyncio.TimeoutError, ConnectionError)):
            return True
        
        # Retry on specific HTTP status codes
        if hasattr(exception, 'response'):
            status_code = getattr(exception.response, 'status_code', None)
            if status_code in (408, 429, 500, 502, 503, 504):
                return True
        
        return False


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter
    
    Returns:
        Decorated function with retry logic
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter
    )
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not policy.should_retry(e):
                        logger.warning(
                            "non_retryable_error",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__
                        )
                        raise
                    
                    if attempt < policy.max_attempts - 1:
                        delay = policy.calculate_delay(attempt)
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=policy.max_attempts,
                            delay_seconds=round(delay, 2),
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "max_retries_exceeded",
                            function=func.__name__,
                            max_attempts=policy.max_attempts,
                            error=str(e)
                        )
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


# Predefined retry policies for common scenarios

# Standard retry: 3 attempts with exponential backoff
standard_retry = with_retry(max_attempts=3, initial_delay=1.0, max_delay=10.0)

# Aggressive retry: More attempts for critical operations
aggressive_retry = with_retry(max_attempts=5, initial_delay=0.5, max_delay=30.0)

# Conservative retry: Fewer attempts with longer delays
conservative_retry = with_retry(max_attempts=2, initial_delay=2.0, max_delay=60.0)
