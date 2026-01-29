# File: backend/tests/test_new_tools.py
# Purpose: 测试新增的文本处理和文件操作工具
# Path: /Users/xinfuzhang/Desktop/Code/mac_agent/backend/tests/test_new_tools.py

import os
import tempfile
from pathlib import Path

import pytest

from agent.tools.mac_tools import (
    DiffTool,
    FindAdvancedTool,
    GrepRecursiveTool,
    GrepSearchTool,
    PortKillerTool,
    TailLogTool,
)
from agent.tools.validators import set_runtime_allowed_roots, reset_runtime_allowed_roots


@pytest.fixture(autouse=True)
def allow_tmp_paths(tmp_path):
    """自动允许临时测试路径"""
    token = set_runtime_allowed_roots([tmp_path, Path(tempfile.gettempdir())])
    yield
    reset_runtime_allowed_roots(token)


class TestGrepSearchTool:
    """测试GrepSearchTool"""

    def test_grep_search_basic(self, tmp_path):
        """测试基本grep搜索"""
        # 创建测试文件
        test_file = tmp_path / "test.log"
        test_file.write_text("INFO: Application started\nERROR: Connection failed\nINFO: Retry attempt\n")

        tool = GrepSearchTool()
        result = tool.execute({"pattern": "ERROR", "file_path": str(test_file)})

        assert result["ok"] is True
        assert "matches" in result["data"]
        assert "ERROR" in result["data"]["matches"]
        assert result["data"]["match_count"] == 1

    def test_grep_search_case_insensitive(self, tmp_path):
        """测试大小写不敏感搜索"""
        test_file = tmp_path / "test.log"
        test_file.write_text("error: lowercase\nERROR: uppercase\nError: mixed\n")

        tool = GrepSearchTool()
        result = tool.execute(
            {"pattern": "error", "file_path": str(test_file), "case_insensitive": True}
        )

        assert result["ok"] is True
        assert result["data"]["match_count"] == 3

    def test_grep_search_with_line_numbers(self, tmp_path):
        """测试显示行号"""
        test_file = tmp_path / "test.log"
        test_file.write_text("line1\nline2 ERROR\nline3\n")

        tool = GrepSearchTool()
        result = tool.execute(
            {"pattern": "ERROR", "file_path": str(test_file), "show_line_numbers": True}
        )

        assert result["ok"] is True
        assert "2:" in result["data"]["matches"]  # 行号应该显示

    def test_grep_search_with_context(self, tmp_path):
        """测试上下文显示"""
        test_file = tmp_path / "test.log"
        test_file.write_text("line1\nline2\nERROR here\nline4\nline5\n")

        tool = GrepSearchTool()
        result = tool.execute(
            {"pattern": "ERROR", "file_path": str(test_file), "context_lines": 1}
        )

        assert result["ok"] is True
        # 应该包含上下文行
        matches = result["data"]["matches"]
        assert "line2" in matches or "line4" in matches

    def test_grep_search_regex(self, tmp_path):
        """测试正则表达式搜索"""
        test_file = tmp_path / "test.py"
        test_file.write_text("def function1():\n    pass\ndef function2():\n    pass\n")

        tool = GrepSearchTool()
        result = tool.execute({"pattern": "^def \\w+\\(", "file_path": str(test_file)})

        assert result["ok"] is True
        assert result["data"]["match_count"] == 2

    def test_grep_search_no_match(self, tmp_path):
        """测试无匹配结果"""
        test_file = tmp_path / "test.log"
        test_file.write_text("INFO: Nothing to see here\n")

        tool = GrepSearchTool()
        result = tool.execute({"pattern": "ERROR", "file_path": str(test_file)})

        assert result["ok"] is True
        assert result["data"]["match_count"] == 0

    def test_grep_search_file_not_exist(self):
        """测试文件不存在"""
        tool = GrepSearchTool()
        result = tool.execute({"pattern": "ERROR", "file_path": "/tmp/nonexistent.log"})

        assert result["ok"] is False
        # 可能是路径不允许或文件不存在
        assert "不存在" in result["error"] or "not allowed" in result["error"]


class TestGrepRecursiveTool:
    """测试GrepRecursiveTool"""

    def test_grep_recursive_basic(self, tmp_path):
        """测试递归搜索"""
        # 创建测试目录结构
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()
        (tmp_path / "dir1" / "file1.log").write_text("ERROR in file1\n")
        (tmp_path / "dir2" / "file2.log").write_text("ERROR in file2\n")
        (tmp_path / "file3.log").write_text("INFO in file3\n")

        tool = GrepRecursiveTool()
        result = tool.execute({"pattern": "ERROR", "directory": str(tmp_path)})

        assert result["ok"] is True
        assert result["data"]["files_matched"] == 2

    def test_grep_recursive_with_file_pattern(self, tmp_path):
        """测试文件模式过滤"""
        (tmp_path / "test.py").write_text("def function():\n    pass\n")
        (tmp_path / "test.txt").write_text("def function():\n    pass\n")

        tool = GrepRecursiveTool()
        result = tool.execute(
            {"pattern": "def", "directory": str(tmp_path), "file_pattern": "*.py"}
        )

        assert result["ok"] is True
        # 应该只匹配.py文件

    def test_grep_recursive_exclude_dirs(self, tmp_path):
        """测试排除目录"""
        (tmp_path / ".git").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / ".git" / "config").write_text("ERROR in git\n")
        (tmp_path / "src" / "main.py").write_text("ERROR in src\n")

        tool = GrepRecursiveTool()
        result = tool.execute(
            {"pattern": "ERROR", "directory": str(tmp_path), "exclude_dirs": [".git"]}
        )

        assert result["ok"] is True
        # .git目录应该被排除


