# File: backend/agent/tools/network/tools.py
# Purpose: 网络工具（下载、网站检查、Ping等）
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.env_detector import get_ping_command
from agent.tools.validators import ensure_path_allowed, normalize_path


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
