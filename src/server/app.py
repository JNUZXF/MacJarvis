import json
import logging
import os
import sys
import time
import uuid
from dataclasses import replace
from pathlib import Path
import threading
from typing import Iterator

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.core.agent import Agent
from agent.core.client import OpenAIClient
from agent.core.config import ALLOWED_MODELS, is_model_allowed, load_openai_config, with_model
from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry
from agent.tools.validators import normalize_path, reset_runtime_allowed_roots, set_runtime_allowed_roots

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("mac_agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


def now_ms() -> int:
    return int(time.time() * 1000)


def log_event(level: int, event: str, **fields: object) -> None:
    payload = {"event": event, "ts": now_ms(), **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False))


def create_session_title(content: str) -> str:
    trimmed = content.strip()
    if not trimmed:
        return "新会话"
    return trimmed[:24] + "..." if len(trimmed) > 24 else trimmed


def create_message(role: str, content: str, tool_calls: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "toolCalls": tool_calls or [],
    }


def create_session(title: str) -> dict[str, object]:
    now = now_ms()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "createdAt": now,
        "updatedAt": now,
    }


USER_STORE: dict[str, dict[str, object]] = {}
USER_PATHS_LOCK = threading.Lock()
DATA_DIR = Path(__file__).resolve().parents[2] / "backend_data"
USER_PATHS_FILE = DATA_DIR / "user_paths.json"


def build_system_prompt(user_paths: list[str]) -> str:
    if not user_paths:
        paths_text = "未配置用户白名单。仅允许默认安全路径。"
    else:
        lines = "\n".join(f"- {path}" for path in user_paths)
        paths_text = f"用户已配置可访问路径：\n{lines}"
    return f"{BASE_SYSTEM_PROMPT}\n\n{paths_text}".strip()


def load_user_paths_store() -> dict[str, object]:
    if not USER_PATHS_FILE.exists():
        return {"version": 1, "users": {}}
    try:
        with USER_PATHS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "users" not in data:
            return {"version": 1, "users": {}}
        if not isinstance(data.get("users"), dict):
            return {"version": 1, "users": {}}
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "users": {}}


