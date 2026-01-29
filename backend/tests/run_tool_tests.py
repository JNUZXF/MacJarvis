#!/usr/bin/env python3
"""
File: backend/tests/run_tool_tests.py
Purpose: Enhanced test runner with detailed result logging
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/run_tool_tests.py

【架构设计原则】【测试策略】【日志系统】
增强版测试运行器，记录所有工具的入参、出参和测试结果
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.tools.base import load_env
from tests.test_cases_config import get_all_test_cases, get_tools_count, get_test_cases_count
from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry


class DetailedTestRunner:
    """
    增强版测试运行器
    
    功能:
    1. 测试所有工具
    2. 记录详细的入参、出参
    3. 生成JSON和Markdown格式的测试报告
    """
    
    def __init__(self):
        self.tools = build_default_tools()
        self.registry = ToolRegistry(self.tools)
        self.results = []
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        
        # 创建测试结果目录
        self.results_dir = Path(__file__).parent / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 生成时间戳
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_tool_by_name(self, tool_name: str):
        """根据名称获取工具"""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None
    
    def execute_tool_with_logging(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        执行工具并记录详细信息
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            description: 测试描述
        
        Returns:
            包含执行结果和元数据的字典
        """
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            return {
                "tool_name": tool_name,
                "description": description,
                "success": False,
                "error": f"Tool {tool_name} not found",
                "input": args,
                "output": None,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # 执行工具
            result = tool.execute(args)
            
            # 构建测试记录
            test_record = {
                "tool_name": tool_name,
                "description": description,
                "success": result.get("ok", False),
                "input": args,
                "output": result,
                "error": result.get("error") if not result.get("ok") else None,
                "timestamp": datetime.now().isoformat()
            }
            
            self.results.append(test_record)
            return test_record
            
        except Exception as e:
            test_record = {
                "tool_name": tool_name,
                "description": description,
                "success": False,
                "input": args,
                "output": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.results.append(test_record)
            return test_record
    
    def save_results_json(self):
        """保存JSON格式的测试结果"""
        json_file = self.results_dir / f"test_results_{self.timestamp}.json"
        
        summary = {
            "timestamp": self.timestamp,
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r["success"]),
            "failed": sum(1 for r in self.results if not r["success"]),
            "tests": self.results
        }
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ JSON结果已保存: {json_file}")
        return json_file
    
    def save_results_markdown(self):
        """保存Markdown格式的测试报告"""
        md_file = self.results_dir / f"test_report_{self.timestamp}.md"
        
        passed = sum(1 for r in self.results if r["success"])
        failed = sum(1 for r in self.results if not r["success"])
        
        with open(md_file, "w", encoding="utf-8") as f:
            # 标题
            f.write(f"# Mac Agent 工具测试报告\n\n")
            f.write(f"> **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"> **测试工具数**: {len(self.results)}\n")
            f.write(f"> **通过**: {passed} ✅\n")
            f.write(f"> **失败**: {failed} ❌\n\n")
            f.write("---\n\n")
            
            # 测试摘要
            f.write("## 📊 测试摘要\n\n")
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 总测试数 | {len(self.results)} |\n")
            f.write(f"| 通过 | {passed} |\n")
            f.write(f"| 失败 | {failed} |\n")
            f.write(f"| 成功率 | {passed/len(self.results)*100:.1f}% |\n\n")
            f.write("---\n\n")
            
            # 详细测试结果
            f.write("## 📝 详细测试结果\n\n")
            
            for i, record in enumerate(self.results, 1):
                status = "✅ 通过" if record["success"] else "❌ 失败"
                f.write(f"### {i}. {record['tool_name']} - {status}\n\n")
                
                if record["description"]:
                    f.write(f"**描述**: {record['description']}\n\n")
                
                # 输入参数
                f.write("**输入参数**:\n```json\n")
                f.write(json.dumps(record["input"], ensure_ascii=False, indent=2))
                f.write("\n```\n\n")
                
                # 输出结果
                if record["output"]:
                    f.write("**输出结果**:\n```json\n")
                    f.write(json.dumps(record["output"], ensure_ascii=False, indent=2))
                    f.write("\n```\n\n")
                
                # 错误信息
                if record["error"]:
                    f.write(f"**错误信息**: {record['error']}\n\n")
                
                f.write("---\n\n")
        
        print(f"✅ Markdown报告已保存: {md_file}")
        return md_file
    
    def print_summary(self):
        """打印测试摘要"""
        passed = sum(1 for r in self.results if r["success"])
        failed = sum(1 for r in self.results if not r["success"])
        
        print("\n" + "="*80)
        print("测试摘要")
        print("="*80)
        print(f"总测试数: {len(self.results)}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"成功率: {passed/len(self.results)*100:.1f}%")
        print("="*80)
        
        if failed > 0:
            print("\n失败的测试:")
            for record in self.results:
                if not record["success"]:
                    print(f"  ❌ {record['tool_name']}: {record['error']}")


def prepare_test_files(test_data_dir: Path):
    """准备测试所需的文件"""
    print("\n📁 准备测试文件...")
    
    # 创建测试文本文件
    (test_data_dir / "test_trash.txt").write_text("This file will be moved to trash")
    (test_data_dir / "file1.txt").write_text("Line 1\nLine 2\nLine 3")
    (test_data_dir / "file2.txt").write_text("Line 1\nLine 2 modified\nLine 3")
    
    # 创建测试CSV文件
    csv_content = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai\nCharlie,35,Guangzhou"
    (test_data_dir / "test_data.csv").write_text(csv_content)
    
    # 创建测试Python脚本
    script_content = """#!/usr/bin/env python3
print("Hello from test script!")
print("This is a test.")
"""
    script_path = test_data_dir / "test_script.py"
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    
    # 创建images目录
    (test_data_dir / "images").mkdir(exist_ok=True)
    
    print("✅ 测试文件准备完成")


def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("Mac Agent 工具全面测试（增强版）")
    print("="*80)
    
    # 加载环境变量
    load_env()
    
    # 创建测试运行器
    runner = DetailedTestRunner()
    
    # 准备测试文件
    prepare_test_files(runner.test_data_dir)
    
    # 获取所有测试用例
    all_test_cases = get_all_test_cases()
    
    print(f"\n📋 测试统计:")
    print(f"  - 工具总数: {get_tools_count()}")
    print(f"  - 测试用例总数: {get_test_cases_count()}")
    print(f"  - 已注册工具: {len(runner.tools)}")
    print("="*80)
    
    # 运行所有测试
    print("\n🚀 开始执行测试...\n")
    
    test_count = 0
    for tool_name, test_cases in all_test_cases.items():
        print(f"\n{'='*60}")
        print(f"测试工具: {tool_name} ({len(test_cases)} 个测试用例)")
        print(f"{'='*60}")
        
        for i, test_case in enumerate(test_cases, 1):
            test_count += 1
            expect_failure = test_case.get("expect_failure", False)
            print(f"\n[{test_count}] {test_case['description']}")
            
            result = runner.execute_tool_with_logging(
                tool_name,
                test_case["args"],
                test_case["description"]
            )
            
            # 如果预期失败，则失败也算通过
            if expect_failure:
                if not result["success"]:
                    print(f"  ✅ 通过（预期失败）: {result.get('error', 'Unknown error')}")
                else:
                    print(f"  ⚠️  警告: 预期失败但实际成功")
            else:
                if result["success"]:
                    print(f"  ✅ 通过")
                else:
                    print(f"  ❌ 失败: {result.get('error', 'Unknown error')}")
    
    # 打印摘要
    runner.print_summary()
    
    # 保存结果
    json_file = runner.save_results_json()
    md_file = runner.save_results_markdown()
    
    print("\n" + "="*80)
    print("📄 测试报告已生成:")
    print(f"  - JSON: {json_file}")
    print(f"  - Markdown: {md_file}")
    print("="*80)
    
    print("\n🎉 测试完成！")
    
    return 0 if sum(1 for r in runner.results if not r["success"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
