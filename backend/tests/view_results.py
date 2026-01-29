#!/usr/bin/env python3
"""
File: backend/tests/view_results.py
Purpose: Interactive viewer for test results
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/view_results.py

【架构设计原则】【用户体验】
交互式测试结果查看器，方便查看和分析测试结果
"""

import json
import sys
from pathlib import Path
from typing import Optional


def load_latest_results(results_dir: Path) -> Optional[dict]:
    """加载最新的测试结果"""
    json_files = sorted(results_dir.glob("test_results_*.json"), reverse=True)
    if not json_files:
        return None
    
    with open(json_files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def print_summary(results: dict):
    """打印测试摘要"""
    print("\n" + "="*80)
    print("Mac Agent 工具测试结果摘要")
    print("="*80)
    print(f"测试时间: {results['timestamp']}")
    print(f"总测试数: {results['total_tests']}")
    print(f"通过: {results['passed']} ✅")
    print(f"失败: {results['failed']} ❌")
    print(f"成功率: {results['passed']/results['total_tests']*100:.1f}%")
    print("="*80)


def print_tool_list(results: dict):
    """打印工具列表"""
    print("\n工具测试列表:")
    print("-" * 80)
    
    # 按工具分组
    tools = {}
    for test in results['tests']:
        tool_name = test['tool_name']
        if tool_name not in tools:
            tools[tool_name] = []
        tools[tool_name].append(test)
    
    for i, (tool_name, tests) in enumerate(tools.items(), 1):
        passed = sum(1 for t in tests if t['success'])
        total = len(tests)
        status = "✅" if passed == total else "❌"
        print(f"{i:2d}. {status} {tool_name:30s} ({passed}/{total})")


def print_test_detail(test: dict):
    """打印单个测试的详细信息"""
    print("\n" + "="*80)
    print(f"工具: {test['tool_name']}")
    print(f"描述: {test['description']}")
    print(f"状态: {'✅ 通过' if test['success'] else '❌ 失败'}")
    print("="*80)
    
    print("\n📥 输入参数:")
    print(json.dumps(test['input'], ensure_ascii=False, indent=2))
    
    if test['output']:
        print("\n📤 输出结果:")
        output_str = json.dumps(test['output'], ensure_ascii=False, indent=2)
        # 限制输出长度
        if len(output_str) > 2000:
            print(output_str[:2000] + "\n... (输出过长，已截断)")
        else:
            print(output_str)
    
    if test['error']:
        print(f"\n❌ 错误信息: {test['error']}")
    
    print("\n" + "="*80)


def interactive_mode(results: dict):
    """交互式查看模式"""
    while True:
        print("\n" + "="*80)
        print("测试结果查看器 - 交互模式")
        print("="*80)
        print("1. 查看测试摘要")
        print("2. 查看工具列表")
        print("3. 查看失败的测试")
        print("4. 查看通过的测试")
        print("5. 按工具名称查看")
        print("6. 查看所有测试详情")
        print("0. 退出")
        print("="*80)
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == "0":
            print("\n再见！")
            break
        elif choice == "1":
            print_summary(results)
        elif choice == "2":
            print_tool_list(results)
        elif choice == "3":
            print("\n失败的测试:")
            print("-" * 80)
            failed_tests = [t for t in results['tests'] if not t['success']]
            if not failed_tests:
                print("没有失败的测试 🎉")
            else:
                for i, test in enumerate(failed_tests, 1):
                    print(f"\n{i}. {test['tool_name']} - {test['description']}")
                    print(f"   错误: {test['error']}")
        elif choice == "4":
            print("\n通过的测试:")
            print("-" * 80)
            passed_tests = [t for t in results['tests'] if t['success']]
            for i, test in enumerate(passed_tests, 1):
                print(f"{i:2d}. ✅ {test['tool_name']:30s} - {test['description']}")
        elif choice == "5":
            tool_name = input("\n请输入工具名称: ").strip()
            tests = [t for t in results['tests'] if t['tool_name'] == tool_name]
            if not tests:
                print(f"\n未找到工具: {tool_name}")
            else:
                for test in tests:
                    print_test_detail(test)
        elif choice == "6":
            for i, test in enumerate(results['tests'], 1):
                print(f"\n{'='*80}")
                print(f"测试 {i}/{len(results['tests'])}")
                print_test_detail(test)
                
                if i < len(results['tests']):
                    cont = input("\n按Enter继续，输入q退出: ").strip()
                    if cont.lower() == 'q':
                        break
        else:
            print("\n无效的选择，请重试")


def main():
    """主函数"""
    results_dir = Path(__file__).parent / "test_results"
    
    if not results_dir.exists():
        print(f"❌ 测试结果目录不存在: {results_dir}")
        return 1
    
    results = load_latest_results(results_dir)
    if not results:
        print("❌ 未找到测试结果文件")
        return 1
    
    # 如果有命令行参数，直接显示对应内容
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "summary":
            print_summary(results)
        elif cmd == "list":
            print_tool_list(results)
        elif cmd == "failed":
            failed_tests = [t for t in results['tests'] if not t['success']]
            for test in failed_tests:
                print_test_detail(test)
        elif cmd == "all":
            for test in results['tests']:
                print_test_detail(test)
        else:
            print(f"未知命令: {cmd}")
            print("可用命令: summary, list, failed, all")
            return 1
    else:
        # 交互模式
        interactive_mode(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
