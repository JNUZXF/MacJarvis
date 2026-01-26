import json
from typing import Any, Iterator, Literal, TypedDict, Union

from agent.core.client import OpenAIClient
from agent.tools.registry import ToolRegistry


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

    def run_stream(self, user_input: str, max_tool_turns: int) -> Iterator[AgentEvent]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
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

                try:
                    args = json.loads(arguments_text) if arguments_text else {}
                except json.JSONDecodeError:
                    args = {}
                    result = {"ok": False, "error": "Invalid JSON arguments"}
                else:
                    yield {"type": "tool_start", "tool_call_id": tool_call_id, "name": name, "args": args}
                    try:
                        result = self.registry.execute(name, args)
                    except Exception as exc:
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

    def run(self, user_input: str, max_tool_turns: int) -> str:
        full_content = ""
        for event in self.run_stream(user_input, max_tool_turns):
            if event["type"] == "content":
                full_content += event["content"]
        return full_content
