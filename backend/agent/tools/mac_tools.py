# File: backend/agent/tools/mac_tools.py
# Purpose: Provide built-in macOS tools and file helpers for the backend agent.
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Callable, Union

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path
from agent.tools.env_detector import (
    get_network_info_command,
    get_dns_info_command,
    get_wifi_info_command,
    get_open_ports_command,
    get_ping_command,
)


@dataclass
class SimpleCommandTool:
    name: str
    description: str
    parameters: dict[str, Any]
    command: Union[list[str], Callable[[], list[str]]]
    timeout_s: int = 30

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        runner = CommandRunner(timeout_s=self.timeout_s)
        # 如果command是可调用对象，则调用它获取命令
        if callable(self.command):
            cmd = self.command()
        else:
            cmd = self.command
        result = runner.run(cmd)
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
            "sw_vers": runner.run(["/usr/bin/sw_vers"]),
            "uname": runner.run(["/usr/bin/uname", "-a"]),
            "cpu": runner.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"]),
            "mem_bytes": runner.run(["/usr/sbin/sysctl", "-n", "hw.memsize"]),
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
        result = runner.run(["/bin/ps", "-axo", "pid,pcpu,pmem,comm"])
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
        return runner.run(["/usr/bin/open", "-a", app_name])


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
        return runner.run(["/usr/bin/open", url])


# ============================================================================
# 文档处理工具 - Document Processing Tools
# ============================================================================


