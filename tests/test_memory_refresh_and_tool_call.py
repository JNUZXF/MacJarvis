"""
File Purpose: Integration tests for memory tool calls and refresh behavior.
File Path: /Users/xinfuzhang/Desktop/Code/mac_agent/tests/test_memory_refresh_and_tool_call.py
Usage:
  cd /Users/xinfuzhang/Desktop/Code/mac_agent && pytest -q tests/test_memory_refresh_and_tool_call.py -s
Environment:
  BACKEND_BASE_URL (default: http://127.0.0.1:18888)
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

import httpx


@dataclass(frozen=True)
class SseResult:
    got_ping: bool
    content_text: str
    events: list[dict[str, Any]]


def _iter_sse_lines(response: httpx.Response) -> Iterable[str]:
    for line in response.iter_lines():
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
    url = f"{base_url.rstrip('/')}/api/v1/chat"
    got_ping = False
    current_event: str | None = None
    content_parts: list[str] = []
    events: list[dict[str, Any]] = []

    timeout = httpx.Timeout(timeout_s, read=max_wait_s)

    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
        ) as resp:
            resp.raise_for_status()

            for line in _iter_sse_lines(resp):
                if line.startswith(":"):
                    if "ping" in line:
                        got_ping = True
                    continue

                if line.startswith("event:"):
                    current_event = line[len("event:") :].strip()
                    continue

                if line.startswith("data:"):
                    data_raw = line[len("data:") :].strip()
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

    return SseResult(
        got_ping=got_ping,
        content_text="".join(content_parts),
        events=events,
    )


def _init_session(base_url: str, user_id: str) -> str:
    with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
        resp = client.post(
            f"{base_url.rstrip('/')}/api/v1/session/init",
            headers={"Content-Type": "application/json"},
            json={"user_id": user_id, "active_session_id": None},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["active_session_id"]


def _send_chat_and_collect(
    base_url: str,
    user_id: str,
    session_id: str,
    message: str,
) -> SseResult:
    payload = {
        "message": message,
        "model": None,
        "user_id": user_id,
        "session_id": session_id,
        "attachments": None,
        "stream": True,
        "tts_enabled": False,
        "tts_voice": "longyingtao_v3",
        "tts_model": "cosyvoice-v3-flash",
    }
    return _collect_sse(base_url=base_url, payload=payload)


def _has_update_memory_tool_call(events: list[dict[str, Any]]) -> bool:
    for ev in events:
        if ev.get("event") == "tool_start":
            data = ev.get("data") or {}
            if data.get("name") == "update_memory":
                return True
    return False


def test_memory_tool_called_on_personal_info():
    base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:18888")
    user_id = str(uuid.uuid4())
    session_id = _init_session(base_url, user_id)

    r1 = _send_chat_and_collect(
        base_url,
        user_id,
        session_id,
        "请记住：我的爱好是打篮球。",
    )
    assert r1.got_ping is True, "SSE should return ping"
    assert r1.content_text.strip(), "SSE should return content"

    r2 = _send_chat_and_collect(
        base_url,
        user_id,
        session_id,
        "再补充：我也喜欢游泳。",
    )
    assert r2.got_ping is True, "SSE should return ping"
    assert r2.content_text.strip(), "SSE should return content"

    tool_called = _has_update_memory_tool_call(r1.events) or _has_update_memory_tool_call(
        r2.events
    )
    assert tool_called, "Expected update_memory tool to be called for personal info"


def test_refresh_memory_uses_all_conversations():
    base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:18888")
    user_id = str(uuid.uuid4())

    session_id_1 = _init_session(base_url, user_id)
    _send_chat_and_collect(
        base_url,
        user_id,
        session_id_1,
        "请记住：我的爱好是打篮球。",
    )

    session_id_2 = _init_session(base_url, user_id)
    _send_chat_and_collect(
        base_url,
        user_id,
        session_id_2,
        "请记住：我的爱好是游泳。",
    )

    with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
        resp = client.post(
            f"{base_url.rstrip('/')}/api/v1/memories/{user_id}/refresh",
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    for key in ["preferences", "facts", "episodes", "tasks", "relations"]:
        assert key in data, f"Missing memory key: {key}"

    combined = " ".join([str(data.get(k, "")) for k in data.keys()])
    assert "篮球" in combined, "Expected basketball hobby to appear in memory"
    assert "游泳" in combined, "Expected swimming hobby to appear in memory"
