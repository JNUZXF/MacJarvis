# File: backend/app/infrastructure/tasks/celery_app.py
# Purpose: Celery application configuration for async task processing
from celery import Celery
from kombu import Exchange, Queue
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "mac_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completion
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task info
    
    # Task routing
    task_routes={
        "app.infrastructure.tasks.workers.process_large_file": {"queue": "files"},
        "app.infrastructure.tasks.workers.generate_summary": {"queue": "ai"},
        "app.infrastructure.tasks.workers.extract_file_text": {"queue": "files"},
        "app.infrastructure.tasks.workers.cleanup_old_files": {"queue": "maintenance"},
        "app.infrastructure.tasks.background_agent.execute_delegated_task": {"queue": "ai"},
    },
    
    # Queues
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("files", Exchange("files"), routing_key="files"),
        Queue("ai", Exchange("ai"), routing_key="ai"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
    ),
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

logger.info(
    "celery_configured",
    broker=settings.CELERY_BROKER_URL.split("@")[-1],  # Hide password
    queues=["default", "files", "ai", "maintenance"]
)