@dataclass
class BatchSummarizeDocumentsTool:
    """多线程批量总结多个文档（PDF/Word/Excel/TXT等）并保存摘要到本地"""

    name: str = "batch_summarize_documents"
    description: str = "多线程批量总结多个文档（支持PDF/Word/Excel/TXT等），生成摘要并保存到指定位置"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要总结的文件路径列表",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "保存摘要的输出文件路径（Markdown格式）",
                    },
                    "max_workers": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "最大并发线程数",
                    },
                    "summary_length": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "description": "摘要长度：short(简短), medium(中等), long(详细)",
                    },
                },
                "required": ["file_paths", "output_path"],
            }

    def _extract_text_from_file(self, file_path: Path) -> str:
        """从文件中提取文本内容"""
        try:
            suffix = file_path.suffix.lower()

            # PDF文件
            if suffix == ".pdf":
                try:
                    import PyPDF2

                    with open(file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages[:20]:  # 限制前20页
                            text += page.extract_text() + "\n"
                        return text[:10000]  # 限制字符数
                except Exception:
                    return "[PDF解析失败]"

            # Word文档
            elif suffix in [".docx", ".doc"]:
                try:
                    import docx

                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs[:100]])
                    return text[:10000]
                except Exception:
                    return "[Word文档解析失败]"

            # Excel文件
            elif suffix in [".xlsx", ".xls"]:
                try:
                    import pandas as pd

                    df = pd.read_excel(file_path, nrows=100)
                    return df.to_string()[:10000]
                except Exception:
                    return "[Excel解析失败]"

            # 纯文本文件
            elif suffix in [".txt", ".md", ".json", ".csv", ".log"]:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(10000)

            else:
                return f"[不支持的文件格式: {suffix}]"

        except Exception as e:
            return f"[文件读取失败: {str(e)}]"

    def _generate_summary(self, text: str, length: str) -> str:
        """生成文本摘要"""
        if not text or text.startswith("["):
            return text

        lines = text.split("\n")
        lines = [line.strip() for line in lines if line.strip()]

        # 根据长度选择摘要行数
        length_map = {"short": 5, "medium": 15, "long": 30}
        max_lines = length_map.get(length, 15)

        # 简单的摘要策略：取前N行 + 关键信息
        summary_lines = []
        word_count = 0

        for line in lines[:max_lines]:
            summary_lines.append(line)
            word_count += len(line)
            if word_count > 1000 and length == "short":
                break
            if word_count > 3000 and length == "medium":
                break

        summary = "\n".join(summary_lines)

        # 添加统计信息
        stats = f"\n\n**统计**: 总字符数={len(text)}, 总行数={len(lines)}"
        return summary + stats

    def _process_single_file(
        self, file_path_str: str, length: str
    ) -> tuple[str, str, bool]:
        """处理单个文件"""
        try:
            file_path = normalize_path(file_path_str)
            ensure_path_allowed(file_path)

            if not file_path.exists() or not file_path.is_file():
                return file_path_str, "[文件不存在或不是文件]", False

            # 提取文本
            text = self._extract_text_from_file(file_path)

            # 生成摘要
            summary = self._generate_summary(text, length)

            return file_path_str, summary, True

        except Exception as e:
            return file_path_str, f"[处理失败: {str(e)}]", False

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        file_paths = args.get("file_paths", [])
        output_path_str = args.get("output_path", "")
        max_workers = int(args.get("max_workers", 4))
        length = args.get("summary_length", "medium")

        if not file_paths:
            return {"ok": False, "error": "file_paths is required"}

        if not output_path_str:
            return {"ok": False, "error": "output_path is required"}

        try:
            output_path = normalize_path(output_path_str)
            ensure_path_allowed(output_path)

            # 多线程处理文件
            results = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = [
                    executor.submit(self._process_single_file, fp, length)
                    for fp in file_paths
                ]

                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

            # 生成Markdown报告
            report_lines = [
                "# 文档批量摘要报告",
                f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"处理文件数: {len(file_paths)}",
                f"摘要长度: {length}",
                "\n---\n",
            ]

            success_count = 0
            for file_path, summary, success in results:
                if success:
                    success_count += 1

                report_lines.append(f"## 📄 {Path(file_path).name}\n")
                report_lines.append(f"**路径**: `{file_path}`\n")
                report_lines.append(f"**状态**: {'✅ 成功' if success else '❌ 失败'}\n")
                report_lines.append("**摘要**:\n")
                report_lines.append(f"```\n{summary}\n```\n")
                report_lines.append("\n---\n")

            report_lines.append(
                f"\n## 📊 总结\n\n- 总文件数: {len(file_paths)}\n- 成功: {success_count}\n- 失败: {len(file_paths) - success_count}"
            )

            report_content = "\n".join(report_lines)

            # 保存报告
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            return {
                "ok": True,
                "data": {
                    "output_file": str(output_path),
                    "total_files": len(file_paths),
                    "success_count": success_count,
                    "failed_count": len(file_paths) - success_count,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"批量总结失败: {str(e)}"}


@dataclass
class ExtractTextFromDocumentsTool:
    """批量从文档中提取纯文本"""

    name: str = "extract_text_from_documents"
    description: str = "批量从多个文档（PDF/Word/Excel等）中提取纯文本内容"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文件路径列表",
                    },
                    "output_directory": {
                        "type": "string",
                        "description": "输出目录（每个文件生成对应的.txt文件）",
                    },
                },
                "required": ["file_paths", "output_directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        file_paths = args.get("file_paths", [])
        output_dir_str = args.get("output_directory", "")

        if not file_paths or not output_dir_str:
            return {"ok": False, "error": "file_paths and output_directory are required"}

        try:
            output_dir = normalize_path(output_dir_str)
            ensure_path_allowed(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            results = []
            for fp in file_paths:
                file_path = normalize_path(fp)
                ensure_path_allowed(file_path)

                # 使用BatchSummarizeDocumentsTool的提取逻辑
                tool = BatchSummarizeDocumentsTool()
                text = tool._extract_text_from_file(file_path)

                # 保存为txt
                output_file = output_dir / f"{file_path.stem}.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(text)

                results.append({"file": str(file_path), "output": str(output_file)})

            return {"ok": True, "data": {"extracted_files": results}}

        except Exception as e:
            return {"ok": False, "error": f"文本提取失败: {str(e)}"}


# ============================================================================
# 媒体处理工具 - Media Processing Tools
# ============================================================================


@dataclass
class CompressImagesTool:
    """批量压缩图片"""

    name: str = "compress_images"
    description: str = "批量压缩图片文件，支持JPG/PNG格式，减小文件大小"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "image_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "图片文件路径列表",
                    },
                    "output_directory": {"type": "string", "description": "输出目录"},
                    "quality": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "压缩质量（1-100，默认85）",
                    },
                },
                "required": ["image_paths", "output_directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        image_paths = args.get("image_paths", [])
        output_dir_str = args.get("output_directory", "")
        quality = int(args.get("quality", 85))

        if not image_paths or not output_dir_str:
            return {"ok": False, "error": "image_paths and output_directory are required"}

        try:
            from PIL import Image

            output_dir = normalize_path(output_dir_str)
            ensure_path_allowed(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            results = []
            for img_path_str in image_paths:
                img_path = normalize_path(img_path_str)
                ensure_path_allowed(img_path)

                if not img_path.exists():
                    results.append(
                        {
                            "file": str(img_path),
                            "success": False,
                            "error": "文件不存在",
                        }
                    )
                    continue

                try:
                    img = Image.open(img_path)
                    output_file = output_dir / img_path.name

                    # 转换RGBA到RGB
                    if img.mode == "RGBA":
                        img = img.convert("RGB")

                    img.save(output_file, optimize=True, quality=quality)

                    original_size = img_path.stat().st_size
                    compressed_size = output_file.stat().st_size
                    ratio = (
                        (1 - compressed_size / original_size) * 100
                        if original_size > 0
                        else 0
                    )

                    results.append(
                        {
                            "file": str(img_path),
                            "output": str(output_file),
                            "success": True,
                            "original_size": original_size,
                            "compressed_size": compressed_size,
                            "compression_ratio": f"{ratio:.1f}%",
                        }
                    )
                except Exception as e:
                    results.append(
                        {"file": str(img_path), "success": False, "error": str(e)}
                    )

            return {"ok": True, "data": {"results": results}}

        except ImportError:
            return {"ok": False, "error": "PIL库未安装，请安装pillow: pip install pillow"}
        except Exception as e:
            return {"ok": False, "error": f"图片压缩失败: {str(e)}"}


@dataclass
class CaptureScreenshotTool:
    """截屏工具"""

    name: str = "capture_screenshot"
    description: str = "捕获屏幕截图，可选择全屏或指定区域"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "保存截图的路径"},
                    "display": {
                        "type": "integer",
                        "description": "显示器编号（默认1）",
                    },
                    "interactive": {
                        "type": "boolean",
                        "description": "是否交互式选择区域",
                    },
                },
                "required": ["output_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        output_path_str = args.get("output_path", "")
        display = args.get("display", 1)
        interactive = args.get("interactive", False)

        if not output_path_str:
            return {"ok": False, "error": "output_path is required"}

        try:
            output_path = normalize_path(output_path_str)
            ensure_path_allowed(output_path)

            cmd = ["/usr/sbin/screencapture"]

            if interactive:
                cmd.append("-i")  # 交互式选择
            else:
                cmd.extend(["-D", str(display)])  # 指定显示器

            cmd.append(str(output_path))

            runner = CommandRunner(timeout_s=30)
            result = runner.run(cmd)

            if result.get("ok"):
                return {
                    "ok": True,
                    "data": {"screenshot_path": str(output_path)},
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"截图失败: {str(e)}"}


@dataclass
class GetVideoInfoTool:
    """获取视频文件信息"""

    name: str = "get_video_info"
    description: str = "获取视频文件的详细信息（时长、分辨率、编码等）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"video_path": {"type": "string", "description": "视频文件路径"}},
                "required": ["video_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        video_path_str = args.get("video_path", "")

        if not video_path_str:
            return {"ok": False, "error": "video_path is required"}

        try:
            video_path = normalize_path(video_path_str)
            ensure_path_allowed(video_path)

            if not video_path.exists():
                return {"ok": False, "error": "视频文件不存在"}

            # 使用ffprobe获取视频信息
            runner = CommandRunner(timeout_s=30)
            result = runner.run(
                [
                    "/usr/local/bin/ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(video_path),
                ]
            )

            if result.get("ok"):
                try:
                    info = json.loads(result.get("stdout", "{}"))
                    return {"ok": True, "data": info}
                except json.JSONDecodeError:
                    return {"ok": False, "error": "解析视频信息失败"}
            else:
                # ffprobe不可用，返回基本信息
                stat = video_path.stat()
                return {
                    "ok": True,
                    "data": {
                        "file": str(video_path),
                        "size": stat.st_size,
                        "note": "ffprobe不可用，仅提供基本信息",
                    },
                }

        except Exception as e:
            return {"ok": False, "error": f"获取视频信息失败: {str(e)}"}


# ============================================================================
# 开发者工具 - Developer Tools
# ============================================================================


@dataclass
class GitStatusTool:
    """Git状态查询"""

    name: str = "git_status"
    description: str = "查询Git仓库的当前状态"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "repository_path": {
                        "type": "string",
                        "description": "Git仓库路径（默认当前目录）",
                    }
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        repo_path_str = args.get("repository_path", ".")

        try:
            repo_path = normalize_path(repo_path_str)
            ensure_path_allowed(repo_path)

            runner = CommandRunner(timeout_s=30)

            # 切换到仓库目录并执行git status
            result = runner.run(["/usr/bin/git", "-C", str(repo_path), "status", "--short"])

            if result.get("ok"):
                # 同时获取分支信息
                branch_result = runner.run(
                    ["/usr/bin/git", "-C", str(repo_path), "branch", "--show-current"]
                )

                return {
                    "ok": True,
                    "data": {
                        "status": result.get("stdout", ""),
                        "branch": branch_result.get("stdout", "").strip(),
                    },
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Git状态查询失败: {str(e)}"}


@dataclass
class GitLogTool:
    """Git日志查看"""

    name: str = "git_log"
    description: str = "查看Git提交日志"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "repository_path": {"type": "string", "description": "Git仓库路径"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "显示的提交数量",
                    },
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        repo_path_str = args.get("repository_path", ".")
        limit = int(args.get("limit", 10))

        try:
            repo_path = normalize_path(repo_path_str)
            ensure_path_allowed(repo_path)

            runner = CommandRunner(timeout_s=30)
            result = runner.run(
                [
                    "/usr/bin/git",
                    "-C",
                    str(repo_path),
                    "log",
                    f"-{limit}",
                    "--pretty=format:%H|%an|%ae|%ad|%s",
                    "--date=iso",
                ]
            )

            if result.get("ok"):
                return {"ok": True, "data": {"log": result.get("stdout", "")}}
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Git日志查询失败: {str(e)}"}


@dataclass
class RunPythonScriptTool:
    """执行Python脚本"""

    name: str = "run_python_script"
    description: str = "执行指定的Python脚本文件"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Python脚本路径"},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "脚本参数列表",
                    },
                    "working_directory": {"type": "string", "description": "工作目录"},
                },
                "required": ["script_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        script_path_str = args.get("script_path", "")
        script_args = args.get("args", [])
        working_dir = args.get("working_directory", "")

        if not script_path_str:
            return {"ok": False, "error": "script_path is required"}

        try:
            script_path = normalize_path(script_path_str)
            ensure_path_allowed(script_path)

            if not script_path.exists():
                return {"ok": False, "error": "脚本文件不存在"}

            cmd = ["/usr/bin/python3", str(script_path)] + script_args

            if working_dir:
                wd_path = normalize_path(working_dir)
                ensure_path_allowed(wd_path)
                runner = CommandRunner(timeout_s=120, cwd=str(wd_path))
            else:
                runner = CommandRunner(timeout_s=120)

            return runner.run(cmd)

        except Exception as e:
            return {"ok": False, "error": f"Python脚本执行失败: {str(e)}"}


# ============================================================================
# 生产力工具 - Productivity Tools
# ============================================================================


@dataclass
class CompressFilesTool:
    """压缩文件或目录"""

    name: str = "compress_files"
    description: str = "将文件或目录压缩为ZIP格式"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "source_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要压缩的文件或目录路径列表",
                    },
                    "output_zip": {"type": "string", "description": "输出ZIP文件路径"},
                },
                "required": ["source_paths", "output_zip"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        source_paths = args.get("source_paths", [])
        output_zip_str = args.get("output_zip", "")

        if not source_paths or not output_zip_str:
            return {"ok": False, "error": "source_paths and output_zip are required"}

        try:
            output_zip = normalize_path(output_zip_str)
            ensure_path_allowed(output_zip)

            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for sp in source_paths:
                    source_path = normalize_path(sp)
                    ensure_path_allowed(source_path)

                    if not source_path.exists():
                        continue

                    if source_path.is_file():
                        zf.write(source_path, source_path.name)
                    elif source_path.is_dir():
                        for file_path in source_path.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(source_path.parent)
                                zf.write(file_path, arcname)

            return {
                "ok": True,
                "data": {
                    "output_zip": str(output_zip),
                    "size": output_zip.stat().st_size,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"文件压缩失败: {str(e)}"}


@dataclass
class ExtractArchiveTool:
    """解压缩文件"""

    name: str = "extract_archive"
    description: str = "解压缩ZIP文件到指定目录"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string", "description": "ZIP文件路径"},
                    "output_directory": {"type": "string", "description": "解压到的目录"},
                },
                "required": ["archive_path", "output_directory"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        archive_path_str = args.get("archive_path", "")
        output_dir_str = args.get("output_directory", "")

        if not archive_path_str or not output_dir_str:
            return {"ok": False, "error": "archive_path and output_directory are required"}

        try:
            archive_path = normalize_path(archive_path_str)
            ensure_path_allowed(archive_path)

            output_dir = normalize_path(output_dir_str)
            ensure_path_allowed(output_dir)

            if not archive_path.exists():
                return {"ok": False, "error": "压缩文件不存在"}

            output_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(output_dir)
                file_list = zf.namelist()

            return {
                "ok": True,
                "data": {
                    "output_directory": str(output_dir),
                    "extracted_files": len(file_list),
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"解压缩失败: {str(e)}"}


@dataclass
class CalculateHashTool:
    """计算文件哈希值"""

    name: str = "calculate_hash"
    description: str = "计算文件的哈希值（MD5/SHA256）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"],
                        "description": "哈希算法",
                    },
                },
                "required": ["file_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        file_path_str = args.get("file_path", "")
        algorithm = args.get("algorithm", "sha256")

        if not file_path_str:
            return {"ok": False, "error": "file_path is required"}

        try:
            file_path = normalize_path(file_path_str)
            ensure_path_allowed(file_path)

            if not file_path.exists() or not file_path.is_file():
                return {"ok": False, "error": "文件不存在"}

            hash_func = getattr(hashlib, algorithm)()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)

            return {
                "ok": True,
                "data": {
                    "file": str(file_path),
                    "algorithm": algorithm,
                    "hash": hash_func.hexdigest(),
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"哈希计算失败: {str(e)}"}


@dataclass
class ClipboardOperationsTool:
    """剪贴板操作"""

    name: str = "clipboard_operations"
    description: str = "读取或写入系统剪贴板内容"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write"],
                        "description": "操作类型：read（读取）或write（写入）",
                    },
                    "content": {
                        "type": "string",
                        "description": "写入剪贴板的内容（仅在write操作时需要）",
                    },
                },
                "required": ["operation"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        operation = args.get("operation", "")
        content = args.get("content", "")

        if not operation:
            return {"ok": False, "error": "operation is required"}

        try:
            runner = CommandRunner(timeout_s=10)

            if operation == "read":
                result = runner.run(["/usr/bin/pbpaste"])
                if result.get("ok"):
                    return {
                        "ok": True,
                        "data": {"content": result.get("stdout", "")},
                    }
                else:
                    return result

            elif operation == "write":
                if not content:
                    return {"ok": False, "error": "content is required for write operation"}

                # 使用echo + pbcopy
                proc = subprocess.run(
                    ["/usr/bin/pbcopy"],
                    input=content.encode("utf-8"),
                    capture_output=True,
                    timeout=10,
                )

                if proc.returncode == 0:
                    return {"ok": True, "data": {"message": "内容已写入剪贴板"}}
                else:
                    return {
                        "ok": False,
                        "error": f"写入失败: {proc.stderr.decode('utf-8')}",
                    }

            else:
                return {"ok": False, "error": "Invalid operation"}

        except Exception as e:
            return {"ok": False, "error": f"剪贴板操作失败: {str(e)}"}


# ============================================================================
# 系统管理工具 - System Management Tools
# ============================================================================


@dataclass
class GetEnvironmentVariablesTool:
    """获取环境变量"""

    name: str = "get_environment_variables"
    description: str = "获取系统环境变量"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "variable_name": {
                        "type": "string",
                        "description": "特定环境变量名（可选，留空返回所有）",
                    }
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        variable_name = args.get("variable_name", "")

        try:
            if variable_name:
                value = os.environ.get(variable_name)
                if value is None:
                    return {"ok": False, "error": f"环境变量 {variable_name} 不存在"}
                return {"ok": True, "data": {variable_name: value}}
            else:
                # 返回所有环境变量
                return {"ok": True, "data": dict(os.environ)}

        except Exception as e:
            return {"ok": False, "error": f"获取环境变量失败: {str(e)}"}


@dataclass
class SpotlightSearchTool:
    """Spotlight搜索"""

    name: str = "spotlight_search"
    description: str = "使用macOS Spotlight搜索文件和应用"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "返回结果数量",
                    },
                },
                "required": ["query"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query", "")
        limit = int(args.get("limit", 10))

        if not query:
            return {"ok": False, "error": "query is required"}

        try:
            runner = CommandRunner(timeout_s=30)
            result = runner.run(["/usr/bin/mdfind", "-limit", str(limit), query])

            if result.get("ok"):
                files = result.get("stdout", "").strip().split("\n")
                files = [f for f in files if f]
                return {"ok": True, "data": {"results": files, "count": len(files)}}
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Spotlight搜索失败: {str(e)}"}


# ============================================================================
# 网络工具 - Network Tools
# ============================================================================


@dataclass
class DownloadFileTool:
    """下载文件"""

    name: str = "download_file"
    description: str = "从URL下载文件到本地"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "文件URL"},
                    "output_path": {"type": "string", "description": "保存路径"},
                },
                "required": ["url", "output_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url", "")
        output_path_str = args.get("output_path", "")

        if not url or not output_path_str:
            return {"ok": False, "error": "url and output_path are required"}

        try:
            output_path = normalize_path(output_path_str)
            ensure_path_allowed(output_path)

            runner = CommandRunner(timeout_s=300)
            result = runner.run(["/usr/bin/curl", "-L", "-o", str(output_path), url])

            if result.get("ok"):
                size = output_path.stat().st_size if output_path.exists() else 0
                return {
                    "ok": True,
                    "data": {"output_path": str(output_path), "size": size},
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"文件下载失败: {str(e)}"}


