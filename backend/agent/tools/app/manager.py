# File: backend/agent/tools/app/manager.py
# Purpose: 应用管理工具（打开应用、打开URL等）
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner


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