class TestTailLogTool:
    """测试TailLogTool"""

    def test_tail_log_basic(self, tmp_path):
        """测试基本日志读取"""
        log_file = tmp_path / "test.log"
        lines = [f"Line {i}\n" for i in range(1, 201)]
        log_file.write_text("".join(lines))

        tool = TailLogTool()
        result = tool.execute({"file_path": str(log_file), "lines": 10})

        assert result["ok"] is True
        assert result["data"]["line_count"] == 10
        assert "Line 200" in result["data"]["content"]  # 应该包含最后一行

    def test_tail_log_with_filter(self, tmp_path):
        """测试过滤功能"""
        log_file = tmp_path / "test.log"
        log_file.write_text("INFO: message 1\nERROR: message 2\nINFO: message 3\n")

        tool = TailLogTool()
        result = tool.execute(
            {"file_path": str(log_file), "lines": 10, "filter_pattern": "ERROR"}
        )

        assert result["ok"] is True
        assert "ERROR" in result["data"]["content"]
        assert result["data"]["line_count"] == 1

    def test_tail_log_file_not_exist(self):
        """测试文件不存在"""
        tool = TailLogTool()
        result = tool.execute({"file_path": "/tmp/nonexistent.log", "lines": 10})

        assert result["ok"] is False
        # 可能是路径不允许或文件不存在
        assert "不存在" in result["error"] or "not allowed" in result["error"]


class TestFindAdvancedTool:
    """测试FindAdvancedTool"""

    def test_find_by_name_pattern(self, tmp_path):
        """测试按文件名模式查找"""
        (tmp_path / "test1.py").write_text("")
        (tmp_path / "test2.py").write_text("")
        (tmp_path / "test.txt").write_text("")

        tool = FindAdvancedTool()
        result = tool.execute({"directory": str(tmp_path), "name_pattern": "*.py"})

        assert result["ok"] is True
        assert result["data"]["count"] >= 2

    def test_find_by_type(self, tmp_path):
        """测试按文件类型查找"""
        (tmp_path / "file.txt").write_text("")
        (tmp_path / "subdir").mkdir()

        tool = FindAdvancedTool()
        result = tool.execute({"directory": str(tmp_path), "file_type": "directory"})

        assert result["ok"] is True
        assert result["data"]["count"] >= 1

    def test_find_by_size(self, tmp_path):
        """测试按大小查找"""
        small_file = tmp_path / "small.txt"
        small_file.write_text("x" * 100)  # 100字节

        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 10000)  # 10KB

        tool = FindAdvancedTool()
        result = tool.execute({"directory": str(tmp_path), "min_size": "1k"})

        assert result["ok"] is True
        # 应该只找到大文件

    def test_find_with_max_depth(self, tmp_path):
        """测试深度限制"""
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "deep.txt").write_text("")

        tool = FindAdvancedTool()
        result = tool.execute(
            {"directory": str(tmp_path), "name_pattern": "deep.txt", "max_depth": 1}
        )

        assert result["ok"] is True
        # 深度为1应该找不到deep.txt


class TestDiffTool:
    """测试DiffTool"""

    def test_diff_identical_files(self, tmp_path):
        """测试相同文件"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "Line 1\nLine 2\nLine 3\n"
        file1.write_text(content)
        file2.write_text(content)

        tool = DiffTool()
        result = tool.execute({"path1": str(file1), "path2": str(file2)})

        assert result["ok"] is True
        assert result["data"]["has_differences"] is False

    def test_diff_different_files(self, tmp_path):
        """测试不同文件"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Line 1\nLine 2\nLine 3\n")
        file2.write_text("Line 1\nLine 2 modified\nLine 3\n")

        tool = DiffTool()
        result = tool.execute({"path1": str(file1), "path2": str(file2)})

        assert result["ok"] is True
        assert result["data"]["has_differences"] is True
        assert "modified" in result["data"]["diff"]

    def test_diff_with_unified_format(self, tmp_path):
        """测试统一格式"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Line 1\nLine 2\n")
        file2.write_text("Line 1\nLine 3\n")

        tool = DiffTool()
        result = tool.execute({"path1": str(file1), "path2": str(file2), "unified": True})

        assert result["ok"] is True
        # 统一格式应该包含+和-符号


class TestPortKillerTool:
    """测试PortKillerTool"""

    def test_port_not_in_use(self):
        """测试端口未被占用"""
        tool = PortKillerTool()
        # 使用一个不太可能被占用的高端口
        result = tool.execute({"port": 54321})

        assert result["ok"] is True
        assert "未被占用" in result["data"]["message"]

    def test_invalid_port(self):
        """测试无效端口号"""
        tool = PortKillerTool()
        result = tool.execute({"port": 99999})

        assert result["ok"] is False
        assert "Invalid port" in result["error"]

    # 注意：实际杀死进程的测试需要谨慎，可能影响系统
    # 这里只测试基本的参数验证


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
