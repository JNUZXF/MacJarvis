# File: backend/agent/mac_agent.py
# Purpose: Unified Mac Agent interface with tools and prompts
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/agent/mac_agent.py

"""
Mac Agent - 统一的 macOS 智能助手接口

这个模块提供了一个统一的接口来创建和使用 Mac Agent，
包括工具注册、提示词管理和流式响应。

使用示例:
    >>> from agent.mac_agent import MacAgent
    >>> 
    >>> # 创建 Agent
    >>> mac_agent = MacAgent()
    >>> 
    >>> # 流式执行
    >>> for event in mac_agent.run_stream("查看系统信息"):
    >>>     if event["type"] == "content":
    >>>         print(event["content"], end="", flush=True)
    >>> 
    >>> # 非流式执行
    >>> result = mac_agent.run("列出当前目录")
    >>> print(result)
"""

import logging
from typing import Any, Iterator, Optional

from agent.core.agent import Agent, AgentEvent
from agent.core.client import OpenAIClient
from agent.core.config import OpenAIConfig, load_openai_config
from agent.prompts import BASE_SYSTEM_PROMPT, build_system_prompt_with_paths
from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry

logger = logging.getLogger("mac_agent")


class MacAgent:
    """
    Mac Agent - macOS 智能助手
    
    提供统一的接口来创建和使用 Mac Agent，包括：
    - 工具注册和管理
    - 提示词管理
    - 流式和非流式响应
    - 路径访问控制
    
    Attributes:
        client: OpenAI 客户端
        registry: 工具注册表
        agent: 核心 Agent 实例
        config: OpenAI 配置
    """
    
    def __init__(
        self,
        config: Optional[OpenAIConfig] = None,
        system_prompt: Optional[str] = None,
        allowed_paths: Optional[list[str]] = None,
        tools: Optional[list[Any]] = None,
    ):
        """
        初始化 Mac Agent
        
        Args:
            config: OpenAI 配置，如果为 None 则从环境变量加载
            system_prompt: 自定义系统提示词，如果为 None 则使用默认提示词
            allowed_paths: 允许访问的路径列表，用于路径访问控制
            tools: 自定义工具列表，如果为 None 则使用默认工具集
        """
        # Load config
        self.config = config or load_openai_config()
        
        # Initialize client
        self.client = OpenAIClient(self.config)
        
        # Build tools
        tool_list = tools if tools is not None else build_default_tools()
        self.registry = ToolRegistry(tool_list)
        
        # Build system prompt
        if system_prompt:
            self.system_prompt = system_prompt
        elif allowed_paths:
            self.system_prompt = build_system_prompt_with_paths(allowed_paths)
        else:
            self.system_prompt = BASE_SYSTEM_PROMPT
        
        # Initialize agent
        self.agent = Agent(self.client, self.registry, self.system_prompt)
        
        logger.info(
            "MacAgent initialized",
            extra={
                "model": self.config.model,
                "tools_count": len(tool_list),
                "has_custom_prompt": system_prompt is not None,
                "allowed_paths_count": len(allowed_paths) if allowed_paths else 0,
            }
        )
    
    def run_stream(
        self,
        user_input: str,
        max_tool_turns: Optional[int] = None,
        extra_system_prompt: Optional[str] = None,
        extra_messages: Optional[list[dict[str, Any]]] = None,
    ) -> Iterator[AgentEvent]:
        """
        流式执行用户请求
        
        Args:
            user_input: 用户输入
            max_tool_turns: 最大工具调用轮数，如果为 None 则使用配置中的值
            extra_system_prompt: 额外的系统提示词
            extra_messages: 额外的历史消息
        
        Yields:
            AgentEvent: Agent 事件（content, tool_start, tool_result）
        
        Example:
            >>> agent = MacAgent()
            >>> for event in agent.run_stream("查看系统信息"):
            >>>     if event["type"] == "content":
            >>>         print(event["content"], end="", flush=True)
        """
        turns = max_tool_turns if max_tool_turns is not None else self.config.max_tool_turns
        
        logger.debug(
            "Starting stream execution",
            extra={
                "user_input_length": len(user_input),
                "max_tool_turns": turns,
                "has_extra_prompt": extra_system_prompt is not None,
                "extra_messages_count": len(extra_messages) if extra_messages else 0,
            }
        )
        
        yield from self.agent.run_stream(
            user_input=user_input,
            max_tool_turns=turns,
            extra_system_prompt=extra_system_prompt,
            extra_messages=extra_messages,
        )
    
    def run(
        self,
        user_input: str,
        max_tool_turns: Optional[int] = None,
    ) -> str:
        """
        非流式执行用户请求
        
        Args:
            user_input: 用户输入
            max_tool_turns: 最大工具调用轮数，如果为 None 则使用配置中的值
        
        Returns:
            完整的响应内容
        
        Example:
            >>> agent = MacAgent()
            >>> result = agent.run("列出当前目录")
            >>> print(result)
        """
        turns = max_tool_turns if max_tool_turns is not None else self.config.max_tool_turns
        
        logger.debug(
            "Starting non-stream execution",
            extra={
                "user_input_length": len(user_input),
                "max_tool_turns": turns,
            }
        )
        
        return self.agent.run(user_input, turns)
    
    def get_tools_info(self) -> list[dict[str, Any]]:
        """
        获取所有工具的信息
        
        Returns:
            工具信息列表
        
        Example:
            >>> agent = MacAgent()
            >>> tools = agent.get_tools_info()
            >>> for tool in tools:
            >>>     print(f"{tool['function']['name']}: {tool['function']['description']}")
        """
        return self.registry.openai_tools()
    
    def get_tools_count(self) -> int:
        """
        获取工具数量
        
        Returns:
            工具数量
        """
        return len(self.registry._tools)
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """
        更新系统提示词
        
        Args:
            new_prompt: 新的系统提示词
        """
        self.system_prompt = new_prompt
        self.agent.system_prompt = new_prompt
        logger.info("System prompt updated")
    
    def add_allowed_paths(self, paths: list[str]) -> None:
        """
        添加允许访问的路径（更新系统提示词）
        
        Args:
            paths: 要添加的路径列表
        """
        new_prompt = build_system_prompt_with_paths(paths)
        self.update_system_prompt(new_prompt)
        logger.info(f"Added {len(paths)} allowed paths")


