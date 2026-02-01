"""
文件功能: 集成测试 - 验证 /api/v1/chat SSE 连续两次请求都能返回内容（避免只收到 ping）
文件路径: /Users/xinfuzhang/Desktop/Code/mac_agent/tests/test_chat_sse_twice.py

使用方式:
- 推荐（对照你当前复现环境，直接测本机已启动的后端）:
    cd /Users/xinfuzhang/Desktop/Code/mac_agent && pytest -q tests/test_chat_sse_twice.py -s

环境变量:
- BACKEND_BASE_URL: 默认 http://127.0.0.1:18888
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

import httpx


@dataclass(frozen=True)
class SseResult:
    got_ping: bool
    content_text: str
    events: list[dict[str, Any]]
    raw_lines_tail: list[str]


def _iter_sse_lines(response: httpx.Response) -> Iterable[str]:
    """
    httpx 流式响应按行读取（SSE 是 text/event-stream）。
    """
    for line in response.iter_lines():
        # httpx 会返回 str（默认 decode），这里统一 strip 但保留原始结构
        if line is None:
            continue
        yield line.rstrip("\n")


def _collect_sse(
    *,
    base_url: str,
    payload: dict[str, Any],
    timeout_s: float = 60.0,
    max_wait_s: float = 30.0,
) -> SseResult:
    """
    发起一次 SSE 请求，收集 ping/comment、event/data，并拼接所有 content 事件文本。

    重要: 这个测试故意“读完流”，以便判断后端是否在 ping 之后真正产出了 content。
    """
    url = f"{base_url.rstrip('/')}/api/v1/chat"
    got_ping = False
    current_event: str | None = None
    content_parts: list[str] = []
    events: list[dict[str, Any]] = []
    raw_lines: list[str] = []

    # SSE 往往需要更长连接，但“读不到任何数据”的情况必须能及时失败，避免测试卡死。
    # 这里将 read timeout 设为 max_wait_s：如果 max_wait_s 秒内没有收到任何字节，会抛 ReadTimeout。
    timeout = httpx.Timeout(timeout_s, read=max_wait_s)

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST",
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
            ) as resp:
                # SSE 一般返回 200；即使业务失败也可能还是 200 + event:error
                resp.raise_for_status()

                for line in _iter_sse_lines(resp):
                    raw_lines.append(line)

                    # SSE 注释/心跳（服务端用 ": ping"）
                    if line.startswith(":"):
                        if "ping" in line:
                            got_ping = True
                        continue

                    if line.startswith("event:"):
                        current_event = line[len("event:") :].strip()
                        continue

                    if line.startswith("data:"):
                        data_raw = line[len("data:") :].strip()
                        data: Any
                        try:
                            data = json.loads(data_raw) if data_raw else None
                        except json.JSONDecodeError:
                            data = data_raw

                        ev = {
                            "event": current_event or "message",
                            "data": data,
                        }
                        events.append(ev)

                        if (current_event or "") == "content" and isinstance(data, str):
                            content_parts.append(data)
                        continue

                    # 空行表示一个事件结束，忽略即可
                    if not line.strip():
                        continue

                    # 其他杂项行也记录下来（便于排查）
                    events.append({"event": "unknown", "data": line})

    except httpx.ReadTimeout as e:
        # 读超时：说明连接建立了，但服务端在 max_wait_s 内没有继续推任何数据（常见于“只收到 ping 就卡住”）
        events.append({"event": "read_timeout", "data": str(e)})

    return SseResult(
        got_ping=got_ping,
        content_text="".join(content_parts),
        events=events,
        raw_lines_tail=raw_lines[-60:],
    )


def test_chat_sse_second_request_returns_content():
    """
    连续两次 SSE 请求都应该收到 content（而不是只有 : ping）。
    """
    base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:18888")
    user_id = str(uuid.uuid4())
    
    # 重要：后端 chat 接口要求 session 必须已存在（与前端流程一致）
    with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
        init_resp = client.post(
            f"{base_url.rstrip('/')}/api/v1/session/init",
            headers={"Content-Type": "application/json"},
            json={"user_id": user_id, "active_session_id": None},
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        session_id = init_data["active_session_id"]

    payload1 = {
        "message": "你好",
        "model": None,
        "user_id": user_id,
        "session_id": session_id,
        "attachments": None,
        "stream": True,
        "tts_enabled": False,
        "tts_voice": "longyingtao_v3",
        "tts_model": "cosyvoice-v3-flash",
    }
    r1 = _collect_sse(base_url=base_url, payload=payload1)
    assert r1.got_ping is True, f"第一次请求未收到 ping，raw tail={r1.raw_lines_tail!r}"
    assert (
        r1.content_text.strip() != ""
    ), f"第一次请求未收到 content，events={r1.events!r}, raw tail={r1.raw_lines_tail!r}"

    payload2 = {
        **payload1,
        "message": "再说一次",
    }
    r2 = _collect_sse(base_url=base_url, payload=payload2)
    assert r2.got_ping is True, f"第二次请求未收到 ping，raw tail={r2.raw_lines_tail!r}"
    assert (
        r2.content_text.strip() != ""
    ), f"第二次请求未收到 content（疑似只收到 ping），events={r2.events!r}, raw tail={r2.raw_lines_tail!r}"

