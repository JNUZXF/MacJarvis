# File: backend/app/main.py
# Purpose: FastAPI application entry point with all components integrated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from app.config import get_settings
from app.infrastructure.logging.setup import setup_logging
from app.infrastructure.database.connection import init_db, close_db
from app.infrastructure.cache.redis_client import init_redis, close_redis
from app.infrastructure.tracing.opentelemetry_setup import setup_tracing
from app.middleware.request_id import RequestIDMiddleware, RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware, get_metrics_collector
from app.middleware.error_handler import (
    global_exception_handler,
    validation_exception_handler,
    http_exception_handler
)

# Import API routers
from app.api.v1 import chat, sessions, files, users, tts, asr, memories

settings = get_settings()

# Setup logging first
logger = setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir="./logs",
    app_name="mac_agent"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        env=settings.ENV,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL
    )
    
    try:
        # Initialize database
        await init_db(settings)
        logger.info("database_ready")
        
        # Initialize Redis (optional - will use in-memory cache if Redis is unavailable)
        try:
            await init_redis(settings)
            logger.info("redis_ready")
        except Exception as redis_error:
            logger.warning(
                "redis_initialization_failed_using_fallback",
                error=str(redis_error)
            )
            # Redis is optional - application can run without it
        
        # Setup tracing (optional)
        setup_tracing(
            service_name=settings.APP_NAME,
            jaeger_endpoint=settings.JAEGER_ENDPOINT,
            enable_tracing=settings.ENABLE_TRACING
        )
        
        logger.info("application_started")
        
    except Exception as e:
        logger.error(
            "application_startup_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    
    try:
        await close_db()
        await close_redis()
        logger.info("application_shutdown_complete")
    except Exception as e:
        logger.error(
            "application_shutdown_error",
            error=str(e)
        )


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade MacOS Agent Backend with AI capabilities",
    version="2.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add custom middleware first (order matters!)
# FastAPI中间件是LIFO（后进先出）顺序，所以先添加的中间件后执行
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
if settings.DEBUG:
    app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware LAST (will execute FIRST due to LIFO)
# 处理CORS配置：当allow_credentials=True时，不能使用["*"]
# 如果配置中包含"*"，则设置allow_credentials=False以允许所有源
cors_origins = settings.get_cors_origins()
allow_creds = True
if "*" in cors_origins:
    # 如果使用通配符，则不允许credentials（浏览器安全限制）
    allow_creds = False
    logger.warning(
        "cors_using_wildcard_without_credentials",
        message="CORS_ORIGINS contains '*', setting allow_credentials=False for compatibility"
    )

# 记录CORS配置用于调试
logger.info(
    "cors_configuration",
    cors_origins=cors_origins,
    allow_credentials=allow_creds
)

# CORS中间件必须最后添加（FastAPI中间件是LIFO顺序）
# 这样CORS头会在响应处理的最外层被添加
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 明确暴露所有头
)

# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "environment": settings.ENV
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all components"""
    from app.dependencies import check_database_health, check_cache_health
    
    try:
        # Check all components
        # Note: In production, these should have timeouts
        db_health = await check_database_health()
        cache_health = await check_cache_health()
        
        overall_status = "healthy"
        if db_health.get("status") != "healthy" or cache_health.get("status") != "healthy":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "service": settings.APP_NAME,
            "version": "2.0.0",
            "environment": settings.ENV,
            "components": {
                "database": db_health,
                "cache": cache_health,
            }
        }
    except Exception as e:
        logger.error("detailed_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint for monitoring"""
    collector = get_metrics_collector()
    metrics = collector.get_metrics()
    
    return {
        "service": settings.APP_NAME,
        "metrics": metrics
    }


# ============================================================================
# API Routes
# ============================================================================

# Include API routers
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["chat"])
app.include_router(sessions.router, prefix=settings.API_V1_PREFIX, tags=["sessions"])
app.include_router(files.router, prefix=settings.API_V1_PREFIX, tags=["files"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["users"])
app.include_router(tts.router, prefix=f"{settings.API_V1_PREFIX}/tts", tags=["tts"])
app.include_router(asr.router, prefix=f"{settings.API_V1_PREFIX}/asr", tags=["asr"])
app.include_router(memories.router, tags=["memories"])


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "environment": settings.ENV,
        "api_prefix": settings.API_V1_PREFIX,
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/health",
        "metrics_url": "/metrics"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
