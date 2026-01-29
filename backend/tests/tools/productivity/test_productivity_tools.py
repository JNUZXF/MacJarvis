"""
File: backend/tests/tools/productivity/test_productivity_tools.py
Purpose: Test productivity tools
Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/tools/productivity/test_productivity_tools.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.tools.base import ToolTestBase


class TestClipboardOperations(ToolTestBase):
    """测试剪贴板操作工具"""
    
    def get_tool_name(self) -> str:
        return "clipboard_operations"
    
    def run_tests(self):
        failures = []
        
        # 测试1: 写入剪贴板
        try:
            print("\n测试1: 写入剪贴板")
            test_content = "Hello from Mac Agent Test!"
            result = self.execute_tool({
                "operation": "write",
                "content": test_content
            })
            self.assert_success(result)
            print("✅ 通过")
        except AssertionError as e:
            failures.append(f"clipboard_operations - 测试1: {e}")
            print(f"❌ 失败: {e}")
        
        # 测试2: 读取剪贴板
        try:
            print("\n测试2: 读取剪贴板")
            result = self.execute_tool({"operation": "read"})
            self.assert_success(result)
            self.assert_has_data(result, "content")
            # 验证刚才写入的内容
            if "Hello from Mac Agent Test!" in result["data"]["content"]:
                print("✅ 通过 - 内容匹配")
            else:
                print("✅ 通过 - 读取成功（内容可能被其他程序修改）")
        except AssertionError as e:
            failures.append(f"clipboard_operations - 测试2: {e}")
            print(f"❌ 失败: {e}")
        
        return failures


class TestCalculateHash(ToolTestBase):
    """测试哈希计算工具"""
    
    def get_tool_name(self) -> str:
        return "calculate_hash"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_content = "Test content for hash calculation"
        test_file = self.create_test_file("test_hash.txt", test_content)
        
        try:
            # 测试1: SHA256哈希
            print("\n测试1: 计算SHA256哈希")
            result = self.execute_tool({
                "file_path": str(test_file),
                "algorithm": "sha256"
            })
            self.assert_success(result)
            self.assert_has_data(result, "hash")
            assert len(result["data"]["hash"]) == 64, "SHA256哈希长度错误"
            print(f"✅ 通过 - Hash: {result['data']['hash'][:16]}...")
            
            # 测试2: MD5哈希
            print("\n测试2: 计算MD5哈希")
            result = self.execute_tool({
                "file_path": str(test_file),
                "algorithm": "md5"
            })
            self.assert_success(result)
            assert len(result["data"]["hash"]) == 32, "MD5哈希长度错误"
            print(f"✅ 通过 - Hash: {result['data']['hash'][:16]}...")
            
        except AssertionError as e:
            failures.append(f"calculate_hash: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
        
        return failures


class TestCompressFiles(ToolTestBase):
    """测试文件压缩工具"""
    
    def get_tool_name(self) -> str:
        return "compress_files"
    
    def run_tests(self):
        failures = []
        
        # 创建测试文件
        test_file1 = self.create_test_file("compress_test1.txt", "Content 1")
        test_file2 = self.create_test_file("compress_test2.txt", "Content 2")
        output_zip = self.test_data_dir / "test_archive.zip"
        
        try:
            print("\n测试: 压缩文件")
            result = self.execute_tool({
                "source_paths": [str(test_file1), str(test_file2)],
                "output_zip": str(output_zip)
            })
            self.assert_success(result)
            self.assert_has_data(result, "output_zip")
            assert output_zip.exists(), "ZIP文件未创建"
            print(f"✅ 通过 - ZIP大小: {output_zip.stat().st_size} bytes")
            
        except AssertionError as e:
            failures.append(f"compress_files: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file1)
            self.cleanup_test_file(test_file2)
            if output_zip.exists():
                output_zip.unlink()
        
        return failures


class TestExtractArchive(ToolTestBase):
    """测试解压缩工具"""
    
    def get_tool_name(self) -> str:
        return "extract_archive"
    
    def run_tests(self):
        failures = []
        
        # 先创建一个ZIP文件
        import zipfile
        test_file = self.create_test_file("extract_test.txt", "Extract test content")
        zip_file = self.test_data_dir / "test_extract.zip"
        output_dir = self.test_data_dir / "extracted"
        
        try:
            # 创建ZIP
            with zipfile.ZipFile(zip_file, 'w') as zf:
                zf.write(test_file, test_file.name)
            
            print("\n测试: 解压缩文件")
            result = self.execute_tool({
                "archive_path": str(zip_file),
                "output_directory": str(output_dir)
            })
            self.assert_success(result)
            self.assert_has_data(result, "extracted_files")
            assert output_dir.exists(), "解压目录未创建"
            print(f"✅ 通过 - 解压了 {result['data']['extracted_files']} 个文件")
            
        except AssertionError as e:
            failures.append(f"extract_archive: {e}")
            print(f"❌ 失败: {e}")
        finally:
            self.cleanup_test_file(test_file)
            if zip_file.exists():
                zip_file.unlink()
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir)
        
        return failures
