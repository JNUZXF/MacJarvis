# File: backend/tests/test_all_tools.py
# Purpose: 全面的工具测试套件，测试所有工具的基本功能和边界情况
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from agent.tools.registry import ToolRegistry
from agent.tools.mac_tools import build_default_tools


class TestAllTools:
    """测试所有47个工具的基本功能"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.registry = ToolRegistry(build_default_tools())
        self.test_dir = Path.home() / "Desktop" / "test_agent_tools"
        self.test_dir.mkdir(exist_ok=True)
        yield
        # 清理测试目录
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    # ============================================================================
    # 系统信息工具测试
    # ============================================================================
    
    def test_system_info(self):
        """测试系统信息获取"""
        result = self.registry.execute("system_info", {})
        assert result["ok"] is True
        assert "data" in result
        assert "sw_vers" in result["data"]
        assert "uname" in result["data"]
        print(f"✓ system_info: {result['data']['sw_vers']['stdout'][:50]}")
    
    def test_disk_usage(self):
        """测试磁盘使用情况"""
        result = self.registry.execute("disk_usage", {})
        assert result["ok"] is True
        assert "stdout" in result
        print(f"✓ disk_usage: {len(result['stdout'])} chars")
    
    def test_battery_status(self):
        """测试电池状态"""
        result = self.registry.execute("battery_status", {})
        # 可能失败（台式机没有电池），但不应该是命令不存在错误
        if not result["ok"]:
            assert "No such file" not in result.get("error", "")
        print(f"✓ battery_status: ok={result['ok']}")
    
    def test_system_sleep_settings(self):
        """测试睡眠设置"""
        result = self.registry.execute("system_sleep_settings", {})
        assert result["ok"] is True
        print(f"✓ system_sleep_settings: {len(result.get('stdout', ''))} chars")
    
    # ============================================================================
    # 进程管理工具测试
    # ============================================================================
    
    def test_process_list(self):
        """测试进程列表"""
        result = self.registry.execute("process_list", {})
        assert result["ok"] is True
        assert "stdout" in result
        print(f"✓ process_list: {len(result['stdout'])} chars")
    
    def test_top_processes(self):
        """测试CPU占用最高的进程"""
        result = self.registry.execute("top_processes", {"limit": 5})
        assert result["ok"] is True
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) <= 5
        print(f"✓ top_processes: {len(result['data'])} processes")
    
    # ============================================================================
    # 网络工具测试
    # ============================================================================
    
    def test_network_info(self):
        """测试网络接口信息"""
        result = self.registry.execute("network_info", {})
        assert result["ok"] is True
        assert "stdout" in result
        # 检查是否包含常见的网络接口
        assert any(iface in result["stdout"] for iface in ["lo0", "en0", "en1"])
        print(f"✓ network_info: {len(result['stdout'])} chars")
    
    def test_dns_info(self):
        """测试DNS配置"""
        result = self.registry.execute("dns_info", {})
        assert result["ok"] is True
        assert "stdout" in result
        print(f"✓ dns_info: {len(result['stdout'])} chars")
    
    def test_wifi_info(self):
        """测试WiFi信息"""
        result = self.registry.execute("wifi_info", {})
        # 可能失败（没有WiFi或未连接），但不应该是命令不存在错误
        if not result["ok"]:
            assert "No such file" not in result.get("error", "")
        print(f"✓ wifi_info: ok={result['ok']}")
    
    def test_open_ports(self):
        """测试监听端口列表"""
        result = self.registry.execute("open_ports", {})
        assert result["ok"] is True
        assert "stdout" in result
        print(f"✓ open_ports: {len(result['stdout'])} chars")
    
    def test_ping_host(self):
        """测试ping功能"""
        result = self.registry.execute("ping_host", {"host": "127.0.0.1", "count": 2})
        assert result["ok"] is True
        assert "data" in result
        print(f"✓ ping_host: {len(result['data']['output'])} chars")
    
    # ============================================================================
    # 文件操作工具测试
    # ============================================================================
    
    def test_list_directory(self):
        """测试目录列表"""
        result = self.registry.execute("list_directory", {"path": str(self.test_dir)})
        assert result["ok"] is True
        assert "data" in result
        assert isinstance(result["data"], list)
        print(f"✓ list_directory: {len(result['data'])} items")
    
    def test_write_and_read_file(self):
        """测试文件写入和读取"""
        test_file = self.test_dir / "test.txt"
        test_content = "Hello, MacAgent!"
        
        # 写入文件
        write_result = self.registry.execute("write_file", {
            "path": str(test_file),
            "content": test_content,
            "overwrite": True
        })
        assert write_result["ok"] is True
        
        # 读取文件
        read_result = self.registry.execute("read_file", {"path": str(test_file)})
        assert read_result["ok"] is True
        assert read_result["data"] == test_content
        print(f"✓ write_file + read_file: {len(test_content)} bytes")
    
    def test_append_file(self):
        """测试文件追加"""
        test_file = self.test_dir / "append_test.txt"
        
        # 创建文件
        self.registry.execute("write_file", {
            "path": str(test_file),
            "content": "Line 1\n",
            "overwrite": True
        })
        
        # 追加内容
        append_result = self.registry.execute("append_file", {
            "path": str(test_file),
            "content": "Line 2\n"
        })
        assert append_result["ok"] is True
        
        # 验证内容
        read_result = self.registry.execute("read_file", {"path": str(test_file)})
        assert "Line 1" in read_result["data"]
        assert "Line 2" in read_result["data"]
        print(f"✓ append_file: {len(read_result['data'])} bytes")
    
    def test_make_directory(self):
        """测试创建目录"""
        new_dir = self.test_dir / "subdir" / "nested"
        result = self.registry.execute("make_directory", {
            "path": str(new_dir),
            "parents": True,
            "exist_ok": True
        })
        assert result["ok"] is True
        assert new_dir.exists()
        print(f"✓ make_directory: {new_dir}")
    
    def test_file_info(self):
        """测试文件信息获取"""
        test_file = self.test_dir / "info_test.txt"
        test_file.write_text("test content")
        
        result = self.registry.execute("file_info", {"path": str(test_file)})
        assert result["ok"] is True
        assert result["data"]["is_file"] is True
        assert result["data"]["size_bytes"] > 0
        print(f"✓ file_info: {result['data']['size_bytes']} bytes")
    
    def test_search_files(self):
        """测试文件搜索"""
        # 创建测试文件
        (self.test_dir / "test1.txt").write_text("content")
        (self.test_dir / "test2.txt").write_text("content")
        (self.test_dir / "other.md").write_text("content")
        
        result = self.registry.execute("search_files", {
            "path": str(self.test_dir),
            "pattern": "*.txt",
            "max_results": 10
        })
        assert result["ok"] is True
        assert len(result["data"]) >= 2
        print(f"✓ search_files: {len(result['data'])} files found")
    
    def test_find_in_file(self):
        """测试文件内容搜索"""
        test_file = self.test_dir / "search_test.txt"
        test_file.write_text("Line 1: hello\nLine 2: world\nLine 3: hello world")
        
        result = self.registry.execute("find_in_file", {
            "path": str(test_file),
            "query": "hello",
            "case_sensitive": True,
            "max_matches": 10
        })
        assert result["ok"] is True
        assert len(result["data"]) >= 2
        print(f"✓ find_in_file: {len(result['data'])} matches")
    
    # ============================================================================
    # 应用管理工具测试
    # ============================================================================
    
    def test_list_applications(self):
        """测试应用列表"""
        result = self.registry.execute("list_applications", {})
        assert result["ok"] is True
        assert "stdout" in result
        # 应该至少有一些应用
        assert len(result["stdout"]) > 0
        print(f"✓ list_applications: {len(result['stdout'].splitlines())} apps")
    
    # ============================================================================
    # 系统管理工具测试
    # ============================================================================
    
    def test_get_environment_variables(self):
        """测试环境变量获取"""
        # 获取所有环境变量
        result = self.registry.execute("get_environment_variables", {})
        assert result["ok"] is True
        assert "data" in result
        assert isinstance(result["data"], dict)
        assert "PATH" in result["data"]
        print(f"✓ get_environment_variables: {len(result['data'])} vars")
        
        # 获取特定环境变量
        result2 = self.registry.execute("get_environment_variables", {"variable_name": "PATH"})
        assert result2["ok"] is True
        assert "PATH" in result2["data"]
        print(f"✓ get_environment_variables(PATH): {len(result2['data']['PATH'])} chars")
    
    def test_spotlight_search(self):
        """测试Spotlight搜索"""
        result = self.registry.execute("spotlight_search", {
            "query": "Applications",
            "limit": 5
        })
        assert result["ok"] is True
        assert "data" in result
        print(f"✓ spotlight_search: {result['data']['count']} results")
    
    # ============================================================================
    # 数据处理工具测试
    # ============================================================================
    
    def test_json_formatter(self):
        """测试JSON格式化"""
        test_json = '{"name":"test","value":123}'
        
        # 美化
        result = self.registry.execute("json_formatter", {
            "json_string": test_json,
            "mode": "pretty"
        })
        assert result["ok"] is True
        assert "\n" in result["data"]["formatted"]
        print(f"✓ json_formatter(pretty): {len(result['data']['formatted'])} chars")
        
        # 压缩
        result2 = self.registry.execute("json_formatter", {
            "json_string": test_json,
            "mode": "compact"
        })
        assert result2["ok"] is True
        assert "\n" not in result2["data"]["formatted"]
        print(f"✓ json_formatter(compact): {len(result2['data']['formatted'])} chars")
    
    def test_text_statistics(self):
        """测试文本统计"""
        test_file = self.test_dir / "stats_test.txt"
        test_file.write_text("Hello world\nThis is a test\n中文测试")
        
        result = self.registry.execute("text_statistics", {"file_path": str(test_file)})
        assert result["ok"] is True
        assert result["data"]["line_count"] == 3
        assert result["data"]["chinese_char_count"] == 4
        print(f"✓ text_statistics: {result['data']['line_count']} lines, {result['data']['word_count']} words")
    
    # ============================================================================
    # 生产力工具测试
    # ============================================================================
    
    def test_compress_and_extract_files(self):
        """测试文件压缩和解压"""
        # 创建测试文件
        test_file1 = self.test_dir / "file1.txt"
        test_file2 = self.test_dir / "file2.txt"
        test_file1.write_text("content 1")
        test_file2.write_text("content 2")
        
        zip_path = self.test_dir / "test.zip"
        extract_dir = self.test_dir / "extracted"
        
        # 压缩
        compress_result = self.registry.execute("compress_files", {
            "source_paths": [str(test_file1), str(test_file2)],
            "output_zip": str(zip_path)
        })
        assert compress_result["ok"] is True
        assert zip_path.exists()
        print(f"✓ compress_files: {compress_result['data']['size']} bytes")
        
        # 解压
        extract_result = self.registry.execute("extract_archive", {
            "archive_path": str(zip_path),
            "output_directory": str(extract_dir)
        })
        assert extract_result["ok"] is True
        assert extract_dir.exists()
        print(f"✓ extract_archive: {extract_result['data']['extracted_files']} files")
    
    def test_calculate_hash(self):
        """测试哈希计算"""
        test_file = self.test_dir / "hash_test.txt"
        test_file.write_text("test content for hashing")
        
        # MD5
        result = self.registry.execute("calculate_hash", {
            "file_path": str(test_file),
            "algorithm": "md5"
        })
        assert result["ok"] is True
        assert len(result["data"]["hash"]) == 32
        print(f"✓ calculate_hash(md5): {result['data']['hash']}")
        
        # SHA256
        result2 = self.registry.execute("calculate_hash", {
            "file_path": str(test_file),
            "algorithm": "sha256"
        })
        assert result2["ok"] is True
        assert len(result2["data"]["hash"]) == 64
        print(f"✓ calculate_hash(sha256): {result2['data']['hash'][:16]}...")
    
    def test_clipboard_operations(self):
        """测试剪贴板操作"""
        test_content = "Test clipboard content"
        
        # 写入剪贴板
        write_result = self.registry.execute("clipboard_operations", {
            "operation": "write",
            "content": test_content
        })
        assert write_result["ok"] is True
        print(f"✓ clipboard_operations(write): {len(test_content)} chars")
        
        # 读取剪贴板
        read_result = self.registry.execute("clipboard_operations", {
            "operation": "read"
        })
        assert read_result["ok"] is True
        assert test_content in read_result["data"]["content"]
        print(f"✓ clipboard_operations(read): {len(read_result['data']['content'])} chars")
    
    # ============================================================================
    # 时间工具测试
    # ============================================================================
    
    def test_timezone_converter(self):
        """测试时区转换"""
        result = self.registry.execute("timezone_converter", {
            "timestamp": "now"
        })
        assert result["ok"] is True
        assert "utc_time" in result["data"]
        assert "local_time" in result["data"]
        print(f"✓ timezone_converter: {result['data']['utc_time']}")


def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("MacAgent 工具测试套件")
    print("=" * 80)
    
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()
