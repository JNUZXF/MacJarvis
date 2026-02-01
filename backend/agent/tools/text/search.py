# File: backend/agent/tools/text/search.py
# Purpose: 文本搜索工具（Grep、Tail等）
import re
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class GrepSearchTool:
    """在文件中搜索正则表达式模式"""

    name: str = "grep_search"
    description: str = "在文件中搜索正则表达式模式，支持大小写敏感、行号显示、上下文显示等选项"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索的正则表达式模式",
                    },
                    "file_path": {"type": "string", "description": "要搜索的文件路径"},
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "是否忽略大小写（默认false）",
                    },
                    "show_line_numbers": {
                        "type": "boolean",
                        "description": "是否显示行号（默认true）",
                    },
                    "context_lines": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                        "description": "显示匹配行的上下文行数（默认0）",
                    },
                    "invert_match": {
                        "type": "boolean",
                        "description": "反向匹配（显示不匹配的行）",
                    },
                    "max_matches": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "最大匹配数（默认100）",
                    },
                },
                "required": ["pattern", "file_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        pattern = args.get("pattern", "")
        file_path_str = args.get("file_path", "")
        case_insensitive = args.get("case_insensitive", False)
        show_line_numbers = args.get("show_line_numbers", True)
        context_lines = int(args.get("context_lines", 0))
        invert_match = args.get("invert_match", False)
        max_matches = int(args.get("max_matches", 100))

        if not pattern:
            return {"ok": False, "error": "pattern is required"}

        try:
            file_path = normalize_path(file_path_str)
            ensure_path_allowed(file_path)

            if not file_path.exists() or not file_path.is_file():
                return {"ok": False, "error": "文件不存在或不是文件"}

            # 构建grep命令
            cmd = ["/usr/bin/grep"]

            if case_insensitive:
                cmd.append("-i")
            if show_line_numbers:
                cmd.append("-n")
            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])
            if invert_match:
                cmd.append("-v")

            cmd.extend(["-m", str(max_matches)])  # 限制匹配数
            cmd.extend(["-E", pattern, str(file_path)])  # 使用扩展正则

            runner = CommandRunner(timeout_s=30)
            result = runner.run(cmd)

            # grep返回码: 0=找到匹配, 1=未找到匹配, 2=错误
            if result.get("exit_code") in [0, 1]:
                matches = result.get("stdout", "")
                return {
                    "ok": True,
                    "data": {
                        "matches": matches,
                        "match_count": len(matches.splitlines()) if matches else 0,
                        "pattern": pattern,
                        "file": str(file_path),
                    },
                }
            else:
                return {
                    "ok": False,
                    "error": f"Grep执行失败: {result.get('stderr', 'Unknown error')}",
                }

        except Exception as e:
            return {"ok": False, "error": f"Grep搜索失败: {str(e)}"}


@dataclass
class GrepRecursiveTool:
    """递归搜索目录中的所有文件"""

    name: str = "grep_recursive"
    description: str = "递归搜索目录中的所有文件，支持文件类型过滤、排除目录等"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索的正则表达式模式",
                    },
                    "directory": {"type": "string", "description": "要搜索的目录路径"},
                    "file_pattern": {
                        "type": "string",
                        "description": "文件名模式（如*.py, *.log）",
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要排除的目录列表（如node_modules, .git）",
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "是否忽略大小写",
                    },
                    "show_line_numbers": {
                        "type": "boolean",
                        "description": "是否显示行号（默认true）",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "description": "最大结果数（默认100）",
                    },
                },
                "required": ["pattern", "directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        pattern = args.get("pattern", "")
        directory_str = args.get("directory", "")
        file_pattern = args.get("file_pattern", "*")
        exclude_dirs = args.get("exclude_dirs", [".git", "node_modules", "__pycache__"])
        case_insensitive = args.get("case_insensitive", False)
        show_line_numbers = args.get("show_line_numbers", True)
        max_results = int(args.get("max_results", 100))

        if not pattern or not directory_str:
            return {"ok": False, "error": "pattern and directory are required"}

        try:
            directory = normalize_path(directory_str)
            ensure_path_allowed(directory)

            if not directory.exists() or not directory.is_dir():
                return {"ok": False, "error": "目录不存在或不是目录"}

            # 构建grep命令
            cmd = ["/usr/bin/grep", "-r"]  # 递归搜索

            if case_insensitive:
                cmd.append("-i")
            if show_line_numbers:
                cmd.append("-n")

            cmd.extend(["-m", str(max_results)])  # 限制总匹配数
            cmd.extend(["-E", pattern])  # 使用扩展正则

            # 添加文件包含模式
            if file_pattern and file_pattern != "*":
                cmd.extend(["--include", file_pattern])

            # 添加排除目录
            for exclude_dir in exclude_dirs:
                cmd.extend(["--exclude-dir", exclude_dir])

            cmd.append(str(directory))

            runner = CommandRunner(timeout_s=60)  # 递归搜索可能需要更长时间
            result = runner.run(cmd)

            # grep返回码: 0=找到匹配, 1=未找到匹配, 2=错误
            if result.get("exit_code") in [0, 1]:
                matches = result.get("stdout", "")
                match_lines = matches.splitlines() if matches else []

                # 解析结果，按文件分组
                files_matched = {}
                for line in match_lines:
                    if ":" in line:
                        file_part, content = line.split(":", 1)
                        if file_part not in files_matched:
                            files_matched[file_part] = []
                        files_matched[file_part].append(content)

                return {
                    "ok": True,
                    "data": {
                        "matches": matches,
                        "match_count": len(match_lines),
                        "files_matched": len(files_matched),
                        "pattern": pattern,
                        "directory": str(directory),
                    },
                }
            else:
                return {
                    "ok": False,
                    "error": f"Grep执行失败: {result.get('stderr', 'Unknown error')}",
                }

        except Exception as e:
            return {"ok": False, "error": f"递归搜索失败: {str(e)}"}


@dataclass
class TailLogTool:
    """实时查看日志文件的最新内容"""

    name: str = "tail_log"
    description: str = "查看日志文件的最新内容，支持持续监控和过滤"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "日志文件路径"},
                    "lines": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "显示的行数（默认100）",
                    },
                    "filter_pattern": {
                        "type": "string",
                        "description": "过滤模式（仅显示匹配的行）",
                    },
                },
                "required": ["file_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        file_path_str = args.get("file_path", "")
        lines = int(args.get("lines", 100))
        filter_pattern = args.get("filter_pattern", "")

        if not file_path_str:
            return {"ok": False, "error": "file_path is required"}

        try:
            file_path = normalize_path(file_path_str)
            ensure_path_allowed(file_path)

            if not file_path.exists() or not file_path.is_file():
                return {"ok": False, "error": "文件不存在或不是文件"}

            # 构建tail命令
            cmd = ["/usr/bin/tail", "-n", str(lines), str(file_path)]

            runner = CommandRunner(timeout_s=10)
            result = runner.run(cmd)

            if result.get("ok"):
                content = result.get("stdout", "")

                # 如果有过滤模式，进行过滤
                if filter_pattern:
                    filtered_lines = []
                    for line in content.splitlines():
                        if re.search(filter_pattern, line, re.IGNORECASE):
                            filtered_lines.append(line)
                    content = "\n".join(filtered_lines)

                return {
                    "ok": True,
                    "data": {
                        "content": content,
                        "line_count": len(content.splitlines()),
                        "file": str(file_path),
                    },
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"读取日志失败: {str(e)}"}
