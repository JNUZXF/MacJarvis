"""
File: backend/tests/tools/base.py
Purpose: Base classes and utilities for tool testing
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/base.py

【架构设计原则】【单一职责原则】
- 提供统一的测试基类
- 封装通用的断言方法
- 提供测试数据管理
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.tools.mac_tools import build_default_tools
from agent.tools.registry import ToolRegistry


class ToolTestBase(ABC):
    """
    工具测试基类
    
    提供统一的测试框架和通用方法
    """
    
    def __init__(self):
        """初始化测试环境"""
        self.tools = build_default_tools()
        self.registry = ToolRegistry(self.tools)
        self.test_data_dir = Path(__file__).parent.parent / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    def get_tool_name(self) -> str:
        """返回要测试的工具名称"""
        pass
    
    def get_tool(self):
        """获取要测试的工具实例"""
        tool_name = self.get_tool_name()
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        raise ValueError(f"Tool {tool_name} not found")
    
    def execute_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具并返回结果"""
        tool = self.get_tool()
        return tool.execute(args)
    
    def assert_success(self, result: Dict[str, Any], message: str = ""):
        """断言工具执行成功"""
        assert result.get("ok") is True, f"{message}\n结果: {result}"
    
    def assert_failure(self, result: Dict[str, Any], message: str = ""):
        """断言工具执行失败"""
        assert result.get("ok") is False, f"{message}\n结果: {result}"
    
    def assert_has_data(self, result: Dict[str, Any], key: Optional[str] = None):
        """断言结果包含数据"""
        assert "data" in result, f"结果中没有data字段: {result}"
        if key:
            assert key in result["data"], f"data中没有{key}字段: {result['data']}"
    
    def assert_error_contains(self, result: Dict[str, Any], text: str):
        """断言错误信息包含指定文本"""
        assert "error" in result, f"结果中没有error字段: {result}"
        assert text in result["error"], f"错误信息不包含'{text}': {result['error']}"
    
    def create_test_file(self, filename: str, content: str = "") -> Path:
        """创建测试文件"""
        file_path = self.test_data_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def cleanup_test_file(self, file_path: Path):
        """清理测试文件"""
        if file_path.exists():
            file_path.unlink()
    
    @abstractmethod
    def run_tests(self) -> List[str]:
        """
        运行所有测试用例
        
        Returns:
            测试结果列表（失败的测试）
        """
        pass
    
    def print_test_header(self, test_name: str):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")
    
    def print_test_result(self, test_name: str, success: bool, message: str = ""):
        """打印测试结果"""
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
        if message:
            print(f"  详情: {message}")


class TestRunner:
    """
    测试运行器
    
    管理和执行所有工具测试
    """
    
    def __init__(self):
        self.test_classes: List[ToolTestBase] = []
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def register_test(self, test_class: ToolTestBase):
        """注册测试类"""
        self.test_classes.append(test_class)
    
    def run_all(self):
        """运行所有测试"""
        print("\n" + "="*80)
        print("Mac Agent 工具全面测试")
        print("="*80)
        
        for test_instance in self.test_classes:
            tool_name = test_instance.get_tool_name()
            print(f"\n{'='*80}")
            print(f"测试工具: {tool_name}")
            print(f"{'='*80}")
            
            try:
                failures = test_instance.run_tests()
                
                if not failures:
                    print(f"\n✅ {tool_name} - 所有测试通过")
                    self.results["passed"] += 1
                else:
                    print(f"\n❌ {tool_name} - {len(failures)} 个测试失败")
                    self.results["failed"] += 1
                    self.results["errors"].extend(failures)
                
                self.results["total"] += 1
                
            except Exception as e:
                print(f"\n❌ {tool_name} - 测试出错: {e}")
                import traceback
                traceback.print_exc()
                self.results["failed"] += 1
                self.results["errors"].append(f"{tool_name}: {str(e)}")
                self.results["total"] += 1
        
        self.print_summary()
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*80)
        print("测试摘要")
        print("="*80)
        print(f"总测试数: {self.results['total']}")
        print(f"通过: {self.results['passed']} ✅")
        print(f"失败: {self.results['failed']} ❌")
        
        if self.results['errors']:
            print("\n失败详情:")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        print("="*80)
        
        if self.results['failed'] == 0:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  有 {self.results['failed']} 个工具测试失败")


def load_env():
    """加载环境变量"""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"⚠️  未找到.env文件: {env_path}")
