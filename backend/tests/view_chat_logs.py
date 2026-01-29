#!/usr/bin/env python3
"""
File: backend/tests/view_chat_logs.py
Purpose: Viewer for chat conversation logs
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/view_chat_logs.py

【架构设计原则】【用户体验】
对话记录查看器，方便查看和分析对话记录
"""

import json
import sys
from pathlib import Path
from typing import Optional


def load_latest_chat_logs(chat_logs_dir: Path) -> Optional[dict]:
    """加载最新的对话记录"""
    json_files = sorted(chat_logs_dir.glob("chat_logs_*.json"), reverse=True)
    if not json_files:
        return None
    
    with open(json_files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def print_summary(logs: dict):
    """打印对话摘要"""
    print("\n" + "="*80)
    print("Mac Agent 对话记录摘要")
    print("="*80)
    print(f"测试时间: {logs['timestamp']}")
    print(f"总对话数: {logs['total_conversations']}")
    print(f"成功: {logs['successful']} ✅")
    print(f"失败: {logs['failed']} ❌")
    print(f"成功率: {logs['successful']/logs['total_conversations']*100:.1f}%")
    print("="*80)


def print_conversation_list(logs: dict):
    """打印对话列表"""
    print("\n对话列表:")
    print("-" * 80)
    
    for i, conv in enumerate(logs['conversations'], 1):
        status = "✅" if conv['success'] else "❌"
        tools_count = len(conv.get('tool_calls', []))
        user_input_preview = conv['user_input'][:60] + "..." if len(conv['user_input']) > 60 else conv['user_input']
        
        print(f"{i:2d}. {status} {user_input_preview}")
        print(f"    工具调用: {tools_count} 个")
        if conv.get('agent_response'):
            response_preview = conv['agent_response'][:50] + "..." if len(conv['agent_response']) > 50 else conv['agent_response']
            print(f"    Agent响应: {response_preview}")


def print_conversation_detail(conv: dict, index: int):
    """打印单个对话的详细信息"""
    print("\n" + "="*80)
    print(f"对话 {index}")
    print("="*80)
    
    status = "✅ 成功" if conv['success'] else "❌ 失败"
    print(f"状态: {status}")
    
    if conv.get('description'):
        print(f"描述: {conv['description']}")
    
    print(f"\n👤 用户输入:")
    print(f"   {conv['user_input']}")
    
    if conv.get('agent_response'):
        print(f"\n🤖 Agent响应:")
        print(f"   {conv['agent_response']}")
    
    if conv.get('tool_calls'):
        print(f"\n🔧 工具调用 ({len(conv['tool_calls'])} 个):")
        for i, tool_call in enumerate(conv['tool_calls'], 1):
            print(f"\n   {i}. {tool_call['name']}")
            print(f"      参数: {json.dumps(tool_call.get('args', {}), ensure_ascii=False)}")
            if 'result' in tool_call:
                result_str = json.dumps(tool_call['result'], ensure_ascii=False)
                if len(result_str) > 200:
                    print(f"      结果: {result_str[:200]}...")
                else:
                    print(f"      结果: {result_str}")
    
    if conv.get('error'):
        print(f"\n❌ 错误: {conv['error']}")
    
    print(f"\n⏰ 时间: {conv['timestamp']}")
    print("="*80)


def interactive_mode(logs: dict):
    """交互式查看模式"""
    while True:
        print("\n" + "="*80)
        print("对话记录查看器 - 交互模式")
        print("="*80)
        print("1. 查看对话摘要")
        print("2. 查看对话列表")
        print("3. 查看失败的对话")
        print("4. 查看成功的对话")
        print("5. 按编号查看对话详情")
        print("6. 查看所有对话详情")
        print("0. 退出")
        print("="*80)
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == "0":
            print("\n再见！")
            break
        elif choice == "1":
            print_summary(logs)
        elif choice == "2":
            print_conversation_list(logs)
        elif choice == "3":
            print("\n失败的对话:")
            print("-" * 80)
            failed = [c for c in logs['conversations'] if not c['success']]
            if not failed:
                print("没有失败的对话 🎉")
            else:
                for i, conv in enumerate(failed, 1):
                    print(f"\n{i}. {conv['user_input']}")
                    print(f"   错误: {conv['error']}")
        elif choice == "4":
            print("\n成功的对话:")
            print("-" * 80)
            successful = [c for c in logs['conversations'] if c['success']]
            for i, conv in enumerate(successful, 1):
                tools_count = len(conv.get('tool_calls', []))
                print(f"{i:2d}. ✅ {conv['user_input'][:60]}")
                print(f"    工具调用: {tools_count} 个")
        elif choice == "5":
            try:
                index = int(input("\n请输入对话编号: ").strip())
                if 1 <= index <= len(logs['conversations']):
                    print_conversation_detail(logs['conversations'][index - 1], index)
                else:
                    print(f"\n无效的编号，请输入 1-{len(logs['conversations'])}")
            except ValueError:
                print("\n无效的输入")
        elif choice == "6":
            for i, conv in enumerate(logs['conversations'], 1):
                print_conversation_detail(conv, i)
                if i < len(logs['conversations']):
                    cont = input("\n按Enter继续，输入q退出: ").strip()
                    if cont.lower() == 'q':
                        break
        else:
            print("\n无效的选择，请重试")


def main():
    """主函数"""
    chat_logs_dir = Path(__file__).parent / "chat_logs"
    
    if not chat_logs_dir.exists():
        print(f"❌ 对话记录目录不存在: {chat_logs_dir}")
        print("💡 提示: 请先运行 'python tests/run_chat_tests.py' 生成对话记录")
        return 1
    
    logs = load_latest_chat_logs(chat_logs_dir)
    if not logs:
        print("❌ 未找到对话记录文件")
        print("💡 提示: 请先运行 'python tests/run_chat_tests.py' 生成对话记录")
        return 1
    
    # 如果有命令行参数，直接显示对应内容
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "summary":
            print_summary(logs)
        elif cmd == "list":
            print_conversation_list(logs)
        elif cmd == "failed":
            failed = [c for c in logs['conversations'] if not c['success']]
            for conv in failed:
                idx = logs['conversations'].index(conv) + 1
                print_conversation_detail(conv, idx)
        elif cmd == "all":
            for i, conv in enumerate(logs['conversations'], 1):
                print_conversation_detail(conv, i)
        else:
            print(f"未知命令: {cmd}")
            print("可用命令: summary, list, failed, all")
            return 1
    else:
        # 交互模式
        interactive_mode(logs)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
