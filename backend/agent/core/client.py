# File: backend/agent/core/client.py
# Purpose: Provide OpenAI-compatible client utilities for backend runtime.
import json
from typing import Any, Iterator
import httpx

from agent.core.config import OpenAIConfig


class OpenAIClient:
    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config
        
        # 配置代理
        proxy = None
        if config.https_proxy:
            proxy = config.https_proxy
        elif config.http_proxy:
            proxy = config.http_proxy
        
        # 创建HTTP客户端,如果有代理则使用代理
        if proxy:
            self.http_client = httpx.Client(
                timeout=self.config.timeout_s,
                proxy=proxy
            )
        else:
            self.http_client = httpx.Client(timeout=self.config.timeout_s)

    def chat_completions(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Iterator[dict[str, Any]]:
        base_url = self.config.base_url.rstrip("/")
        if base_url.endswith("/v1"):
            url = f"{base_url}/chat/completions"
        else:
            url = f"{base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        if stream:
            return self._stream_request(url, headers, payload)

        try:
            response = self.http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    def _stream_request(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> Iterator[dict[str, Any]]:
        try:
            with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.strip():
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenAI stream failed: {exc}") from exc
