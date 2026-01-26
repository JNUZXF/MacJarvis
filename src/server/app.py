import json
import os
import sys
from dataclasses import replace
from typing import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.core.agent import Agent
from agent.core.client import OpenAIClient
from agent.core.config import ALLOWED_MODELS, is_model_allowed, load_openai_config, with_model
from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize shared config and tools
try:
    config = load_openai_config()
    registry = ToolRegistry(build_default_tools())
    
    SYSTEM_PROMPT = """你是一个专业的 macOS 智能助手，可以帮助用户管理系统、排查问题、执行自动化任务。
你可以使用提供的工具来获取信息或执行操作。
在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数。
请用中文回复用户。
"""
    
except Exception as e:
    print(f"Warning: Agent initialization failed: {e}")
    config = None
    registry = None
    SYSTEM_PROMPT = ""

class ChatRequest(BaseModel):
    message: str
    model: str | None = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not config or not registry:
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps('Agent not initialized')}\n\n"]),
            media_type="text/event-stream"
        )

    selected_model = (request.model or config.model).strip()
    if not is_model_allowed(selected_model):
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps('Unsupported model')}\n\n"]),
            media_type="text/event-stream"
        )

    request_config = with_model(config, selected_model)
    client = OpenAIClient(request_config)
    agent = Agent(client, registry, SYSTEM_PROMPT)

    def event_generator() -> Iterator[str]:
        try:
            for event in agent.run_stream(request.message, request_config.max_tool_turns):
                if event["type"] == "content":
                    # Using json.dumps to handle escaping newlines etc.
                    yield f"event: content\ndata: {json.dumps(event['content'])}\n\n"
                elif event["type"] == "tool_start":
                    data = {
                        "name": event["name"],
                        "args": event["args"],
                        "tool_call_id": event["tool_call_id"]
                    }
                    yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                elif event["type"] == "tool_result":
                    data = {
                        "result": event["result"],
                        "tool_call_id": event["tool_call_id"]
                    }
                    yield f"event: tool_result\ndata: {json.dumps(data, default=str)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
