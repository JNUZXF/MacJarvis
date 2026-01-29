"""
File: backend/tests/tools/network/test_network_tools.py
Purpose: Test network-related tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/network/test_network_tools.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.tools.base import ToolTestBase


class TestNetworkInfo(ToolTestBase):
    """测试网络信息工具"""
    
    def get_tool_name(self) -> str:
        return "network_info"
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试: 获取网络接口信息")
            result = self.execute_tool({})
            self.assert_success(result)
            assert len(result.get("stdout", "")) > 0, "网络信息为空"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"network_info: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestPingHost(ToolTestBase):
    """测试Ping工具"""
    
    def get_tool_name(self) -> str:
        return "ping_host"
    
    def run_tests(self):
        failures = []
        
        # 测试1: Ping本地主机
        try:
            print("\n测试1: Ping localhost")
            result = self.execute_tool({
                "host": "localhost",
                "count": 3
            })
            self.assert_success(result)
            self.assert_has_data(result, "output")
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"ping_host - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试2: Ping公网地址
        try:
            print("\n测试2: Ping 8.8.8.8")
            result = self.execute_tool({
                "host": "8.8.8.8",
                "count": 2
            })
            # Ping可能失败（网络问题），所以只检查是否有输出
            assert "data" in result or "error" in result, "结果格式错误"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"ping_host - 测试2: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestCheckWebsiteStatus(ToolTestBase):
    """测试网站状态检查工具"""
    
    def get_tool_name(self) -> str:
        return "check_website_status"
    
    def run_tests(self):
        failures = []
        
        try:
            print("\n测试: 检查网站状态")
            # 使用一个稳定的网站
            result = self.execute_tool({"url": "https://www.google.com"})
            # 网站可能无法访问，所以只检查是否有响应
            assert "ok" in result, "结果格式错误"
            if result.get("ok"):
                print(f"✅ 通过 - 状态码: {result.get('data', {}).get('status_code')}")
            else:
                print("✅ 通过 - 网站无法访问（预期行为）")
        except AssertionError as e:
            failures.append(f"check_website_status: {e}")
            print(f"❌ 失败: {e}")
        
        return failures