@dataclass
class CheckWebsiteStatusTool:
    """检查网站状态"""

    name: str = "check_website_status"
    description: str = "检查网站是否可访问及响应时间"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "网站URL"}},
                "required": ["url"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        url = args.get("url", "")

        if not url:
            return {"ok": False, "error": "url is required"}

        try:
            runner = CommandRunner(timeout_s=30)
            result = runner.run(
                ["/usr/bin/curl", "-I", "-s", "-o", "/dev/null", "-w", "%{http_code}", url]
            )

            if result.get("ok"):
                status_code = result.get("stdout", "").strip()
                return {
                    "ok": True,
                    "data": {"url": url, "status_code": status_code},
                }
            else:
                return {"ok": False, "error": "网站无法访问"}

        except Exception as e:
            return {"ok": False, "error": f"网站检查失败: {str(e)}"}


@dataclass
class PingHostTool:
    """Ping主机"""

    name: str = "ping_host"
    description: str = "Ping指定主机检测网络连接"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "主机名或IP地址"},
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Ping次数",
                    },
                },
                "required": ["host"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        host = args.get("host", "")
        count = int(args.get("count", 4))

        if not host:
            return {"ok": False, "error": "host is required"}

        try:
            runner = CommandRunner(timeout_s=30)
            ping_cmd = get_ping_command()
            result = runner.run(ping_cmd + ["-c", str(count), host])

            if result.get("ok"):
                return {"ok": True, "data": {"output": result.get("stdout", "")}}
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Ping失败: {str(e)}"}


# ============================================================================
# 数据处理工具 - Data Processing Tools
# ============================================================================


@dataclass
class JsonFormatterTool:
    """JSON格式化"""

    name: str = "json_formatter"
    description: str = "格式化或压缩JSON数据"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "json_string": {"type": "string", "description": "JSON字符串"},
                    "mode": {
                        "type": "string",
                        "enum": ["pretty", "compact"],
                        "description": "格式化模式：pretty（美化）或compact（压缩）",
                    },
                },
                "required": ["json_string"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        json_string = args.get("json_string", "")
        mode = args.get("mode", "pretty")

        if not json_string:
            return {"ok": False, "error": "json_string is required"}

        try:
            data = json.loads(json_string)

            if mode == "pretty":
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                formatted = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

            return {"ok": True, "data": {"formatted": formatted}}

        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"JSON解析失败: {str(e)}"}
        except Exception as e:
            return {"ok": False, "error": f"JSON格式化失败: {str(e)}"}


