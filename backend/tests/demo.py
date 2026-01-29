#!/usr/bin/env python3
"""
File: backend/tests/demo.py
Purpose: Demonstration script for the test system
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/demo.py

【架构设计原则】【用户体验】
演示测试系统的核心功能
"""

import json
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.view_results import load_latest_results


def print_banner(text: str):
    """打印横幅"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)


def demo_summary():
    """演示1: 查看测试摘要"""
    print_banner("演示 1: 测试摘要")
    
    results_dir = Path(__file__).parent / "test_results"
    results = load_latest_results(results_dir)
    
    if not results:
        print("❌ 未找到测试结果")
        return
    
    print(f"\n📊 测试统计:")
    print(f"  • 测试时间: {results['timestamp']}")
    print(f"  • 总测试数: {results['total_tests']}")
    print(f"  • 通过: {results['passed']} ✅")
    print(f"  • 失败: {results['failed']} ❌")
    print(f"  • 成功率: {results['passed']/results['total_tests']*100:.1f}%")


def demo_tool_categories():
    """演示2: 按分类统计"""
    print_banner("演示 2: 工具分类统计")
    
    results_dir = Path(__file__).parent / "test_results"
    results = load_latest_results(results_dir)
    
    if not results:
        return
    
    # 按工具分组
    tools = {}
    for test in results['tests']:
        tool_name = test['tool_name']
        if tool_name not in tools:
            tools[tool_name] = []
        tools[tool_name].append(test)
    
    # 统计分类
    categories = {
        "系统信息": ["system_info", "disk_usage", "battery_status", "system_sleep_settings"],
        "进程管理": ["process_list", "top_processes", "port_killer"],
        "网络工具": ["network_info", "dns_info", "wifi_info", "open_ports", "ping_host", "download_file", "check_website_status"],
        "文件管理": ["list_directory", "search_files", "read_file", "write_file", "append_file", "make_directory", "file_info", "find_in_file", "move_to_trash", "find_advanced"],
    }
    
    print("\n📁 分类统计:")
    for category, tool_names in categories.items():
        category_tools = {k: v for k, v in tools.items() if k in tool_names}
        if category_tools:
            total = sum(len(tests) for tests in category_tools.values())
            passed = sum(sum(1 for t in tests if t['success']) for tests in category_tools.values())
            print(f"  • {category:12s}: {passed}/{total} 通过 ({passed/total*100:.0f}%)")


def demo_sample_test():
    """演示3: 查看示例测试"""
    print_banner("演示 3: 测试结果示例")
    
    results_dir = Path(__file__).parent / "test_results"
    results = load_latest_results(results_dir)
    
    if not results:
        return
    
    # 找一个成功的测试
    success_test = next((t for t in results['tests'] if t['success'] and t['tool_name'] == 'system_info'), None)
    
    if success_test:
        print("\n✅ 成功的测试示例:")
        print(f"  工具: {success_test['tool_name']}")
        print(f"  描述: {success_test['description']}")
        print(f"\n  输入参数:")
        print(f"    {json.dumps(success_test['input'], ensure_ascii=False)}")
        print(f"\n  输出结果:")
        output_str = json.dumps(success_test['output'], ensure_ascii=False, indent=4)
        # 限制输出长度
        if len(output_str) > 300:
            print(f"    {output_str[:300]}...")
        else:
            print(f"    {output_str}")
    
    # 找一个失败的测试
    failed_test = next((t for t in results['tests'] if not t['success']), None)
    
    if failed_test:
        print("\n\n❌ 失败的测试示例:")
        print(f"  工具: {failed_test['tool_name']}")
        print(f"  描述: {failed_test['description']}")
        print(f"  错误: {failed_test['error']}")


def demo_file_locations():
    """演示4: 文件位置"""
    print_banner("演示 4: 测试文件位置")
    
    results_dir = Path(__file__).parent / "test_results"
    
    print("\n📁 测试结果文件:")
    
    # JSON文件
    json_files = sorted(results_dir.glob("test_results_*.json"), reverse=True)
    if json_files:
        latest_json = json_files[0]
        size_mb = latest_json.stat().st_size / 1024 / 1024
        print(f"  • JSON: {latest_json.name}")
        print(f"    大小: {size_mb:.1f} MB")
        print(f"    路径: {latest_json}")
    
    # Markdown文件
    md_files = sorted(results_dir.glob("test_report_*.md"), reverse=True)
    if md_files:
        latest_md = md_files[0]
        size_mb = latest_md.stat().st_size / 1024 / 1024
        print(f"\n  • Markdown: {latest_md.name}")
        print(f"    大小: {size_mb:.1f} MB")
        print(f"    路径: {latest_md}")
    
    print(f"\n📚 文档文件:")
    docs_dir = Path(__file__).parent.parent / "docs"
    doc_files = [
        "工具测试完整报告_20260129.md",
        "mac_agent_工具说明_20260129.md",
    ]
    for doc_file in doc_files:
        doc_path = docs_dir / doc_file
        if doc_path.exists():
            size_kb = doc_path.stat().st_size / 1024
            print(f"  • {doc_file}")
            print(f"    大小: {size_kb:.1f} KB")


def demo_usage_commands():
    """演示5: 常用命令"""
    print_banner("演示 5: 常用命令")
    
    print("\n🚀 运行测试:")
    print("  python tests/run_tool_tests.py")
    
    print("\n📊 查看结果:")
    print("  # 交互式查看")
    print("  python tests/view_results.py")
    print()
    print("  # 快速查看摘要")
    print("  python tests/view_results.py summary")
    print()
    print("  # 查看工具列表")
    print("  python tests/view_results.py list")
    print()
    print("  # 查看失败的测试")
    print("  python tests/view_results.py failed")
    
    print("\n📄 查看文档:")
    print("  open backend/docs/工具测试完整报告_20260129.md")
    print("  open backend/tests/测试使用指南.md")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("  Mac Agent 测试系统演示")
    print("="*80)
    
    # 运行所有演示
    demo_summary()
    demo_tool_categories()
    demo_sample_test()
    demo_file_locations()
    demo_usage_commands()
    
    print("\n" + "="*80)
    print("  演示完成！")
    print("="*80)
    print("\n💡 提示: 运行 'python tests/view_results.py' 进入交互模式")
    print()


if __name__ == "__main__":
    main()
