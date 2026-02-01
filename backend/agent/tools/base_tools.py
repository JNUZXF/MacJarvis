# File: backend/agent/tools/base_tools.py
# Purpose: 基础工具类定义，包括SimpleCommandTool等通用工具
from dataclasses import dataclass
from typing import Any, Callable, Union

from agent.tools.command_runner import CommandRunner


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
