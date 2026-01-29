"""
File: backend/tests/tools/text/test_shell_command.py
Purpose: Test shell command execution tool (核心功能)
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/text/test_shell_command.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.tools.base import ToolTestBase


class TestExecuteShellCommand(ToolTestBase):
    """测试Shell命令执行工具 - 核心功能"""
    
    def get_tool_name(self) -> str:
        return "execute_shell_command"
    
    def run_tests(self):
        failures = []
        
        # 测试1: 简单命令
        try:
            print("\n测试1: 执行简单echo命令")
            result = self.execute_tool({"command": "echo 'Hello, Mac Agent!'"})
            self.assert_success(result)
            assert "Hello, Mac Agent!" in result["stdout"], "输出内容不匹配"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试2: 管道命令
        try:
            print("\n测试2: 执行管道命令")
            result = self.execute_tool({
                "command": "echo 'line1\nline2\nline3' | grep 'line2'"
            })
            self.assert_success(result)
            assert "line2" in result["stdout"], "管道命令执行失败"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试2: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试3: 环境变量
        try:
            print("\n测试3: 访问环境变量")
            result = self.execute_tool({"command": "echo $HOME"})
            self.assert_success(result)
            assert len(result["stdout"]) > 0, "环境变量为空"
            print(f"✅ 通过 - HOME={result['stdout']}")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试3: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试4: 工作目录
        try:
            print("\n测试4: 指定工作目录")
            import os
            cwd = os.getcwd()
            result = self.execute_tool({
                "command": "pwd",
                "working_directory": cwd
            })
            self.assert_success(result)
            assert cwd in result["stdout"], "工作目录不匹配"
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试4: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试5: 危险命令拦截
        try:
            print("\n测试5: 危险命令拦截")
            dangerous_commands = [
                "rm -rf /",
                "mkfs.ext4 /dev/sda1",
            ]
            for cmd in dangerous_commands:
                result = self.execute_tool({"command": cmd})
                self.assert_failure(result)
                self.assert_error_contains(result, "危险命令")
            print("✅ 通过 - 所有危险命令被拦截")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试5: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试6: 超时控制
        try:
            print("\n测试6: 超时控制")
            result = self.execute_tool({
                "command": "sleep 5",
                "timeout": 2
            })
            self.assert_failure(result)
            self.assert_error_contains(result, "超时")
            print("✅ 通过 - 超时控制正常")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试6: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试7: 命令失败处理
        try:
            print("\n测试7: 命令失败处理")
            result = self.execute_tool({"command": "ls /nonexistent/path"})
            self.assert_failure(result)
            assert result["exit_code"] != 0, "退出码应该非0"
            print("✅ 通过 - 正确处理命令失败")
        except AssertionError as e:
            failures.append(f"execute_shell_command - 测试7: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestGrepSearch(ToolTestBase):
    """测试Grep搜索工具"""
    
    def get_tool_name(self) -> str:
        return "grep_search"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_content = """line 1: hello world
line 2: HELLO WORLD
line 3: goodbye world
line 4: test content
line 5: hello again"""
        test_file = self.create_test_file("test_grep.txt", test_content)
        
        try:
            # 测试1: 基本搜索
            print("\n测试1: 基本grep搜索")
            result = self.execute_tool({
                "pattern": "hello",
                "file_path": str(test_file)
            })
            self.assert_success(result)
            self.assert_has_data(result, "matches")
            assert result["data"]["match_count"] >= 1, "未找到匹配"
            print(f"✅ 通过 - 找到 {result['data']['match_count']} 个匹配")
            
            # 测试2: 忽略大小写
            print("\n测试2: 忽略大小写搜索")
            result = self.execute_tool({
                "pattern": "hello",
                "file_path": str(test_file),
                "case_insensitive": True
            })
            self.assert_success(result)
            assert result["data"]["match_count"] >= 2, "大小写不敏感搜索失败"
            print(f"✅ 通过 - 找到 {result['data']['match_count']} 个匹配")
            
        except AssertionError as e:
            failures.append(f"grep_search: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
        
        return failures


class TestTailLog(ToolTestBase):
    """测试日志查看工具"""
    
    def get_tool_name(self) -> str:
        return "tail_log"
    
    def run_tests(self):
        failures = []
        
        # 创建测试日志文件
        log_lines = [f"Log line {i}\n" for i in range(1, 101)]
        test_log = self.create_test_file("test.log", "".join(log_lines))
        
        try:
            # 测试1: 读取最后10行
            print("\n测试1: 读取最后10行")
            result = self.execute_tool({
                "file_path": str(test_log),
                "lines": 10
            })
            self.assert_success(result)
            self.assert_has_data(result, "content")
            assert result["data"]["line_count"] <= 10, "行数超过限制"
            print(f"✅ 通过 - 读取了 {result['data']['line_count']} 行")
            
            # 测试2: 过滤日志
            print("\n测试2: 过滤特定内容")
            result = self.execute_tool({
                "file_path": str(test_log),
                "lines": 100,
                "filter_pattern": "line 9"
            })
            self.assert_success(result)
            # 应该匹配 line 9, line 90-99
            assert result["data"]["line_count"] >= 10, "过滤结果不正确"
            print(f"✅ 通过 - 过滤后 {result['data']['line_count']} 行")
            
        except AssertionError as e:
            failures.append(f"tail_log: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_log)
        
        return failures
