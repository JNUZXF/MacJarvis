"""
File: backend/tests/tools/system/test_system_info.py
Purpose: Test system information tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/system/test_system_info.py
"""

import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.tools.base import ToolTestBase


class TestSystemInfo(ToolTestBase):
    """测试系统信息工具"""
    
    def get_tool_name(self) -> str:
        return "system_info"
    
    def run_tests(self):
        failures = []
        
        # 测试1: 获取系统信息
        try:
            print("\n测试1: 获取系统信息")
            result = self.execute_tool({})
            self.assert_success(result, "获取系统信息失败")
            self.assert_has_data(result, "sw_vers")
            self.assert_has_data(result, "uname")
            self.assert_has_data(result, "cpu")
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"system_info - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestDiskUsage(ToolTestBase):
    """测试磁盘使用情况工具"""
    
    def get_tool_name(self) -> str:
        return "disk_usage"
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试: 查看磁盘使用情况")
            result = self.execute_tool({})
            self.assert_success(result, "获取磁盘使用情况失败")
            assert len(result.get("stdout", "")) > 0, "磁盘信息为空"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"disk_usage: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestBatteryStatus(ToolTestBase):
    """测试电池状态工具"""
    
    def get_tool_name(self) -> str:
        return "battery_status"
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试: 查看电池状态")
            result = self.execute_tool({})
            self.assert_success(result, "获取电池状态失败")
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"battery_status: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestTopProcesses(ToolTestBase):
    """测试进程列表工具"""
    
    def get_tool_name(self) -> str:
        return "top_processes"
    
    def run_tests(self):
        failures = []
        
        # 测试1: 默认获取前10个进程
        try:
            print("\n测试1: 获取前10个进程")
            result = self.execute_tool({"limit": 10})
            self.assert_success(result, "获取进程列表失败")
            self.assert_has_data(result)
            assert len(result["data"]) <= 10, "进程数量超过限制"
            print(f"✅ 通过 - 获取到 {len(result['data'])} 个进程")
        except AssertionError as e:
            failures.append(f"top_processes - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试2: 获取前5个进程
        try:
            print("\n测试2: 获取前5个进程")
            result = self.execute_tool({"limit": 5})
            self.assert_success(result)
            assert len(result["data"]) <= 5, "进程数量超过限制"
            print(f"✅ 通过 - 获取到 {len(result['data'])} 个进程")
        except AssertionError as e:
            failures.append(f"top_processes - 测试2: {e}")
            print(f"❌ 失败: {e}")
        
        return failures
