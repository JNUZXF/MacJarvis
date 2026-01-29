# File: backend/agent/api_service.py
# Purpose: API service wrapper for Mac Agent
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/agent/api_service.py

"""
Mac Agent API Service

这个模块提供了一个便于集成到 FastAPI 的服务层，
封装了 Mac Agent 的核心功能，并提供了异步接口。

使用示例:
    >>> from agent.api_service import MacAgentService
    >>> 
    >>> # 创建服务
    >>> service = MacAgentService()
    >>> 
    >>> # 流式处理
    >>> async for event in service.process_stream(
    >>>     user_input="查看系统信息",
    >>>     user_id="user123",
    >>>     allowed_paths=["/Users/user/Documents"]
    >>> ):
    >>>     print(event)
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Optional

from agent.mac_agent import MacAgent, create_mac_agent
from agent.prompts import build_extra_system_prompt

logger = logging.getLogger("mac_agent.api_service")


class MacAgentService:
    """
    Mac Agent API Service
    
    提供异步接口用于集成到 FastAPI 应用中。
    
    Features:
        - 异步流式响应
        - 用户路径访问控制
        - 附件和记忆上下文支持
        - 自动资源管理
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        default_max_tool_turns: int = 5,
    ):
        """
        初始化 API 服务
        
        Args:
            model: 默认使用的模型
            default_max_tool_turns: 默认最大工具调用轮数
        """
        self.model = model
        self.default_max_tool_turns = default_max_tool_turns
        
        logger.info(
            "MacAgentService initialized",
            extra={
                "model": model,
                "default_max_tool_turns": default_max_tool_turns,
            }
        )
    
    async def process_stream(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        allowed_paths: Optional[list[str]] = None,
        attachment_context: str = "",
        memory_context: str = "",
        custom_instructions: str = "",
        extra_messages: Optional[list[dict[str, Any]]] = None,
        max_tool_turns: Optional[int] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        异步流式处理用户请求
        
        Args:
            user_input: 用户输入
            user_id: 用户ID（用于日志）
            allowed_paths: 允许访问的路径列表
            attachment_context: 附件上下文
            memory_context: 记忆上下文
            custom_instructions: 自定义指令
            extra_messages: 额外的历史消息
            max_tool_turns: 最大工具调用轮数
            model: 使用的模型（覆盖默认模型）
        
        Yields:
            事件字典（type, content/name/args/result）
        
        Example:
            >>> service = MacAgentService()
            >>> async for event in service.process_stream("查看系统信息"):
            >>>     print(event)
        """
        # Create agent with user's allowed paths
        agent = create_mac_agent(
            model=model or self.model,
            allowed_paths=allowed_paths,
        )
        
        # Build extra system prompt
        extra_prompt = build_extra_system_prompt(
            attachment_context=attachment_context,
            memory_context=memory_context,
            custom_instructions=custom_instructions,
        )
        
        # Get max tool turns
        turns = max_tool_turns if max_tool_turns is not None else self.default_max_tool_turns
        
        logger.info(
            "Starting stream processing",
            extra={
                "user_id": user_id,
                "user_input_length": len(user_input),
                "allowed_paths_count": len(allowed_paths) if allowed_paths else 0,
                "has_attachment": bool(attachment_context),
                "has_memory": bool(memory_context),
                "max_tool_turns": turns,
                "model": model or self.model,
            }
        )
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def sync_stream():
                """Synchronous generator wrapper"""
                for event in agent.run_stream(
                    user_input=user_input,
                    max_tool_turns=turns,
                    extra_system_prompt=extra_prompt if extra_prompt else None,
                    extra_messages=extra_messages,
                ):
                    yield event
            
            # Convert sync generator to async
            for event in sync_stream():
                yield event
                # Allow other tasks to run
                await asyncio.sleep(0)
        
        except Exception as e:
            logger.error(
                "Stream processing error",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def process(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        allowed_paths: Optional[list[str]] = None,
        max_tool_turns: Optional[int] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        异步非流式处理用户请求
        
        Args:
            user_input: 用户输入
            user_id: 用户ID（用于日志）
            allowed_paths: 允许访问的路径列表
            max_tool_turns: 最大工具调用轮数
            model: 使用的模型
        
        Returns:
            完整的响应内容
        
        Example:
            >>> service = MacAgentService()
            >>> result = await service.process("查看系统信息")
            >>> print(result)
        """
        # Create agent
        agent = create_mac_agent(
            model=model or self.model,
            allowed_paths=allowed_paths,
        )
        
        # Get max tool turns
        turns = max_tool_turns if max_tool_turns is not None else self.default_max_tool_turns
        
        logger.info(
            "Starting non-stream processing",
            extra={
                "user_id": user_id,
                "user_input_length": len(user_input),
                "max_tool_turns": turns,
            }
        )
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                agent.run,
                user_input,
                turns
            )
            return result
        
        except Exception as e:
            logger.error(
                "Processing error",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise
    
    def get_tools_info(self) -> list[dict[str, Any]]:
        """
        获取所有工具的信息
        
        Returns:
            工具信息列表
        """
        # Create a temporary agent to get tools info
        agent = create_mac_agent(model=self.model)
        return agent.get_tools_info()
    
    def get_tools_count(self) -> int:
        """
        获取工具数量
        
        Returns:
            工具数量
        """
        agent = create_mac_agent(model=self.model)
        return agent.get_tools_count()


# ============================================================================
# Singleton Instance - 单例实例
# ============================================================================

_service_instance: Optional[MacAgentService] = None


def get_mac_agent_service(
    model: Optional[str] = None,
    force_new: bool = False,
) -> MacAgentService:
    """
    获取 Mac Agent Service 单例
    
    Args:
        model: 模型名称
        force_new: 是否强制创建新实例
    
    Returns:
        MacAgentService 实例
    
    Example:
        >>> service = get_mac_agent_service()
        >>> async for event in service.process_stream("查看系统信息"):
        >>>     print(event)
    """
    global _service_instance
    
    if force_new or _service_instance is None:
        _service_instance = MacAgentService(model=model)
        logger.info("Created new MacAgentService instance")
    
    return _service_instance


# ============================================================================
# Module-level API - 模块级 API
# ============================================================================

__all__ = [
    "MacAgentService",
    "get_mac_agent_service",
]
