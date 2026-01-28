#!/usr/bin/env python3
# File: backend/tests/run_tool_tests.py
# Purpose: 运行工具测试并生成报告
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.tools.registry import ToolRegistry
from agent.tools.mac_tools import build_default_tools
import json
from datetime import datetime


def test_tool(registry: ToolRegistry, tool_name: str, args: dict) -> dict:
    """测试单个工具"""
    try:
        result = registry.execute(tool_name, args)
        return {
            "tool": tool_name,
            "args": args,
            "success": result.get("ok", False),
            "result": result,
            "error": None
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "args": args,
            "success": False,
            "result": None,
            "error": str(e)
        }


def run_all_tests():
    """运行所有工具测试"""
    print("=" * 80)
    print("MacAgent 工具快速测试")
    print("=" * 80)
    print()
    
    registry = ToolRegistry(build_default_tools())
    test_dir = Path.home() / "Desktop" / "test_agent_quick"
    test_dir.mkdir(exist_ok=True)
    
    results = []
    
    # 定义测试用例
    test_cases = [
        # 系统信息
        ("system_info", {}),
        ("disk_usage", {}),
        ("battery_status", {}),
        
        # 进程管理
        ("process_list", {}),
        ("top_processes", {"limit": 5}),
        
        # 网络工具
        ("network_info", {}),
        ("dns_info", {}),
        ("wifi_info", {}),
        ("open_ports", {}),
        ("ping_host", {"host": "127.0.0.1", "count": 2}),
        
        # 文件操作
        ("list_directory", {"path": str(test_dir)}),
        ("write_file", {"path": str(test_dir / "test.txt"), "content": "Hello", "overwrite": True}),
        ("read_file", {"path": str(test_dir / "test.txt")}),
        ("file_info", {"path": str(test_dir / "test.txt")}),
        ("make_directory", {"path": str(test_dir / "subdir"), "parents": True}),
        
        # 应用管理
        ("list_applications", {}),
        
        # 系统管理
        ("get_environment_variables", {"variable_name": "PATH"}),
        ("spotlight_search", {"query": "Applications", "limit": 3}),
        
        # 数据处理
        ("json_formatter", {"json_string": '{"test":123}', "mode": "pretty"}),
        ("text_statistics", {"file_path": str(test_dir / "test.txt")}),
        
        # 生产力工具
        ("calculate_hash", {"file_path": str(test_dir / "test.txt"), "algorithm": "md5"}),
        ("clipboard_operations", {"operation": "write", "content": "test"}),
        ("clipboard_operations", {"operation": "read"}),
        
        # 时间工具
        ("timezone_converter", {"timestamp": "now"}),
    ]
    
    print(f"运行 {len(test_cases)} 个测试用例...\n")
    
    for tool_name, args in test_cases:
        print(f"测试 {tool_name}...", end=" ")
        result = test_tool(registry, tool_name, args)
        results.append(result)
        
        if result["success"]:
            print("✓ 通过")
        else:
            print(f"✗ 失败: {result.get('error') or result['result'].get('error', 'Unknown error')}")
    
    # 统计结果
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print(f"总测试数: {total}")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    
    # 显示失败的测试
    if failed > 0:
        print("\n失败的测试:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['tool']}: {r.get('error') or r['result'].get('error', 'Unknown')}")
    
    # 保存详细报告
    report_path = test_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{passed/total*100:.1f}%"
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: {report_path}")
    
    # 清理测试目录
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
