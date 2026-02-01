# File: backend/agent/tools/productivity/clipboard.py
# Purpose: 剪贴板操作工具
import subprocess
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner


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
