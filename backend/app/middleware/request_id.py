# File: backend/app/middleware/request_id.py
# Purpose: Request ID middleware for distributed tracing and log correlation
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each HTTP request.
    The request ID is:
    - Generated for each request
    - Added to response headers (X-Request-ID)
    - Bound to logging context for correlation
    - Available in request.state for use in handlers
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Bind request_id to logging context
        # This makes it available in all logs during this request
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            logger.info(
                "http_request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error with request context
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "http_request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True
            )
            raise
            
        finally:
            # Clear logging context
            structlog.contextvars.clear_contextvars()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed HTTP request/response logging.
    Logs request details, response status, and timing information.
    """
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Log incoming request
        logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Optionally log request body (be careful with sensitive data!)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                logger.debug("http_request_body", body_size=len(body))
            except Exception:
                pass
        
        # Process request
        response = await call_next(request)
        
        return response
