# File: backend/app/core/agent/orchestrator.py
# Purpose: Agent orchestrator for coordinating LLM, tools, and memory
import json
from typing import Any, AsyncIterator, Optional
import structlog

from app.infrastructure.llm.openai_client import OpenAIClient
from app.core.tools.registry import ToolRegistry
from app.core.agent.events import AgentEvent, ContentEvent, ToolStartEvent, ToolResultEvent
from app.config import Settings

logger = structlog.get_logger(__name__)


class AgentOrchestrator:
    """
    Agent orchestrator that coordinates:
    - LLM interactions
    - Tool execution
    - Streaming responses
    - Error handling
    """
    
    def __init__(
        self,
        client: OpenAIClient,
        registry: ToolRegistry,
        settings: Settings,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize agent orchestrator.
        
        Args:
            client: LLM client
            registry: Tool registry
            settings: Application settings
            system_prompt: Optional system prompt
        """
        self.client = client
        self.registry = registry
        self.settings = settings
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Get default system prompt"""
        return """你是一个专业的 macOS 智能助手，可以帮助用户管理系统、排查问题、执行自动化任务。
你可以使用提供的工具来获取信息或执行操作。
在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数。
请用中文回复用户。"""
    
    async def run_stream(
        self,
        user_input: Any,
        max_tool_turns: Optional[int] = None,
        extra_system_prompt: Optional[str] = None,
        extra_messages: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run agent with streaming response.
        
        Args:
            user_input: User input (text or multimodal)
            max_tool_turns: Maximum tool execution turns
            extra_system_prompt: Additional system prompt
            extra_messages: Additional messages for context
        
        Yields:
            Agent events (content, tool_start, tool_result)
        """
        max_turns = max_tool_turns or self.settings.OPENAI_MAX_TOOL_TURNS
        
        # Build system content
        system_content = self.system_prompt
        if extra_system_prompt:
            system_content = f"{system_content}\n\n{extra_system_prompt}"
        
        # Build messages
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
        ]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_input})
        
        # Get tools
        tools = self.registry.openai_tools()
        
        logger.info(
            "agent_run_started",
            max_turns=max_turns,
            tool_count=len(tools),
            message_count=len(messages)
        )
        
        # Agent loop
        for turn in range(max_turns):
            try:
                # Stream LLM response
                stream = await self.client.chat_completions(
                    messages=messages,
                    model=self.settings.OPENAI_MODEL,
                    tools=tools,
                    stream=True
                )
                
                current_content = ""
                current_tool_calls: dict[int, dict[str, str]] = {}
                
                # Process stream chunks
                async for chunk in stream:
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    
                    choice = choices[0]
                    delta = choice.get("delta", {})
                    
                    # Handle content
                    content = delta.get("content")
                    if content:
                        current_content += content
                        yield ContentEvent(type="content", content=content)
                    
                    # Handle tool calls
                    tool_calls_delta = delta.get("tool_calls")
                    if tool_calls_delta:
                        for tc in tool_calls_delta:
                            index = tc.get("index", 0)
                            if index not in current_tool_calls:
                                current_tool_calls[index] = {
                                    "id": "",
                                    "name": "",
                                    "arguments": ""
                                }
                            
                            if tc.get("id"):
                                current_tool_calls[index]["id"] = tc.get("id")
                            if tc.get("function", {}).get("name"):
                                current_tool_calls[index]["name"] = tc.get("function").get("name")
                            if tc.get("function", {}).get("arguments"):
                                current_tool_calls[index]["arguments"] += tc.get("function").get("arguments")
                
                # Build assistant message
                message = {
                    "role": "assistant",
                    "content": current_content if current_content else None,
                }
                
                # If no tool calls, we're done
                if not current_tool_calls:
                    messages.append(message)
                    logger.info(
                        "agent_run_completed",
                        turn=turn + 1,
                        response_length=len(current_content)
                    )
                    return
                
                # Reconstruct tool calls
                tool_calls = []
                for index in sorted(current_tool_calls.keys()):
                    tc_data = current_tool_calls[index]
                    tool_calls.append({
                        "id": tc_data["id"],
                        "type": "function",
                        "function": {
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"],
                        },
                    })
                
                message["tool_calls"] = tool_calls
                messages.append(message)
                
                # Execute tool calls
                for call in tool_calls:
                    function = call.get("function", {})
                    name = function.get("name", "")
                    arguments_text = function.get("arguments", "{}")
                    tool_call_id = call.get("id", "")
                    
                    try:
                        args = json.loads(arguments_text) if arguments_text else {}
                    except json.JSONDecodeError:
                        args = {}
                        result = {"ok": False, "error": "Invalid JSON arguments"}
                    else:
                        # Emit tool start event
                        yield ToolStartEvent(
                            type="tool_start",
                            tool_call_id=tool_call_id,
                            name=name,
                            args=args
                        )
                        
                        # Execute tool
                        try:
                            result = self.registry.execute(name, args)
                            logger.info(
                                "tool_executed",
                                tool_name=name,
                                tool_call_id=tool_call_id,
                                success=result.get("ok", True)
                            )
                        except Exception as exc:
                            result = {
                                "ok": False,
                                "error": str(exc),
                                "error_type": type(exc).__name__,
                            }
                            logger.error(
                                "tool_execution_failed",
                                tool_name=name,
                                tool_call_id=tool_call_id,
                                error=str(exc)
                            )
                    
                    # Emit tool result event
                    yield ToolResultEvent(
                        type="tool_result",
                        tool_call_id=tool_call_id,
                        result=result
                    )
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            
            except Exception as e:
                logger.error(
                    "agent_turn_failed",
                    turn=turn + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        # Max turns exceeded
        logger.warning("agent_max_turns_exceeded", max_turns=max_turns)
        yield ContentEvent(
            type="content",
            content="\n\n[System: Max tool turns exceeded]"
        )
    
    async def run(
        self,
        user_input: Any,
        max_tool_turns: Optional[int] = None
    ) -> str:
        """
        Run agent and return complete response.
        
        Args:
            user_input: User input
            max_tool_turns: Maximum tool execution turns
        
        Returns:
            Complete response text
        """
        full_content = ""
        async for event in self.run_stream(user_input, max_tool_turns):
            if event["type"] == "content":
                full_content += event["content"]
        return full_content