@dataclass
class CsvAnalyzerTool:
    """CSV数据分析"""

    name: str = "csv_analyzer"
    description: str = "分析CSV文件，提供基本统计信息"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"csv_path": {"type": "string", "description": "CSV文件路径"}},
                "required": ["csv_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        csv_path_str = args.get("csv_path", "")

        if not csv_path_str:
            return {"ok": False, "error": "csv_path is required"}

        try:
            csv_path = normalize_path(csv_path_str)
            ensure_path_allowed(csv_path)

            if not csv_path.exists():
                return {"ok": False, "error": "CSV文件不存在"}

            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                return {"ok": False, "error": "CSV文件为空"}

            headers = list(rows[0].keys())
            row_count = len(rows)

            # 统计每列的信息
            column_stats = {}
            for header in headers:
                values = [row.get(header, "") for row in rows]
                non_empty = [v for v in values if v]

                column_stats[header] = {
                    "total_values": len(values),
                    "non_empty_values": len(non_empty),
                    "empty_values": len(values) - len(non_empty),
                    "sample_values": non_empty[:5],
                }

            return {
                "ok": True,
                "data": {
                    "file": str(csv_path),
                    "row_count": row_count,
                    "column_count": len(headers),
                    "headers": headers,
                    "column_statistics": column_stats,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"CSV分析失败: {str(e)}"}


@dataclass
class TextStatisticsTool:
    """文本统计分析"""

    name: str = "text_statistics"
    description: str = "分析文本文件的统计信息（字数、行数、字符数等）"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "文本文件路径"}},
                "required": ["file_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        file_path_str = args.get("file_path", "")

        if not file_path_str:
            return {"ok": False, "error": "file_path is required"}

        try:
            file_path = normalize_path(file_path_str)
            ensure_path_allowed(file_path)

            if not file_path.exists() or not file_path.is_file():
                return {"ok": False, "error": "文件不存在"}

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = content.split("\n")
            words = content.split()

            # 字符统计
            char_count = len(content)
            char_count_no_spaces = len(content.replace(" ", "").replace("\n", ""))

            # 中英文统计
            chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
            english_words = len(re.findall(r"\b[a-zA-Z]+\b", content))

            return {
                "ok": True,
                "data": {
                    "file": str(file_path),
                    "line_count": len(lines),
                    "word_count": len(words),
                    "char_count": char_count,
                    "char_count_no_spaces": char_count_no_spaces,
                    "chinese_char_count": chinese_chars,
                    "english_word_count": english_words,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"文本统计失败: {str(e)}"}


# ============================================================================
# 日历和时间工具 - Calendar and Time Tools
# ============================================================================


@dataclass
class TimezoneConverterTool:
    """时区转换"""

    name: str = "timezone_converter"
    description: str = "转换时间到不同时区"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "string",
                        "description": "ISO格式时间戳或'now'表示当前时间",
                    },
                    "target_timezone": {
                        "type": "string",
                        "description": "目标时区（如：Asia/Shanghai, America/New_York）",
                    },
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        timestamp_str = args.get("timestamp", "now")
        target_tz = args.get("target_timezone", "")

        try:
            # 获取当前时间
            if timestamp_str == "now":
                now = datetime.now(timezone.utc)
            else:
                now = datetime.fromisoformat(timestamp_str)

            result_data = {
                "utc_time": now.astimezone(timezone.utc).isoformat(),
                "local_time": datetime.now().isoformat(),
                "timestamp": int(now.timestamp()),
            }

            if target_tz:
                # 使用系统命令获取时区时间
                runner = CommandRunner(timeout_s=10)
                tz_result = runner.run(
                    ["TZ=" + target_tz, "/bin/date", "+%Y-%m-%dT%H:%M:%S%z"]
                )
                if tz_result.get("ok"):
                    result_data["target_timezone_time"] = tz_result.get("stdout", "").strip()

            return {"ok": True, "data": result_data}

        except Exception as e:
            return {"ok": False, "error": f"时区转换失败: {str(e)}"}


# ============================================================================
# 文本处理工具 - Text Processing Tools (新增)
# ============================================================================


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


@dataclass
class PortKillerTool:
    """查找并杀死占用指定端口的进程"""

    name: str = "port_killer"
    description: str = "查找并杀死占用指定端口的进程，开发者常用工具"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                        "description": "端口号",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "强制杀死进程（默认false）",
                    },
                    "show_process_info": {
                        "type": "boolean",
                        "description": "显示进程详细信息（默认true）",
                    },
                },
                "required": ["port"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        port = int(args.get("port", 0))
        force = args.get("force", False)
        show_process_info = args.get("show_process_info", True)

        if not port or port < 1 or port > 65535:
            return {"ok": False, "error": "Invalid port number"}

        try:
            runner = CommandRunner(timeout_s=10)

            # 查找占用端口的进程
            # 使用lsof命令查找端口占用
            result = runner.run(["/usr/sbin/lsof", "-ti", f":{port}"])

            if not result.get("ok"):
                return {
                    "ok": True,
                    "data": {"message": f"端口 {port} 未被占用"},
                }

            pids = result.get("stdout", "").strip().split("\n")
            pids = [pid.strip() for pid in pids if pid.strip()]

            if not pids:
                return {
                    "ok": True,
                    "data": {"message": f"端口 {port} 未被占用"},
                }

            # 获取进程信息
            process_info = []
            if show_process_info:
                for pid in pids:
                    ps_result = runner.run(["/bin/ps", "-p", pid, "-o", "pid,comm,args"])
                    if ps_result.get("ok"):
                        process_info.append(ps_result.get("stdout", ""))

            # 杀死进程
            killed_pids = []
            for pid in pids:
                signal = "-9" if force else "-15"
                kill_result = runner.run(["/bin/kill", signal, pid])
                if kill_result.get("ok") or kill_result.get("exit_code") == 0:
                    killed_pids.append(pid)

            return {
                "ok": True,
                "data": {
                    "port": port,
                    "killed_pids": killed_pids,
                    "process_info": process_info if show_process_info else [],
                    "force": force,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"杀死进程失败: {str(e)}"}


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


@dataclass
class ExecuteShellCommandTool:
    """执行任意Shell命令 - 像人类一样使用命令行"""

    name: str = "execute_shell_command"
    description: str = "执行任意Shell命令，支持管道、重定向等Shell特性。注意：危险命令会被拒绝执行"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的Shell命令（支持管道、重定向等）",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "工作目录（可选，默认为当前目录）",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 300,
                        "description": "超时时间（秒，默认60秒）",
                    },
                },
                "required": ["command"],
            }

    def _is_dangerous_command(self, command: str) -> tuple[bool, str]:
        """检查命令是否危险"""
        dangerous_patterns = [
            ("rm -rf /", "禁止删除根目录"),
            ("rm -rf /*", "禁止删除根目录下所有文件"),
            ("mkfs", "禁止格式化磁盘"),
            ("dd if=/dev/zero", "禁止危险的dd操作"),
            (":(){ :|:& };:", "禁止fork炸弹"),
            ("> /dev/sda", "禁止直接写入磁盘设备"),
            ("chmod -R 777 /", "禁止修改根目录权限"),
            ("chown -R", "禁止递归修改所有权"),
        ]

        command_lower = command.lower().strip()
        for pattern, reason in dangerous_patterns:
            if pattern.lower() in command_lower:
                return True, reason

        return False, ""

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        command = args.get("command", "").strip()
        working_dir = args.get("working_directory", "")
        timeout = int(args.get("timeout", 60))

        if not command:
            return {"ok": False, "error": "command is required"}

        # 安全检查
        is_dangerous, reason = self._is_dangerous_command(command)
        if is_dangerous:
            return {
                "ok": False,
                "error": f"危险命令被拒绝: {reason}",
                "command": command,
            }

        try:
            # 处理工作目录
            cwd = None
            if working_dir:
                wd_path = normalize_path(working_dir)
                ensure_path_allowed(wd_path)
                if not wd_path.exists() or not wd_path.is_dir():
                    return {"ok": False, "error": "工作目录不存在或不是目录"}
                cwd = str(wd_path)

            # 执行命令（使用shell=True以支持管道、重定向等）
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "exit_code": proc.returncode,
                "command": command,
                "working_directory": cwd or "当前目录",
            }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"命令执行超时（{timeout}秒）",
                "command": command,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"命令执行失败: {str(e)}",
                "command": command,
            }


