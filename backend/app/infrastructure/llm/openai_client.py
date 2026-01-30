# File: backend/app/infrastructure/llm/openai_client.py
# Purpose: OpenAI-compatible API client with streaming support
import json
from typing import Optional, AsyncIterator, Union
import structlog

from app.infrastructure.llm.client import LLMClient

logger = structlog.get_logger(__name__)


class OpenAIClient(LLMClient):
    """
    OpenAI-compatible API client.
    Supports both OpenAI and OpenRouter APIs.
    """
    
    async def chat_completions(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[dict, AsyncIterator[dict]]:
        """
        Create chat completion.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            tools: Optional list of tool definitions
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Response dictionary or async iterator for streaming
        """
        if stream:
            # For streaming, use the dedicated streaming method
            return self.chat_completions_stream(
                messages=messages,
                model=model,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        else:
            # For non-streaming, proceed with normal async call
            endpoint = "/chat/completions" if self.base_url.endswith("/v1") else "/v1/chat/completions"
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
                **kwargs
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            if tools:
                payload["tools"] = tools
            
            logger.debug(
                "llm_request_started",
                model=model,
                stream=False,
                message_count=len(messages),
                has_tools=tools is not None
            )
            
            return await self._complete(endpoint, payload)
    
    def chat_completions_stream(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[dict]:
        """
        Create streaming chat completion.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            tools: Optional list of tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Async iterator for streaming
        """
        endpoint = "/chat/completions" if self.base_url.endswith("/v1") else "/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
        
        logger.debug(
            "llm_request_started",
            model=model,
            stream=True,
            message_count=len(messages),
            has_tools=tools is not None
        )
        
        # Return the async generator directly
        return self._stream_completion(endpoint, payload)
    
    async def _complete(self, endpoint: str, payload: dict) -> dict:
        """Non-streaming completion"""
        response = await self._make_request("POST", endpoint, json=payload)
        result = response.json()
        
        logger.debug(
            "llm_response_received",
            model=payload["model"],
            finish_reason=result.get("choices", [{}])[0].get("finish_reason")
        )
        
        return result
    
    async def _stream_completion(self, endpoint: str, payload: dict) -> AsyncIterator[dict]:
        """Streaming completion"""
        async with self.client.stream("POST", f"{self.base_url}{endpoint}", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line or line.strip() == "":
                    continue
                
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        yield chunk
                    except json.JSONDecodeError as e:
                        logger.warning("llm_stream_decode_error", error=str(e), data=data[:100])
                        continue
    
    async def create_embedding(
        self,
        input_text: Union[str, list[str]],
        model: str = "text-embedding-3-small"
    ) -> dict:
        """
        Create embeddings for text.
        
        Args:
            input_text: Text or list of texts to embed
            model: Embedding model name
        
        Returns:
            Embedding response dictionary
        """
        endpoint = "/embeddings" if self.base_url.endswith("/v1") else "/v1/embeddings"
        
        payload = {
            "model": model,
            "input": input_text
        }
        
        response = await self._make_request("POST", endpoint, json=payload)
        return response.json()
