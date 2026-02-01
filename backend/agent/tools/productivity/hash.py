# File: backend/agent/tools/productivity/hash.py
# Purpose: 哈希计算工具
import hashlib
from dataclasses import dataclass
from typing import Any

from agent.tools.validators import ensure_path_allowed, normalize_path


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
