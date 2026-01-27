# File: backend/agent/tools/mac_tools.py
# Purpose: Provide built-in macOS tools and file helpers for the backend agent.
import json
import os
import shutil
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class SimpleCommandTool:
    name: str
    description: str
    parameters: dict[str, Any]
    command: list[str]
    timeout_s: int = 30

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        runner = CommandRunner(timeout_s=self.timeout_s)
        result = runner.run(self.command)
        return result


@dataclass
class SystemInfoTool:
    name: str = "system_info"
    description: str = "获取系统版本、内核与硬件概览"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        runner = CommandRunner(timeout_s=30)
        parts = {
            "sw_vers": runner.run(["sw_vers"]),
            "uname": runner.run(["uname", "-a"]),
            "cpu": runner.run(["sysctl", "-n", "machdep.cpu.brand_string"]),
            "mem_bytes": runner.run(["sysctl", "-n", "hw.memsize"]),
        }
        return {"ok": True, "data": parts}


@dataclass
class TopProcessesTool:
    name: str = "top_processes"
    description: str = "按 CPU 排序获取前 N 个进程"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}},
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 10))
        runner = CommandRunner(timeout_s=20)
        result = runner.run(["ps", "-axo", "pid,pcpu,pmem,comm"])
        if not result.get("ok"):
            return result
        lines = result.get("stdout", "").splitlines()
        if not lines:
            return {"ok": True, "data": []}
        rows = []
        for line in lines[1:]:
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            pid, cpu, mem, command = parts
            try:
                rows.append(
                    {
                        "pid": int(pid),
                        "cpu": float(cpu),
                        "mem": float(mem),
                        "command": command,
                    }
                )
            except ValueError:
                continue
        rows.sort(key=lambda x: x["cpu"], reverse=True)
        return {"ok": True, "data": rows[:limit]}


@dataclass
class ListDirectoryTool:
    name: str = "list_directory"
    description: str = "列出目录内容"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        if not path.exists() or not path.is_dir():
            return {"ok": False, "error": "Path does not exist or is not a directory"}
        entries = sorted(p.name for p in path.iterdir())
        return {"ok": True, "data": entries}


