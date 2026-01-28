# File: backend/agent/core/agent.py
# Purpose: Provide the core agent loop with streaming, tools, and context injection.
import json
import logging
from typing import Any, Iterator, Literal, TypedDict, Union

from agent.core.client import OpenAIClient
from agent.tools.registry import ToolRegistry

logger = logging.getLogger("mac_agent.agent")


class ContentEvent(TypedDict):
    type: Literal["content"]
    content: str


class ToolStartEvent(TypedDict):
    type: Literal["tool_start"]
    tool_call_id: str
    name: str
    args: dict[str, Any]


class ToolResultEvent(TypedDict):
    type: Literal["tool_result"]
    tool_call_id: str
    result: Any


AgentEvent = Union[ContentEvent, ToolStartEvent, ToolResultEvent]


class Agent:
    def __init__(self, client: OpenAIClient, registry: ToolRegistry, system_prompt: str) -> None:
        self.client = client
        self.registry = registry
        self.system_prompt = system_prompt

    def run_stream(
        self,
        user_input: Any,
        max_tool_turns: int,
        extra_system_prompt: str | None = None,
        extra_messages: list[dict[str, Any]] | None = None,
    ) -> Iterator[AgentEvent]:
        system_content = self.system_prompt
        if extra_system_prompt:
            system_content = f"{system_content}\n\n{extra_system_prompt}"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
        ]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_input})

        tools = self.registry.openai_tools()

        for _ in range(max_tool_turns):
            stream = self.client.chat_completions(messages, tools, stream=True)

            current_content = ""
            # index -> {id, name, args_str}
            current_tool_calls: dict[int, dict[str, str]] = {}

            for chunk in stream:
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta", {})

                # Handle content
                content = delta.get("content")
                if content:
                    current_content += content
                    yield {"type": "content", "content": content}

                # Handle tool calls
                tool_calls_delta = delta.get("tool_calls")
                if tool_calls_delta:
                    for tc in tool_calls_delta:
                        index = tc.get("index", 0)
                        if index not in current_tool_calls:
                            current_tool_calls[index] = {"id": "", "name": "", "arguments": ""}

                        if tc.get("id"):
                            current_tool_calls[index]["id"] = tc.get("id")
                        if tc.get("function", {}).get("name"):
                            current_tool_calls[index]["name"] = tc.get("function").get("name")
                        if tc.get("function", {}).get("arguments"):
                            current_tool_calls[index]["arguments"] += tc.get("function").get("arguments")

            message = {
                "role": "assistant",
                "content": current_content if current_content else None,
            }

            if not current_tool_calls:
                messages.append(message)
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

            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name", "")
                arguments_text = function.get("arguments", "{}")
                tool_call_id = call.get("id", "")

                # 添加日志：记录原始参数
                logger.debug(f"Tool call: {name}, raw arguments: {arguments_text[:200]}")

                try:
                    args = json.loads(arguments_text) if arguments_text else {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments for {name}: {e}, raw: {arguments_text[:200]}")
                    args = {}
                    result = {"ok": False, "error": f"Invalid JSON arguments: {str(e)}"}
                else:
                    # 添加日志：记录解析后的参数
                    logger.debug(f"Parsed args for {name}: {json.dumps(args, ensure_ascii=False)[:200]}")
                    yield {"type": "tool_start", "tool_call_id": tool_call_id, "name": name, "args": args}
                    try:
                        result = self.registry.execute(name, args)
                        logger.debug(f"Tool {name} execution result: ok={result.get('ok', False)}")
                    except Exception as exc:
                        logger.error(f"Tool {name} execution failed: {type(exc).__name__}: {str(exc)}")
                        result = {
                            "ok": False,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        }

                yield {"type": "tool_result", "tool_call_id": tool_call_id, "result": result}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        # Max turns exceeded
        yield {"type": "content", "content": "\n\n[System: Max tool turns exceeded]"}

    def run(self, user_input: Any, max_tool_turns: int) -> str:
        full_content = ""
        for event in self.run_stream(user_input, max_tool_turns):
            if event["type"] == "content":
                full_content += event["content"]
        return full_content
