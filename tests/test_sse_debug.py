"""
文件功能: SSE 流式响应调试测试 - 定位第二次请求失败的根本原因
文件路径: /Users/xinfuzhang/Desktop/Code/mac_agent/tests/test_sse_debug.py

这个测试会详细记录每次请求的完整过程，帮助定位问题
"""

import asyncio
import json
import httpx
import uuid
from typing import AsyncIterator


async def test_sse_stream_twice():
    """测试连续两次 SSE 流式请求"""
    base_url = "http://127.0.0.1:18888"
    user_id = str(uuid.uuid4())
    
    # 1. 初始化 session
    print("\n=== 步骤 1: 初始化 Session ===")
    async with httpx.AsyncClient(timeout=10.0) as client:
        init_resp = await client.post(
            f"{base_url}/api/v1/session/init",
            json={"user_id": user_id, "active_session_id": None},
        )
        init_resp.raise_for_status()
        session_id = init_resp.json()["active_session_id"]
        print(f"✓ Session ID: {session_id}")
    
    # 2. 第一次请求
    print("\n=== 步骤 2: 第一次 SSE 请求 ===")
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
    
    content1 = await collect_sse_content(base_url, payload1, "第一次")
    print(f"✓ 第一次请求收到内容: {content1[:50]}...")
    assert content1.strip(), "第一次请求应该有内容"
    
    # 等待一下，确保第一次请求完全结束
    await asyncio.sleep(1)
    
    # 3. 第二次请求
    print("\n=== 步骤 3: 第二次 SSE 请求 ===")
    payload2 = {**payload1, "message": "再说一次"}
    
    content2 = await collect_sse_content(base_url, payload2, "第二次")
    print(f"✓ 第二次请求收到内容: {content2[:50]}...")
    assert content2.strip(), "第二次请求应该有内容"
    
    print("\n=== ✅ 测试通过 ===")


async def collect_sse_content(
    base_url: str,
    payload: dict,
    label: str,
    timeout: float = 30.0
) -> str:
    """收集 SSE 流式响应的内容"""
    url = f"{base_url}/api/v1/chat"
    content_parts = []
    event_count = 0
    got_ping = False
    
    print(f"  → 发送 {label} 请求...")
    
    try:
        # 使用独立的 client，避免连接池问题
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, read=timeout)) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                print(f"  ✓ 连接建立 (status: {response.status_code})")
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # 记录原始行
                    if event_count < 5:  # 只打印前几行
                        print(f"    < {line[:80]}")
                    
                    # 处理 ping
                    if line.startswith(":"):
                        if "ping" in line:
                            got_ping = True
                            print(f"  ✓ 收到 ping")
                        continue
                    
                    # 处理事件
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                        continue
                    
                    # 处理数据
                    if line.startswith("data:"):
                        event_count += 1
                        data_raw = line[5:].strip()
                        
                        try:
                            data = json.loads(data_raw) if data_raw else None
                            if isinstance(data, str):
                                content_parts.append(data)
                                if event_count <= 3:
                                    print(f"  ✓ 收到内容: {data[:30]}...")
                        except json.JSONDecodeError:
                            pass
                
                print(f"  ✓ {label} 请求完成，收到 {event_count} 个事件")
    
    except httpx.ReadTimeout:
        print(f"  ✗ {label} 请求超时 (got_ping={got_ping}, events={event_count})")
        raise
    except Exception as e:
        print(f"  ✗ {label} 请求失败: {e}")
        raise
    
    return "".join(content_parts)


if __name__ == "__main__":
    asyncio.run(test_sse_stream_twice())
