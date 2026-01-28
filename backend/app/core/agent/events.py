# File: backend/app/core/agent/events.py
# Purpose: Type definitions for agent events
from typing import Any, Literal, TypedDict, Union


class ContentEvent(TypedDict):
    """Event for streaming content from LLM"""
    type: Literal["content"]
    content: str


class ToolStartEvent(TypedDict):
    """Event when tool execution starts"""
    type: Literal["tool_start"]
    tool_call_id: str
    name: str
    args: dict[str, Any]


class ToolResultEvent(TypedDict):
    """Event when tool execution completes"""
    type: Literal["tool_result"]
    tool_call_id: str
    result: Any


class ErrorEvent(TypedDict):
    """Event for errors"""
    type: Literal["error"]
    error: str
    error_type: str


# Union type for all agent events
AgentEvent = Union[ContentEvent, ToolStartEvent, ToolResultEvent, ErrorEvent]