@dataclass
class SearchFilesTool:
    name: str = "search_files"
    description: str = "按通配符在目录中搜索文件"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 500},
                },
                "required": ["path", "pattern"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        pattern = args.get("pattern", "")
        max_results = int(args.get("max_results", 100))
        if not path.exists() or not path.is_dir():
            return {"ok": False, "error": "Path does not exist or is not a directory"}
        matches = []
        for root, _, files in os.walk(path):
            for filename in files:
                if fnmatch(filename, pattern):
                    matches.append(str(Path(root) / filename))
                    if len(matches) >= max_results:
                        return {"ok": True, "data": matches}
        return {"ok": True, "data": matches}


@dataclass
class ReadFileTool:
    name: str = "read_file"
    description: str = "读取文件内容（限制大小）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "minimum": 1, "maximum": 50000},
                },
                "required": ["path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        max_bytes = int(args.get("max_bytes", 20000))
        if not path.exists() or not path.is_file():
            return {"ok": False, "error": "Path does not exist or is not a file"}
        with path.open("rb") as f:
            data = f.read(max_bytes)
        return {"ok": True, "data": data.decode("utf-8", errors="replace")}


@dataclass
class WriteFileTool:
    name: str = "write_file"
    description: str = "写入文本到文件（可选覆盖）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean"},
                    "max_bytes": {"type": "integer", "minimum": 1, "maximum": 100000},
                },
                "required": ["path", "content"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        content = str(args.get("content", ""))
        overwrite = bool(args.get("overwrite", False))
        max_bytes = int(args.get("max_bytes", 50000))
        encoded = content.encode("utf-8")
        if len(encoded) > max_bytes:
            return {"ok": False, "error": "Content exceeds max_bytes limit"}
        if path.exists() and not overwrite:
            return {"ok": False, "error": "File already exists"}
        if not path.parent.exists():
            return {"ok": False, "error": "Parent directory does not exist"}
        with path.open("wb") as f:
            f.write(encoded)
        return {"ok": True, "data": {"bytes": len(encoded)}}


@dataclass
class AppendFileTool:
    name: str = "append_file"
    description: str = "追加文本到文件（可选创建）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "create_if_missing": {"type": "boolean"},
                    "max_bytes": {"type": "integer", "minimum": 1, "maximum": 100000},
                },
                "required": ["path", "content"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        content = str(args.get("content", ""))
        create_if_missing = bool(args.get("create_if_missing", False))
        max_bytes = int(args.get("max_bytes", 50000))
        encoded = content.encode("utf-8")
        if len(encoded) > max_bytes:
            return {"ok": False, "error": "Content exceeds max_bytes limit"}
        if path.exists() and not path.is_file():
            return {"ok": False, "error": "Path exists but is not a file"}
        if not path.exists() and not create_if_missing:
            return {"ok": False, "error": "File does not exist"}
        if not path.parent.exists():
            return {"ok": False, "error": "Parent directory does not exist"}
        with path.open("ab") as f:
            f.write(encoded)
        return {"ok": True, "data": {"bytes": len(encoded)}}


@dataclass
class MakeDirectoryTool:
    name: str = "make_directory"
    description: str = "创建目录"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "parents": {"type": "boolean"},
                    "exist_ok": {"type": "boolean"},
                },
                "required": ["path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        parents = bool(args.get("parents", True))
        exist_ok = bool(args.get("exist_ok", True))
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return {"ok": True, "data": {"created": str(path)}}


@dataclass
class FileInfoTool:
    name: str = "file_info"
    description: str = "获取文件或目录的基础信息"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        if not path.exists():
            return {"ok": False, "error": "Path does not exist"}
        stat = path.stat()
        return {
            "ok": True,
            "data": {
                "path": str(path),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
            },
        }


@dataclass
class FindInFileTool:
    name: str = "find_in_file"
    description: str = "在文本文件中查找关键词"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "query": {"type": "string"},
                    "case_sensitive": {"type": "boolean"},
                    "max_matches": {"type": "integer", "minimum": 1, "maximum": 200},
                    "max_bytes": {"type": "integer", "minimum": 1, "maximum": 200000},
                },
                "required": ["path", "query"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        path = normalize_path(args.get("path", ""))
        ensure_path_allowed(path)
        query = str(args.get("query", ""))
        if not query:
            return {"ok": False, "error": "query is required"}
        case_sensitive = bool(args.get("case_sensitive", True))
        max_matches = int(args.get("max_matches", 50))
        max_bytes = int(args.get("max_bytes", 20000))
        if not path.exists() or not path.is_file():
            return {"ok": False, "error": "Path does not exist or is not a file"}
        with path.open("rb") as f:
            data = f.read(max_bytes)
        content = data.decode("utf-8", errors="replace")
        matches = []
        if not case_sensitive:
            query_lower = query.lower()
        for line_no, line in enumerate(content.splitlines(), start=1):
            hay = line if case_sensitive else line.lower()
            needle = query if case_sensitive else query_lower
            if needle in hay:
                matches.append({"line": line_no, "text": line})
                if len(matches) >= max_matches:
                    break
        return {"ok": True, "data": matches}


@dataclass
class MoveToTrashTool:
    name: str = "move_to_trash"
    description: str = "将文件或目录移动到回收站"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        source = normalize_path(args.get("path", ""))
        ensure_path_allowed(source)
        if not source.exists():
            return {"ok": False, "error": "Path does not exist"}
        trash = Path.home() / ".Trash"
        target = trash / source.name
        shutil.move(str(source), str(target))
        return {"ok": True, "data": {"moved_to": str(target)}}


@dataclass
class OpenAppTool:
    name: str = "open_app"
    description: str = "打开指定应用"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        app_name = str(args.get("app_name", "")).strip()
        if not app_name:
            return {"ok": False, "error": "app_name is required"}
        runner = CommandRunner(timeout_s=10)
        return runner.run(["open", "-a", app_name])


@dataclass
class OpenUrlTool:
    name: str = "open_url"
    description: str = "在默认浏览器打开 URL"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        url = str(args.get("url", "")).strip()
        if not url:
            return {"ok": False, "error": "url is required"}
        runner = CommandRunner(timeout_s=10)
        return runner.run(["open", url])


def build_default_tools() -> list[Any]:
    return [
        SystemInfoTool(),
        SimpleCommandTool(
            name="disk_usage",
            description="查看磁盘空间使用情况",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["df", "-h"],
        ),
        SimpleCommandTool(
            name="process_list",
            description="列出当前进程",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["ps", "aux"],
        ),
        TopProcessesTool(),
        SimpleCommandTool(
            name="open_ports",
            description="列出监听端口",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
        ),
        SimpleCommandTool(
            name="network_info",
            description="获取网络接口信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["ifconfig"],
        ),
        SimpleCommandTool(
            name="dns_info",
            description="获取 DNS 配置",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["scutil", "--dns"],
        ),
        SimpleCommandTool(
            name="wifi_info",
            description="获取当前 Wi-Fi 连接信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["networksetup", "-getairportnetwork", "en0"],
        ),
        ListDirectoryTool(),
        SearchFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        AppendFileTool(),
        MakeDirectoryTool(),
        FileInfoTool(),
        FindInFileTool(),
        MoveToTrashTool(),
        OpenAppTool(),
        OpenUrlTool(),
        SimpleCommandTool(
            name="list_applications",
            description="列出 /Applications 下的应用",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/ls", "/Applications"],
        ),
        SimpleCommandTool(
            name="battery_status",
            description="查看电源与电池状态",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["pmset", "-g", "batt"],
        ),
        SimpleCommandTool(
            name="system_sleep_settings",
            description="查看睡眠与电源策略",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["pmset", "-g"],
        ),
    ]
