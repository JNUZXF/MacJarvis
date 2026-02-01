# File: backend/app/middleware/request_id.py
# Purpose: Request ID middleware for distributed tracing and log correlation
import uuid
import time
import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """
    Middleware to add unique request ID to each HTTP request.
    The request ID is:
    - Generated for each request
    - Added to response headers (X-Request-ID)
    - Bound to logging context for correlation
    - Available in request.state for use in handlers
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 关键点：SSE/StreamingResponse 不要用 BaseHTTPMiddleware（会导致流式阻塞/缓冲）。
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        method = scope.get("method")
        path = scope.get("path")

        # FastAPI 的 request.state 基于 scope["state"]
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=method,
            path=path,
        )

        start_time = time.time()
        status_code_holder = {"status_code": None}
        logged = {"done": False}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code_holder["status_code"] = message.get("status")
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers

            if message["type"] == "http.response.body" and not message.get("more_body", False):
                # 最后一帧 body（对 StreamingResponse 也成立）
                if not logged["done"]:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "http_request_completed",
                        status_code=status_code_holder["status_code"],
                        duration_ms=round(duration_ms, 2),
                    )
                    logged["done"] = True
                    structlog.contextvars.clear_contextvars()

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "http_request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            structlog.contextvars.clear_contextvars()
            raise
        finally:
            # 兜底：如果没走到最后一帧 body（例如异常/中断），确保清理上下文
            if not logged["done"]:
                structlog.contextvars.clear_contextvars()


class RequestLoggingMiddleware:
    """
    Middleware for detailed HTTP request/response logging.
    Logs request details, response status, and timing information.
    """
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        self.app = app
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method")
        path = scope.get("path")
        query_string = scope.get("query_string") or b""
        headers = {k.decode("latin1"): v.decode("latin1") for k, v in (scope.get("headers") or [])}

        logger.info(
            "http_request_started",
            method=method,
            path=path,
            query_string=query_string.decode("utf-8", errors="ignore"),
            client_host=(scope.get("client") or [None])[0],
            user_agent=headers.get("user-agent"),
        )

        # 为了不影响 SSE/大 body，这里不读取 request body
        await self.app(scope, receive, send)
