# File: backend/app/infrastructure/llm/client.py
# Purpose: Base LLM client with retry logic and error handling
import httpx
import asyncio
from typing import Optional, AsyncIterator, Union
import structlog

logger = structlog.get_logger(__name__)


class LLMClient:
    """
    Base class for LLM API clients.
    Provides common functionality for HTTP requests with timeout and error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize LLM client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Create HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
            ),
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> dict:
        """Get default headers for requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx request
        
        Returns:
            HTTP response
        
        Raises:
            httpx.HTTPError: On HTTP errors
            asyncio.TimeoutError: On timeout
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as e:
            logger.error("llm_request_timeout", url=url, timeout=self.timeout)
            raise asyncio.TimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_http_error",
                url=url,
                status_code=e.response.status_code,
                response=e.response.text[:500]
            )
            raise
        except httpx.RequestError as e:
            logger.error("llm_request_error", url=url, error=str(e))
            raise
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