# ============================================================================
# Factory Functions - 工厂函数
# ============================================================================

def create_mac_agent(
    model: Optional[str] = None,
    allowed_paths: Optional[list[str]] = None,
    **kwargs
) -> MacAgent:
    """
    创建 Mac Agent 的工厂函数
    
    Args:
        model: 模型名称（如 "gpt-4o-mini"）
        allowed_paths: 允许访问的路径列表
        **kwargs: 其他参数传递给 MacAgent
    
    Returns:
        MacAgent 实例
    
    Example:
        >>> agent = create_mac_agent(model="gpt-4o-mini")
        >>> result = agent.run("查看系统信息")
    """
    config = load_openai_config()
    if model:
        config.model = model
    
    return MacAgent(
        config=config,
        allowed_paths=allowed_paths,
        **kwargs
    )


def create_cli_agent() -> MacAgent:
    """
    创建用于 CLI 的 Mac Agent
    
    Returns:
        MacAgent 实例（使用 CLI 提示词）
    
    Example:
        >>> agent = create_cli_agent()
        >>> result = agent.run("查看系统信息")
    """
    from agent.prompts import CLI_SYSTEM_PROMPT
    
    return MacAgent(system_prompt=CLI_SYSTEM_PROMPT)


# ============================================================================
# Convenience Functions - 便捷函数
# ============================================================================

def quick_run(user_input: str, model: Optional[str] = None) -> str:
    """
    快速执行用户请求（非流式）
    
    Args:
        user_input: 用户输入
        model: 模型名称
    
    Returns:
        响应内容
    
    Example:
        >>> from agent.mac_agent import quick_run
        >>> result = quick_run("查看系统信息")
        >>> print(result)
    """
    agent = create_mac_agent(model=model)
    return agent.run(user_input)


def quick_stream(user_input: str, model: Optional[str] = None) -> Iterator[AgentEvent]:
    """
    快速执行用户请求（流式）
    
    Args:
        user_input: 用户输入
        model: 模型名称
    
    Yields:
        AgentEvent: Agent 事件
    
    Example:
        >>> from agent.mac_agent import quick_stream
        >>> for event in quick_stream("查看系统信息"):
        >>>     if event["type"] == "content":
        >>>         print(event["content"], end="", flush=True)
    """
    agent = create_mac_agent(model=model)
    yield from agent.run_stream(user_input)


# ============================================================================
# Module-level API - 模块级 API
# ============================================================================

__all__ = [
    "MacAgent",
    "create_mac_agent",
    "create_cli_agent",
    "quick_run",
    "quick_stream",
]