def build_default_tools() -> list[Any]:
    """构建默认工具集 - 共50个工具，覆盖工作生活的方方面面
    
    核心工具:
    - ExecuteShellCommandTool: 执行任意Shell命令（支持管道、重定向，内置安全检查）
    
    高级工具:
    - GrepSearchTool: 在文件中搜索正则表达式
    - GrepRecursiveTool: 递归搜索目录
    - TailLogTool: 查看日志文件
    - FindAdvancedTool: 高级文件查找
    - DiffTool: 文件对比
    - PortKillerTool: 杀死占用端口的进程
    """
    return [
        # ============================================================
        # 系统信息与监控工具 (System Information & Monitoring)
        # ============================================================
        SystemInfoTool(),
        SimpleCommandTool(
            name="disk_usage",
            description="查看磁盘空间使用情况",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/df", "-h"],
        ),
        SimpleCommandTool(
            name="battery_status",
            description="查看电源与电池状态",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/usr/bin/pmset", "-g", "batt"],
        ),
        SimpleCommandTool(
            name="system_sleep_settings",
            description="查看睡眠与电源策略",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/usr/bin/pmset", "-g"],
        ),
        # ============================================================
        # 进程管理工具 (Process Management)
        # ============================================================
        SimpleCommandTool(
            name="process_list",
            description="列出当前进程",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/ps", "aux"],
        ),
        TopProcessesTool(),
        # ============================================================
        # 网络工具 (Network Tools)
        # ============================================================
        SimpleCommandTool(
            name="open_ports",
            description="列出监听端口",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_open_ports_command,
        ),
        SimpleCommandTool(
            name="network_info",
            description="获取网络接口信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_network_info_command,
        ),
        SimpleCommandTool(
            name="dns_info",
            description="获取 DNS 配置",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_dns_info_command,
        ),
        SimpleCommandTool(
            name="wifi_info",
            description="获取当前 Wi-Fi 连接信息",
            parameters={"type": "object", "properties": {}, "required": []},
            command=get_wifi_info_command,
        ),
        DownloadFileTool(),
        CheckWebsiteStatusTool(),
        PingHostTool(),
        # ============================================================
        # 文件管理工具 (File Management)
        # ============================================================
        ListDirectoryTool(),
        SearchFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        AppendFileTool(),
        MakeDirectoryTool(),
        FileInfoTool(),
        FindInFileTool(),
        MoveToTrashTool(),
        # ============================================================
        # 文档处理工具 (Document Processing) - 重点功能
        # ============================================================
        BatchSummarizeDocumentsTool(),  # 多线程批量文档总结 - 核心功能
        ExtractTextFromDocumentsTool(),  # 批量提取文本
        # ============================================================
        # 媒体处理工具 (Media Processing)
        # ============================================================
        CompressImagesTool(),  # 批量图片压缩
        CaptureScreenshotTool(),  # 截屏
        GetVideoInfoTool(),  # 视频信息
        # ============================================================
        # 开发者工具 (Developer Tools)
        # ============================================================
        GitStatusTool(),  # Git状态
        GitLogTool(),  # Git日志
        RunPythonScriptTool(),  # 执行Python脚本
        # ============================================================
        # 生产力工具 (Productivity Tools)
        # ============================================================
        CompressFilesTool(),  # 压缩文件
        ExtractArchiveTool(),  # 解压缩
        CalculateHashTool(),  # 计算哈希
        ClipboardOperationsTool(),  # 剪贴板操作
        # ============================================================
        # 系统管理工具 (System Management)
        # ============================================================
        GetEnvironmentVariablesTool(),  # 环境变量
        SpotlightSearchTool(),  # Spotlight搜索
        # ============================================================
        # 数据处理工具 (Data Processing)
        # ============================================================
        JsonFormatterTool(),  # JSON格式化
        CsvAnalyzerTool(),  # CSV分析
        TextStatisticsTool(),  # 文本统计
        # ============================================================
        # 时间工具 (Time Tools)
        # ============================================================
        TimezoneConverterTool(),  # 时区转换
        # ============================================================
        # 应用管理工具 (Application Management)
        # ============================================================
        OpenAppTool(),
        OpenUrlTool(),
        SimpleCommandTool(
            name="list_applications",
            description="列出 /Applications 下的应用",
            parameters={"type": "object", "properties": {}, "required": []},
            command=["/bin/ls", "-1", "/Applications"],
        ),
        # ============================================================
        # 文本处理工具 (Text Processing) - 新增
        # ============================================================
        GrepSearchTool(),  # 在文件中搜索正则表达式
        GrepRecursiveTool(),  # 递归搜索目录
        TailLogTool(),  # 查看日志文件
        # ============================================================
        # 高级文件操作 (Advanced File Operations) - 新增
        # ============================================================
        FindAdvancedTool(),  # 高级文件查找
        DiffTool(),  # 文件对比
        # ============================================================
        # 开发者工具增强 (Developer Tools Enhanced) - 新增
        # ============================================================
        PortKillerTool(),  # 杀死占用端口的进程
        # ============================================================
        # 通用命令执行 (Universal Command Execution) - 核心功能
        # ============================================================
        ExecuteShellCommandTool(),  # 执行任意Shell命令
    ]
