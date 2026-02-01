# File: backend/agent/tools/productivity/archive.py
# Purpose: 压缩解压工具
import zipfile
from dataclasses import dataclass
from typing import Any

from agent.tools.validators import ensure_path_allowed, normalize_path


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
