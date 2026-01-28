# File: backend/app/middleware/error_handler.py
# Purpose: Global error handling middleware with SSE support
from fastapi import Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog
import json
from typing import Union

logger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> Union[StreamingResponse, JSONResponse]:
    """
    Global exception handler for all unhandled exceptions.
    
    - For SSE endpoints (/api/v1/chat), returns SSE-formatted errors
    - For other endpoints, returns JSON errors
    - Logs all exceptions with full context
    
    Args:
        request: FastAPI request object
        exc: Exception that was raised
    
    Returns:
        Appropriate error response based on endpoint type
    """
    # Get request ID from state
    request_id = getattr(request.state, "request_id", None)
    
    # Log the exception with full context
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=request_id,
        exc_info=True
    )
    
    # Check if this is an SSE endpoint
    if _is_sse_endpoint(request.url.path):
        return _create_sse_error_response(str(exc), request_id)
    
    # Return JSON error for non-SSE endpoints
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": str(exc),
            "request_id": request_id
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Union[StreamingResponse, JSONResponse]:
    """
    Handler for Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: Validation error
    
    Returns:
        Formatted error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
        request_id=request_id
    )
    
    if _is_sse_endpoint(request.url.path):
        error_message = f"Invalid request: {_format_validation_errors(exc.errors())}"
        return _create_sse_error_response(error_message, request_id)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": request_id
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Union[StreamingResponse, JSONResponse]:
    """
    Handler for HTTP exceptions (404, 403, etc.).
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
    
    Returns:
        Formatted error response
    """
    request_id = getattr(request.state, "request_id", None)
    
    logger.warning(
        "http_exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=request_id
    )
    
    if _is_sse_endpoint(request.url.path):
        error_message = f"HTTP {exc.status_code}: {exc.detail}"
        return _create_sse_error_response(error_message, request_id)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": _get_error_code(exc.status_code),
            "message": exc.detail,
            "request_id": request_id
        }
    )


def _is_sse_endpoint(path: str) -> bool:
    """Check if the endpoint is an SSE endpoint"""
    return path.startswith("/api/v1/chat") or path.endswith("/stream")


def _create_sse_error_response(error_message: str, request_id: str = None) -> StreamingResponse:
    """Create an SSE-formatted error response"""
    error_data = {
        "message": error_message,
        "request_id": request_id
    }
    
    def error_generator():
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        error_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id or "unknown"
        }
    )


def _format_validation_errors(errors: list) -> str:
    """Format Pydantic validation errors into a readable string"""
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{loc}: {msg}")
    return "; ".join(error_messages)


def _get_error_code(status_code: int) -> str:
    """Map HTTP status code to error code string"""
    error_codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "too_many_requests",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }
    return error_codes.get(status_code, "unknown_error")


class ErrorHandlingMiddleware:
    """
    Middleware wrapper for consistent error handling.
    Can be used to add additional error processing logic.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Log unexpected errors in middleware
            logger.error(
                "middleware_exception",
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True
            )
            raise
