"""
File: backend/tests/tools/file/test_file_operations.py
Purpose: Test file operation tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/file/test_file_operations.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.tools.base import ToolTestBase


class TestListDirectory(ToolTestBase):
    """测试列出目录工具"""
    
    def get_tool_name(self) -> str:
        return "list_directory"
    
    def run_tests(self):
        failures = []
        
        # 测试1: 列出当前目录
        try:
            print("\n测试1: 列出当前目录")
            result = self.execute_tool({"path": str(Path.cwd())})
            self.assert_success(result)
            self.assert_has_data(result)
            assert isinstance(result["data"], list), "返回的不是列表"
            print(f"✅ 通过 - 找到 {len(result['data'])} 个文件/目录")
        except AssertionError as e:
            failures.append(f"list_directory - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试2: 列出不存在的目录（跳过，因为路径验证会抛出异常）
        try:
            print("\n测试2: 列出不存在的目录")
            # 使用允许的路径但不存在的子目录
            test_path = self.test_data_dir / "nonexistent_subdir"
            result = self.execute_tool({"path": str(test_path)})
            self.assert_failure(result)
            print("✅ 通过 - 正确处理不存在的目录")
        except (AssertionError, ValueError) as e:
            # ValueError是路径验证异常，这也是预期行为
            if "Path is not allowed" in str(e):
                print("✅ 通过 - 路径验证正常工作")
            else:
                failures.append(f"list_directory - 测试2: {e}")
                print(f"❌ 失败: {e}")
        
        return failures


class TestReadFile(ToolTestBase):
    """测试读取文件工具"""
    
    def get_tool_name(self) -> str:
        return "read_file"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_content = "Hello, Mac Agent!\nThis is a test file.\n"
        test_file = self.create_test_file("test_read.txt", test_content)
        
        try:
            # 测试1: 读取文件
            print("\n测试1: 读取测试文件")
            result = self.execute_tool({"path": str(test_file)})
            self.assert_success(result)
            self.assert_has_data(result)
            assert test_content in result["data"], "文件内容不匹配"
            print("✅ 通过")
            
            # 测试2: 读取不存在的文件
            print("\n测试2: 读取不存在的文件")
            # 使用允许的路径但不存在的文件
            nonexistent_file = self.test_data_dir / "nonexistent_file.txt"
            result = self.execute_tool({"path": str(nonexistent_file)})
            self.assert_failure(result)
            print("✅ 通过 - 正确处理不存在的文件")
            
        except AssertionError as e:
            failures.append(f"read_file: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
        
        return failures


class TestWriteFile(ToolTestBase):
    """测试写入文件工具"""
    
    def get_tool_name(self) -> str:
        return "write_file"
    
    def run_tests(self):
        failures = []
        test_file = self.test_data_dir / "test_write.txt"
        
        try:
            # 测试1: 写入新文件
            print("\n测试1: 写入新文件")
            content = "Test content for write_file"
            result = self.execute_tool({
                "path": str(test_file),
                "content": content,
                "overwrite": False
            })
            self.assert_success(result)
            assert test_file.exists(), "文件未创建"
            assert test_file.read_text() == content, "文件内容不匹配"
            print("✅ 通过")
            
            # 测试2: 覆盖现有文件
            print("\n测试2: 覆盖现有文件")
            new_content = "New content"
            result = self.execute_tool({
                "path": str(test_file),
                "content": new_content,
                "overwrite": True
            })
            self.assert_success(result)
            assert test_file.read_text() == new_content, "文件内容未更新"
            print("✅ 通过")
            
        except AssertionError as e:
            failures.append(f"write_file: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
        
        return failures


class TestFileInfo(ToolTestBase):
    """测试文件信息工具"""
    
    def get_tool_name(self) -> str:
        return "file_info"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_file = self.create_test_file("test_info.txt", "test content")
        
        try:
            print("\n测试: 获取文件信息")
            result = self.execute_tool({"path": str(test_file)})
            self.assert_success(result)
            self.assert_has_data(result, "is_file")
            self.assert_has_data(result, "size_bytes")
            assert result["data"]["is_file"] is True, "文件类型判断错误"
            print("✅ 通过")
            
        except AssertionError as e:
            failures.append(f"file_info: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
        
        return failures


class TestSearchFiles(ToolTestBase):
    """测试文件搜索工具"""
    
    def get_tool_name(self) -> str:
        return "search_files"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        self.create_test_file("test1.txt", "content1")
        self.create_test_file("test2.txt", "content2")
        self.create_test_file("test.log", "log content")
        
        try:
            # 测试1: 搜索.txt文件
            print("\n测试1: 搜索.txt文件")
            result = self.execute_tool({
                "path": str(self.test_data_dir),
                "pattern": "*.txt"
            })
            self.assert_success(result)
            self.assert_has_data(result)
            assert len(result["data"]) >= 2, "未找到足够的.txt文件"
            print(f"✅ 通过 - 找到 {len(result['data'])} 个文件")
            
            # 测试2: 搜索.log文件
            print("\n测试2: 搜索.log文件")
            result = self.execute_tool({
                "path": str(self.test_data_dir),
                "pattern": "*.log"
            })
            self.assert_success(result)
            assert len(result["data"]) >= 1, "未找到.log文件"
            print(f"✅ 通过 - 找到 {len(result['data'])} 个文件")
            
        except AssertionError as e:
            failures.append(f"search_files: {e}")
            print(f"❌ 失败: {e}")
        finally:
            # 清理测试文件
            for f in self.test_data_dir.glob("test*"):
                f.unlink()
        
        return failures
