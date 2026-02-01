# File: backend/agent/tools/data/processor.py
# Purpose: 数据处理工具（JSON格式化、CSV分析、文本统计等）
import csv
import json
import re
from dataclasses import dataclass
from typing import Any

from agent.tools.validators import ensure_path_allowed, normalize_path


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
