#!/usr/bin/env python3
"""
File: backend/scripts/test_first_token_latency.py
Purpose: Test script to measure first token latency and validate optimizations

This script sends test requests to the chat endpoint and measures:
1. Time to first token
2. Total preparation time
3. Individual stage timings
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx


async def test_first_token_latency(base_url: str = "http://localhost:8000", num_tests: int = 3):
    """
    Test first token latency by sending chat requests.
    
    Args:
        base_url: Backend server URL
        num_tests: Number of test requests to send
    """
    print("=" * 80)
    print("首Token延迟测试")
    print("=" * 80)
    print()
    
    # Test data
    test_message = "你好，请简单介绍一下你自己。"
    test_user_id = "test_user_performance"
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(num_tests):
            print(f"\n{'='*60}")
            print(f"测试 #{i+1}/{num_tests}")
            print(f"{'='*60}")
            
            request_start = time.perf_counter()
            first_token_time = None
            total_tokens = 0
            
            try:
                # Send SSE request
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json={
                        "message": test_message,
                        "user_id": test_user_id,
                        "model": None,  # Use default
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ 请求失败: HTTP {response.status_code}")
                        continue
                    
                    # Process SSE stream
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        # Parse SSE event
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            data = line[6:].strip()
                            
                            # Record first token
                            if first_token_time is None and event_type == "content":
                                first_token_time = (time.perf_counter() - request_start) * 1000
                                print(f"\n⏱️  首Token时间: {first_token_time:.2f}ms")
                            
                            # Count content tokens
                            if event_type == "content":
                                total_tokens += 1
                                if total_tokens <= 3:
                                    try:
                                        content = json.loads(data)
                                        print(f"   Token #{total_tokens}: {repr(content[:50])}")
                                    except:
                                        pass
                            
                            # Stop after getting first few tokens
                            if total_tokens >= 5:
                                break
                    
                    # Record result
                    if first_token_time:
                        results.append(first_token_time)
                        print(f"\n✅ 测试完成: {first_token_time:.2f}ms")
                    else:
                        print(f"\n⚠️  未收到内容token")
                        
            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                continue
            
            # Wait between tests
            if i < num_tests - 1:
                print(f"\n等待2秒后进行下一次测试...")
                await asyncio.sleep(2)
    
    # Print summary
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    
    if results:
        avg_time = sum(results) / len(results)
        min_time = min(results)
        max_time = max(results)
        
        print(f"\n成功测试次数: {len(results)}/{num_tests}")
        print(f"平均首Token时间: {avg_time:.2f}ms")
        print(f"最快首Token时间: {min_time:.2f}ms")
        print(f"最慢首Token时间: {max_time:.2f}ms")
        
        print(f"\n性能评估:")
        if avg_time < 1000:
            print(f"  🎉 优秀! 平均延迟 < 1秒")
        elif avg_time < 2000:
            print(f"  ✅ 良好! 平均延迟 < 2秒")
        elif avg_time < 3000:
            print(f"  ⚠️  一般，平均延迟 < 3秒")
        else:
            print(f"  ❌ 需要优化，平均延迟 >= 3秒")
    else:
        print(f"\n❌ 所有测试都失败了")
    
    print()


async def test_client_pool_stats(base_url: str = "http://localhost:8000"):
    """Test client pool debug endpoint."""
    print(f"\n{'='*80}")
    print("客户端池统计")
    print(f"{'='*80}\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{base_url}/api/debug/client-pool")
            if response.status_code == 200:
                data = response.json()
                print(f"池大小: {data['pool_size']}/{data['max_size']}")
                print(f"缓存的客户端数量: {len(data['cached_clients'])}")
                if data['cached_clients']:
                    print(f"\n缓存的客户端:")
                    for i, key in enumerate(data['cached_clients'], 1):
                        print(f"  {i}. {key}")
            else:
                print(f"❌ 请求失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print()


async def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试首Token延迟")
    parser.add_argument("--url", default="http://localhost:8000", help="后端服务器URL")
    parser.add_argument("--tests", type=int, default=3, help="测试次数")
    parser.add_argument("--pool-stats", action="store_true", help="显示客户端池统计")
    
    args = parser.parse_args()
    
    # Check if server is running
    print(f"检查服务器连接: {args.url}")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{args.url}/health")
            if response.status_code == 200:
                print(f"✅ 服务器在线\n")
            else:
                print(f"❌ 服务器响应异常: HTTP {response.status_code}")
                return
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            print(f"\n请确保后端服务器正在运行:")
            print(f"  cd backend && source .venv/bin/activate && python server/app.py")
            return
    
    # Run tests
    await test_first_token_latency(args.url, args.tests)
    
    # Show pool stats if requested
    if args.pool_stats:
        await test_client_pool_stats(args.url)


if __name__ == "__main__":
    asyncio.run(main())
