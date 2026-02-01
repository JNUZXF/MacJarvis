# File: backend/agent/tools/system/info.py
# Purpose: 系统信息查询工具
from dataclasses import dataclass
from typing import Any

from agent.tools.base_tools import SimpleCommandTool
from agent.tools.command_runner import CommandRunner


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
