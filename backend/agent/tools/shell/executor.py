# File: backend/agent/tools/shell/executor.py
# Purpose: Shell命令执行工具
import subprocess
from dataclasses import dataclass
from typing import Any

from agent.tools.validators import ensure_path_allowed, normalize_path


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
