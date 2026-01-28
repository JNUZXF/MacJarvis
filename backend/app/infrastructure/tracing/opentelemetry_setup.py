# File: backend/app/infrastructure/tracing/opentelemetry_setup.py
# Purpose: OpenTelemetry setup for distributed tracing (optional)
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


def setup_tracing(
    service_name: str = "mac_agent",
    jaeger_endpoint: Optional[str] = None,
    enable_tracing: bool = False
):
    """
    Setup OpenTelemetry tracing (optional feature).
    
    Args:
        service_name: Service name for tracing
        jaeger_endpoint: Jaeger collector endpoint
        enable_tracing: Whether to enable tracing
    """
    if not enable_tracing:
        logger.info("tracing_disabled")
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        
        # Create resource
        resource = Resource.create({"service.name": service_name})
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add Jaeger exporter if endpoint provided
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                collector_endpoint=jaeger_endpoint,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Auto-instrument libraries
        FastAPIInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        
        logger.info(
            "tracing_enabled",
            service_name=service_name,
            jaeger_endpoint=jaeger_endpoint
        )
        
    except ImportError as e:
        logger.warning(
            "tracing_setup_failed",
            error="OpenTelemetry packages not installed",
            hint="Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi"
        )
    except Exception as e:
        logger.error(
            "tracing_setup_error",
            error=str(e),
            error_type=type(e).__name__
        )


def get_tracer(name: str = "mac_agent"):
    """
    Get tracer instance for manual instrumentation.
    
    Args:
        name: Tracer name
    
    Returns:
        Tracer instance or None if tracing is disabled
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return None
