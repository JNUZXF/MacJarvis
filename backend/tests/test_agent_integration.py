#!/usr/bin/env python3
# File: backend/tests/test_agent_integration.py
# Purpose: 测试智能体集成，验证工具调用和参数传递
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.core.agent import Agent
from agent.core.client import OpenAIClient
from agent.core.config import load_openai_config
from agent.tools.registry import ToolRegistry
from agent.tools.mac_tools import build_default_tools
from integration_test_questions import TEST_QUESTIONS, get_statistics


def test_agent_with_questions():
    """使用测试问题集测试智能体"""
    print("=" * 80)
    print("MacAgent 智能体集成测试")
    print("=" * 80)
    print()
    
    # 初始化
    config = load_openai_config()
    client = OpenAIClient(config)
    registry = ToolRegistry(build_default_tools())
    system_prompt = """你是一个专业的 macOS 智能助手。
请根据用户的问题，使用合适的工具来完成任务。
"""
    agent = Agent(client, registry, system_prompt)
    
    # 获取统计信息
    stats = get_statistics()
    print(f"测试问题集统计:")
    print(f"  总问题数: {stats['total_questions']}")
    print(f"  覆盖工具数: {stats['tools_covered']}")
    print()
    
    # 选择几个代表性问题进行测试
    test_questions = [
        q for q in TEST_QUESTIONS 
        if q["id"] in ["net_001", "net_002", "net_003", "file_001", "sys_001", "proc_002"]
    ]
    
    print(f"运行 {len(test_questions)} 个集成测试...\n")
    
    results = []
    for q in test_questions:
        print(f"[{q['id']}] {q['question']}")
        print(f"  期望工具: {', '.join(q['expected_tools'])}")
        
        try:
            # 收集工具调用
            tool_calls = []
            content = ""
            
            for event in agent.run_stream(q["question"], max_tool_turns=3):
                if event["type"] == "tool_start":
                    tool_calls.append({
                        "name": event["name"],
                        "args": event["args"]
                    })
                    print(f"  → 调用工具: {event['name']}")
                    print(f"     参数: {event['args']}")
                elif event["type"] == "content":
                    content += event["content"]
            
            # 检查是否调用了期望的工具
            called_tools = [tc["name"] for tc in tool_calls]
            expected_tools = q["expected_tools"]
            
            # 检查参数是否为空
            has_empty_args = any(not tc["args"] for tc in tool_calls if tc["args"] is not None)
            
            success = any(tool in called_tools for tool in expected_tools) and not has_empty_args
            
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected_tools": expected_tools,
                "called_tools": called_tools,
                "has_empty_args": has_empty_args,
                "success": success
            })
            
            if success:
                print(f"  ✓ 通过")
            else:
                if has_empty_args:
                    print(f"  ✗ 失败: 工具参数为空")
                else:
                    print(f"  ✗ 失败: 未调用期望的工具")
        
        except Exception as e:
            print(f"  ✗ 错误: {str(e)}")
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected_tools": q["expected_tools"],
                "called_tools": [],
                "has_empty_args": False,
                "success": False,
                "error": str(e)
            })
        
        print()
    
    # 统计结果
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print("=" * 80)
    print("集成测试结果汇总")
    print("=" * 80)
    print(f"总测试数: {total}")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    
    if failed > 0:
        print("\n失败的测试:")
        for r in results:
            if not r["success"]:
                print(f"  - [{r['id']}] {r['question']}")
                if r.get("has_empty_args"):
                    print(f"      原因: 工具参数为空")
                elif r.get("error"):
                    print(f"      错误: {r['error']}")
                else:
                    print(f"      期望: {r['expected_tools']}, 实际: {r['called_tools']}")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = test_agent_integration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
