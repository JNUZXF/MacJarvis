# File: backend/app/middleware/metrics.py
# Purpose: Metrics collection middleware for monitoring and observability
import time
from typing import Dict, Optional
import structlog
from collections import defaultdict
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    In-memory metrics collector for basic monitoring.
    In production, this should be replaced with Prometheus, StatsD, or similar.
    """
    
    def __init__(self):
        self.request_count = defaultdict(int)  # {method: count}
        self.status_count = defaultdict(int)   # {status_code: count}
        self.path_count = defaultdict(int)     # {path: count}
        self.error_count = 0
        self.total_duration_ms = 0.0
        self.request_durations = []  # For percentile calculations
        self.start_time = datetime.utcnow()
        
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float
    ):
        """Record a completed HTTP request"""
        self.request_count[method] += 1
        self.status_count[status_code] += 1
        self.path_count[path] += 1
        self.total_duration_ms += duration_ms
        self.request_durations.append(duration_ms)
        
        if status_code >= 400:
            self.error_count += 1
        
        # Keep only last 1000 durations for percentile calculations
        if len(self.request_durations) > 1000:
            self.request_durations = self.request_durations[-1000:]
    
    def get_metrics(self) -> Dict:
        """Get current metrics snapshot"""
        total_requests = sum(self.request_count.values())
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        metrics = {
            "uptime_seconds": uptime_seconds,
            "total_requests": total_requests,
            "requests_per_second": total_requests / uptime_seconds if uptime_seconds > 0 else 0,
            "error_count": self.error_count,
            "error_rate": self.error_count / total_requests if total_requests > 0 else 0,
            "avg_duration_ms": self.total_duration_ms / total_requests if total_requests > 0 else 0,
            "requests_by_method": dict(self.request_count),
            "requests_by_status": dict(self.status_count),
            "top_paths": self._get_top_paths(10),
        }
        
        # Calculate percentiles if we have data
        if self.request_durations:
            sorted_durations = sorted(self.request_durations)
            metrics["p50_duration_ms"] = self._percentile(sorted_durations, 50)
            metrics["p95_duration_ms"] = self._percentile(sorted_durations, 95)
            metrics["p99_duration_ms"] = self._percentile(sorted_durations, 99)
        
        return metrics
    
    def _get_top_paths(self, limit: int) -> list:
        """Get top N most requested paths"""
        sorted_paths = sorted(
            self.path_count.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [{"path": path, "count": count} for path, count in sorted_paths[:limit]]
    
    def _percentile(self, sorted_data: list, percentile: float) -> float:
        """Calculate percentile from sorted data"""
        if not sorted_data:
            return 0.0
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def reset(self):
        """Reset all metrics"""
        self.request_count.clear()
        self.status_count.clear()
        self.path_count.clear()
        self.error_count = 0
        self.total_duration_ms = 0.0
        self.request_durations.clear()
        self.start_time = datetime.utcnow()


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return _metrics_collector


class MetricsMiddleware:
    """
    ASGI middleware to collect HTTP request metrics.
    对 StreamingResponse 也能正确统计（以最后一个 http.response.body 为结束信号）。
    """

    def __init__(self, app, collector: Optional[MetricsCollector] = None):
        self.app = app
        self.collector = collector or get_metrics_collector()

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Normalize path for metrics grouping.
        Replaces UUIDs and IDs with placeholders.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+/", "/{id}/", path)

        return path

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        method = scope.get("method") or ""
        start_time = time.time()
        status_code_holder = {"status_code": 500}
        finished = {"done": False}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code_holder["status_code"] = int(message.get("status") or 500)

            if message["type"] == "http.response.body" and not message.get("more_body", False):
                if not finished["done"]:
                    duration_ms = (time.time() - start_time) * 1000
                    self.collector.record_request(
                        method=method,
                        path=self._normalize_path(path),
                        status_code=status_code_holder["status_code"],
                        duration_ms=duration_ms,
                    )
                    if duration_ms > 1000:
                        logger.warning(
                            "slow_request",
                            method=method,
                            path=path,
                            duration_ms=round(duration_ms, 2),
                            status_code=status_code_holder["status_code"],
                        )
                    finished["done"] = True

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = (time.time() - start_time) * 1000
            self.collector.record_request(
                method=method,
                path=self._normalize_path(path),
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