def save_user_paths_store(data: dict[str, object]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = USER_PATHS_FILE.with_suffix(".json.tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_file.replace(USER_PATHS_FILE)


def normalize_user_paths(raw_paths: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_paths:
        if not raw or not str(raw).strip():
            continue
        try:
            path = normalize_path(str(raw).strip())
        except OSError:
            continue
        if path.as_posix() == "/":
            continue
        if not path.exists() or not path.is_dir():
            continue
        path_str = str(path)
        if path_str in seen:
            continue
        normalized.append(path_str)
        seen.add(path_str)
    return normalized


def get_user_paths(user_id: str) -> list[str]:
    with USER_PATHS_LOCK:
        store = load_user_paths_store()
        users = store.get("users", {})
        if isinstance(users, dict):
            paths = users.get(user_id, [])
            if isinstance(paths, list):
                return [str(item) for item in paths]
    return []


def set_user_paths(user_id: str, paths: list[str]) -> list[str]:
    normalized = normalize_user_paths(paths)
    with USER_PATHS_LOCK:
        store = load_user_paths_store()
        users = store.get("users")
        if not isinstance(users, dict):
            users = {}
            store["users"] = users
        users[user_id] = normalized
        save_user_paths_store(store)
    return normalized


def get_or_create_user(user_id: str | None) -> tuple[str, dict[str, object]]:
    if user_id and user_id in USER_STORE:
        return user_id, USER_STORE[user_id]
    new_user_id = user_id or str(uuid.uuid4())
    if new_user_id not in USER_STORE:
        USER_STORE[new_user_id] = {"sessions": {}, "active_session_id": ""}
    return new_user_id, USER_STORE[new_user_id]


def ensure_session(user_state: dict[str, object], session_id: str | None, title_hint: str | None = None) -> str:
    sessions = user_state["sessions"]
    if isinstance(sessions, dict) and session_id and session_id in sessions:
        return session_id
    title = title_hint or "新会话"
    session = create_session(title)
    sessions[session["id"]] = session
    user_state["active_session_id"] = session["id"]
    return session["id"]


def list_sessions(user_state: dict[str, object]) -> list[dict[str, object]]:
    sessions = list(user_state.get("sessions", {}).values())
    sessions.sort(key=lambda item: item.get("updatedAt", 0), reverse=True)
    return sessions

# SSE响应头配置
def add_sse_headers(response: StreamingResponse) -> StreamingResponse:
    """为SSE响应添加必要的响应头"""
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response

# 全局异常处理器 - 确保所有错误都返回SSE格式
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，将错误转换为SSE格式"""
    # 如果是/api/chat端点，返回SSE格式的错误
    if request.url.path == "/api/chat":
        error_message = f"Server error: {str(exc)}"
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps(error_message)}\n\n"]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    # 其他端点返回JSON格式
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )

# 请求验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证错误处理器"""
    if request.url.path == "/api/chat":
        error_message = f"Invalid request: {str(exc)}"
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps(error_message)}\n\n"]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )

# HTTP异常处理器（包括404）
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器（包括404）"""
    if request.url.path.startswith("/api/"):
        error_message = f"API error ({exc.status_code}): {exc.detail}"
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps(error_message)}\n\n"]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Initialize shared config and tools
try:
    config = load_openai_config()
    registry = ToolRegistry(build_default_tools())
    
    BASE_SYSTEM_PROMPT = """你是一个专业的 macOS 智能助手，可以帮助用户管理系统、排查问题、执行自动化任务。
你可以使用提供的工具来获取信息或执行操作。
在执行具有潜在风险的操作（如删除文件、修改系统设置）前，请务必仔细确认路径和参数。
请用中文回复用户。
"""
    
except Exception as e:
    print(f"Warning: Agent initialization failed: {e}")
    config = None
    registry = None
    BASE_SYSTEM_PROMPT = ""

class ChatRequest(BaseModel):
    message: str
    model: str | None = None
    user_id: str | None = None
    session_id: str | None = None


class SessionInitRequest(BaseModel):
    user_id: str | None = None
    active_session_id: str | None = None


class SessionCreateRequest(BaseModel):
    user_id: str
    title: str | None = None


class UserPathsRequest(BaseModel):
    user_id: str
    paths: list[str]

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "macjarvis-backend"}


@app.post("/api/session/init")
async def init_session(request: SessionInitRequest):
    user_id, user_state = get_or_create_user(request.user_id)
    sessions = user_state["sessions"]
    if isinstance(sessions, dict) and not sessions:
        session_id = ensure_session(user_state, None)
    else:
        session_id = request.active_session_id or user_state.get("active_session_id", "")
        if session_id and session_id not in sessions:
            session_id = ensure_session(user_state, None)
        if not session_id and sessions:
            session_id = list_sessions(user_state)[0]["id"]
            user_state["active_session_id"] = session_id
    log_event(logging.INFO, "session_init", user_id=user_id, session_id=session_id)
    return {
        "user_id": user_id,
        "active_session_id": session_id,
        "sessions": list_sessions(user_state),
    }


@app.post("/api/session/new")
async def create_session_endpoint(request: SessionCreateRequest):
    user_id, user_state = get_or_create_user(request.user_id)
    session_id = ensure_session(user_state, None, title_hint=request.title or "新会话")
    session = user_state["sessions"][session_id]
    log_event(logging.INFO, "session_new", user_id=user_id, session_id=session_id)
    return session


@app.get("/api/session/{session_id}")
async def get_session(session_id: str, user_id: str):
    stored_user_id, user_state = get_or_create_user(user_id)
    sessions = user_state["sessions"]
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    user_state["active_session_id"] = session_id
    log_event(logging.INFO, "session_load", user_id=stored_user_id, session_id=session_id)
    return sessions[session_id]


@app.get("/api/user/paths")
async def get_user_paths_endpoint(user_id: str):
    stored_user_id, _ = get_or_create_user(user_id)
    paths = get_user_paths(stored_user_id)
    return {"user_id": stored_user_id, "paths": paths}


@app.post("/api/user/paths")
async def set_user_paths_endpoint(request: UserPathsRequest):
    stored_user_id, _ = get_or_create_user(request.user_id)
    normalized = set_user_paths(stored_user_id, request.paths)
    return {"user_id": stored_user_id, "paths": normalized}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not config or not registry:
        return add_sse_headers(StreamingResponse(
            iter([f"event: error\ndata: {json.dumps('Agent not initialized')}\n\n"]),
            media_type="text/event-stream"
        ))

    selected_model = (request.model or config.model).strip()
    if not is_model_allowed(selected_model):
        return add_sse_headers(StreamingResponse(
            iter([f"event: error\ndata: {json.dumps('Unsupported model')}\n\n"]),
            media_type="text/event-stream"
        ))

    user_id, user_state = get_or_create_user(request.user_id)
    session_id = ensure_session(user_state, request.session_id)
    session = user_state["sessions"][session_id]
    user_state["active_session_id"] = session_id
    user_paths = get_user_paths(user_id)

    request_config = with_model(config, selected_model)
    client = OpenAIClient(request_config)
    system_prompt = build_system_prompt(user_paths)
    agent = Agent(client, registry, system_prompt)

    def event_generator() -> Iterator[str]:
        # 立即发送 SSE 注释，避免客户端等待首包超时
        yield ": ping\n\n"
        token = set_runtime_allowed_roots([Path(path) for path in user_paths])
        try:
            message_title = create_session_title(request.message)
            if session.get("title") == "新会话" and not session.get("messages"):
                session["title"] = message_title
            user_message = create_message("user", request.message)
            assistant_message = create_message("assistant", "", [])
            session["messages"].append(user_message)
            session["messages"].append(assistant_message)
            session["updatedAt"] = now_ms()
            tool_index: dict[str, int] = {}

            log_event(
                logging.INFO,
                "chat_start",
                user_id=user_id,
                session_id=session_id,
                model=selected_model,
                message_length=len(request.message),
            )
            for event in agent.run_stream(request.message, request_config.max_tool_turns):
                if event["type"] == "content":
                    # Using json.dumps to handle escaping newlines etc.
                    assistant_message["content"] += event["content"]
                    session["updatedAt"] = now_ms()
                    yield f"event: content\ndata: {json.dumps(event['content'])}\n\n"
                elif event["type"] == "tool_start":
                    data = {
                        "name": event["name"],
                        "args": event["args"],
                        "tool_call_id": event["tool_call_id"]
                    }
                    tool_call = {
                        "id": event["tool_call_id"],
                        "name": event["name"],
                        "args": event["args"],
                        "status": "running",
                    }
                    tool_index[event["tool_call_id"]] = len(assistant_message["toolCalls"])
                    assistant_message["toolCalls"].append(tool_call)
                    session["updatedAt"] = now_ms()
                    log_event(
                        logging.INFO,
                        "tool_start",
                        user_id=user_id,
                        session_id=session_id,
                        tool_name=event["name"],
                        tool_call_id=event["tool_call_id"],
                    )
                    yield f"event: tool_start\ndata: {json.dumps(data)}\n\n"
                elif event["type"] == "tool_result":
                    data = {
                        "result": event["result"],
                        "tool_call_id": event["tool_call_id"]
                    }
                    tool_pos = tool_index.get(event["tool_call_id"])
                    if tool_pos is not None:
                        tool_call = assistant_message["toolCalls"][tool_pos]
                        tool_call["result"] = event["result"]
                        tool_call["status"] = "failed" if isinstance(event["result"], dict) and event["result"].get("ok") is False else "completed"
                    session["updatedAt"] = now_ms()
                    log_event(
                        logging.INFO,
                        "tool_result",
                        user_id=user_id,
                        session_id=session_id,
                        tool_call_id=event["tool_call_id"],
                        ok=isinstance(event["result"], dict) and event["result"].get("ok", True),
                    )
                    yield f"event: tool_result\ndata: {json.dumps(data, default=str)}\n\n"
        except Exception as e:
            log_event(
                logging.ERROR,
                "chat_error",
                user_id=user_id,
                session_id=session_id,
                error=str(e),
            )
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
        finally:
            reset_runtime_allowed_roots(token)
            session["updatedAt"] = now_ms()
            log_event(
                logging.INFO,
                "chat_end",
                user_id=user_id,
                session_id=session_id,
            )

    return add_sse_headers(StreamingResponse(
        event_generator(), 
        media_type="text/event-stream"
    ))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
