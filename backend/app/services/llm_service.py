# File: backend/app/services/llm_service.py
# Purpose: LLM service with caching, retry logic, and error handling
import asyncio
from typing import Optional, Union, AsyncIterator
import structlog

from app.infrastructure.llm.openai_client import OpenAIClient
from app.infrastructure.cache.cache_manager import CacheManager
from app.infrastructure.llm.retry_policy import with_retry
from app.config import Settings

logger = structlog.get_logger(__name__)


class LLMService:
    """
    High-level LLM service with production-grade features:
    - Response caching for cost optimization
    - Automatic retry with exponential backoff
    - Timeout control
    - Comprehensive error handling and logging
    """
    
    def __init__(
        self,
        client: OpenAIClient,
        cache: CacheManager,
        settings: Settings
    ):
        """
        Initialize LLM service.
        
        Args:
            client: OpenAI-compatible client
            cache: Cache manager for response caching
            settings: Application settings
        """
        self.client = client
        self.cache = cache
        self.settings = settings
    
    @with_retry(max_attempts=3, initial_delay=2.0, max_delay=10.0)
    async def chat_completion(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Union[dict, AsyncIterator[dict]]:
        """
        Create chat completion with caching and retry.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            tools: Optional list of tool definitions
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use caching (only for non-streaming)
            **kwargs: Additional parameters
        
        Returns:
            Response dictionary or async iterator for streaming
        """
        # Streaming responses cannot be cached
        if stream:
            use_cache = False
        
        # Try to get from cache first (non-streaming only)
        if use_cache and self.settings.LLM_CACHE_ENABLED:
            cached_response = await self.cache.get_llm_response(
                messages=messages,
                model=model,
                temperature=temperature,
                tools=tools,
                **kwargs
            )
            
            if cached_response:
                logger.info(
                    "llm_cache_hit",
                    model=model,
                    message_count=len(messages)
                )
                return cached_response
        
        # Make actual API call with timeout
        try:
            response = await asyncio.wait_for(
                self.client.chat_completions(
                    messages=messages,
                    model=model,
                    tools=tools,
                    stream=stream,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                ),
                timeout=self.settings.LLM_REQUEST_TIMEOUT
            )
            
            # Cache non-streaming responses
            if use_cache and not stream and self.settings.LLM_CACHE_ENABLED:
                await self.cache.set_llm_response(
                    messages=messages,
                    model=model,
                    response=response,
                    temperature=temperature,
                    ttl=self.settings.LLM_CACHE_TTL,
                    tools=tools,
                    **kwargs
                )
            
            logger.info(
                "llm_call_success",
                model=model,
                stream=stream,
                has_tools=tools is not None,
                cached=False
            )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(
                "llm_call_timeout",
                model=model,
                timeout=self.settings.LLM_REQUEST_TIMEOUT,
                message_count=len(messages)
            )
            raise
        except Exception as e:
            logger.error(
                "llm_call_failed",
                model=model,
                error=str(e),
                error_type=type(e).__name__,
                message_count=len(messages)
            )
            raise
    
    async def create_embedding(
        self,
        text: Union[str, list[str]],
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> list[float]:
        """
        Create embeddings for text with caching.
        
        Args:
            text: Text or list of texts to embed
            model: Embedding model name (uses default if None)
            use_cache: Whether to use caching
        
        Returns:
            List of embedding vectors
        """
        model = model or self.settings.EMBEDDING_MODEL
        
        # Generate cache key for embeddings
        cache_key = None
        if use_cache and self.settings.LLM_CACHE_ENABLED:
            cache_key = self.cache._generate_key("embedding", text, model)
            cached = await self.cache.get(cache_key)
            
            if cached:
                import json
                logger.info("embedding_cache_hit", model=model)
                return json.loads(cached)
        
        # Create embeddings
        try:
            response = await asyncio.wait_for(
                self.client.create_embedding(text, model),
                timeout=self.settings.LLM_REQUEST_TIMEOUT
            )
            
            # Extract embeddings from response
            embeddings = [item["embedding"] for item in response["data"]]
            
            # Cache the result
            if use_cache and cache_key and self.settings.LLM_CACHE_ENABLED:
                import json
                await self.cache.set(
                    cache_key,
                    json.dumps(embeddings),
                    ttl=self.settings.LLM_CACHE_TTL
                )
            
            logger.info(
                "embedding_created",
                model=model,
                text_count=len(text) if isinstance(text, list) else 1
            )
            
            return embeddings
            
        except asyncio.TimeoutError:
            logger.error(
                "embedding_timeout",
                model=model,
                timeout=self.settings.LLM_REQUEST_TIMEOUT
            )
            raise
        except Exception as e:
            logger.error(
                "embedding_failed",
                model=model,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def summarize_text(
        self,
        text: str,
        max_length: int = 200,
        model: Optional[str] = None
    ) -> str:
        """
        Summarize text using LLM.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            model: Model to use (uses default if None)
        
        Returns:
            Summary text
        """
        model = model or self.settings.OPENAI_MODEL
        
        messages = [
            {
                "role": "system",
                "content": "你是一个擅长总结的助手。请用简洁的中文总结以下内容，保留关键信息。"
            },
            {
                "role": "user",
                "content": f"请总结以下内容（不超过{max_length}字）：\n\n{text[:6000]}"
            }
        ]
        
        try:
            response = await self.chat_completion(
                messages=messages,
                model=model,
                temperature=0.3,  # Lower temperature for more focused summaries
                max_tokens=max_length * 2,  # Account for token vs character difference
                use_cache=True
            )
            
            summary = response["choices"][0]["message"]["content"].strip()
            
            # Truncate if needed
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            logger.info(
                "text_summarized",
                original_length=len(text),
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error("summarization_failed", error=str(e))
            # Fallback: return truncated original text
            return text[:max_length] + "..." if len(text) > max_length else text
    
    async def health_check(self) -> dict:
        """
        Check LLM service health.
        
        Returns:
            Health status dictionary
        """
        try:
            # Simple test request
            test_messages = [{"role": "user", "content": "test"}]
            await asyncio.wait_for(
                self.chat_completion(
                    messages=test_messages,
                    model=self.settings.OPENAI_MODEL,
                    max_tokens=5,
                    use_cache=False
                ),
                timeout=10
            )
            
            return {
                "status": "healthy",
                "model": self.settings.OPENAI_MODEL,
                "cache_enabled": self.settings.LLM_CACHE_ENABLED
            }
        except Exception as e:
            logger.error("llm_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
