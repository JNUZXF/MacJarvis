# File: backend/agent/tools/document/processor.py
# Purpose: 文档处理工具（批量总结、文本提取等）
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.tools.validators import ensure_path_allowed, normalize_path


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
