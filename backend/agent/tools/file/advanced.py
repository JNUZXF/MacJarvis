# File: backend/agent/tools/file/advanced.py
# Purpose: 高级文件操作工具（查找、对比等）
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class FindAdvancedTool:
    """高级文件查找，支持按大小、修改时间、文件类型等条件搜索"""

    name: str = "find_advanced"
    description: str = "高级文件查找，支持按大小、修改时间、文件类型、权限等条件搜索"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "搜索目录"},
                    "name_pattern": {
                        "type": "string",
                        "description": "文件名模式（支持通配符，如*.py）",
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["file", "directory", "symlink"],
                        "description": "文件类型",
                    },
                    "min_size": {
                        "type": "string",
                        "description": "最小文件大小（如100k, 1M, 1G）",
                    },
                    "max_size": {
                        "type": "string",
                        "description": "最大文件大小",
                    },
                    "modified_within": {
                        "type": "string",
                        "description": "修改时间范围（如1表示1天内，7表示7天内）",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "搜索深度",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "最大结果数（默认100）",
                    },
                },
                "required": ["directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        directory_str = args.get("directory", "")
        name_pattern = args.get("name_pattern", "")
        file_type = args.get("file_type", "")
        min_size = args.get("min_size", "")
        max_size = args.get("max_size", "")
        modified_within = args.get("modified_within", "")
        max_depth = args.get("max_depth", 0)
        max_results = int(args.get("max_results", 100))

        if not directory_str:
            return {"ok": False, "error": "directory is required"}

        try:
            directory = normalize_path(directory_str)
            ensure_path_allowed(directory)

            if not directory.exists() or not directory.is_dir():
                return {"ok": False, "error": "目录不存在或不是目录"}

            # 构建find命令
            cmd = ["/usr/bin/find", str(directory)]

            # 添加深度限制
            if max_depth > 0:
                cmd.extend(["-maxdepth", str(max_depth)])

            # 添加文件类型
            if file_type == "file":
                cmd.extend(["-type", "f"])
            elif file_type == "directory":
                cmd.extend(["-type", "d"])
            elif file_type == "symlink":
                cmd.extend(["-type", "l"])

            # 添加文件名模式
            if name_pattern:
                cmd.extend(["-name", name_pattern])

            # 添加大小限制
            if min_size:
                cmd.extend(["-size", f"+{min_size}"])
            if max_size:
                cmd.extend(["-size", f"-{max_size}"])

            # 添加修改时间
            if modified_within:
                cmd.extend(["-mtime", f"-{modified_within}"])

            runner = CommandRunner(timeout_s=60)
            result = runner.run(cmd)

            if result.get("ok"):
                files = result.get("stdout", "").strip().split("\n")
                files = [f for f in files if f][:max_results]

                return {
                    "ok": True,
                    "data": {
                        "files": files,
                        "count": len(files),
                        "directory": str(directory),
                    },
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"文件查找失败: {str(e)}"}


@dataclass
class DiffTool:
    """对比两个文件或目录的差异"""

    name: str = "diff_files"
    description: str = "对比两个文件或目录的差异，生成易读的差异报告"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path1": {
                        "type": "string",
                        "description": "第一个文件/目录路径",
                    },
                    "path2": {
                        "type": "string",
                        "description": "第二个文件/目录路径",
                    },
                    "unified": {
                        "type": "boolean",
                        "description": "使用统一格式（默认true）",
                    },
                    "context_lines": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "description": "上下文行数（默认3）",
                    },
                    "ignore_whitespace": {
                        "type": "boolean",
                        "description": "忽略空白字符差异",
                    },
                },
                "required": ["path1", "path2"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path1_str = args.get("path1", "")
        path2_str = args.get("path2", "")
        unified = args.get("unified", True)
        context_lines = int(args.get("context_lines", 3))
        ignore_whitespace = args.get("ignore_whitespace", False)

        if not path1_str or not path2_str:
            return {"ok": False, "error": "path1 and path2 are required"}

        try:
            path1 = normalize_path(path1_str)
            path2 = normalize_path(path2_str)
            ensure_path_allowed(path1)
            ensure_path_allowed(path2)

            if not path1.exists() or not path2.exists():
                return {"ok": False, "error": "一个或两个路径不存在"}

            # 构建diff命令
            cmd = ["/usr/bin/diff"]

            if unified:
                cmd.extend(["-u", f"-U{context_lines}"])

            if ignore_whitespace:
                cmd.append("-w")

            cmd.extend([str(path1), str(path2)])

            runner = CommandRunner(timeout_s=45)
            result = runner.run(cmd)

            # diff返回码: 0=无差异, 1=有差异, 2=错误
            if result.get("exit_code") in [0, 1]:
                diff_output = result.get("stdout", "")
                has_differences = result.get("exit_code") == 1

                return {
                    "ok": True,
                    "data": {
                        "diff": diff_output,
                        "has_differences": has_differences,
                        "path1": str(path1),
                        "path2": str(path2),
                    },
                }
            else:
                return {
                    "ok": False,
                    "error": f"Diff执行失败: {result.get('stderr', 'Unknown error')}",
                }

        except Exception as e:
            return {"ok": False, "error": f"文件对比失败: {str(e)}"}
