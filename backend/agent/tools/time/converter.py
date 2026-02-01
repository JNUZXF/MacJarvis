# File: backend/agent/tools/time/converter.py
# Purpose: 时区转换工具
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agent.tools.command_runner import CommandRunner


@dataclass
class TimezoneConverterTool:
    """时区转换"""

    name: str = "timezone_converter"
    description: str = "转换时间到不同时区"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "string",
                        "description": "ISO格式时间戳或'now'表示当前时间",
                    },
                    "target_timezone": {
                        "type": "string",
                        "description": "目标时区（如：Asia/Shanghai, America/New_York）",
                    },
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        timestamp_str = args.get("timestamp", "now")
        target_tz = args.get("target_timezone", "")

        try:
            # 获取当前时间
            if timestamp_str == "now":
                now = datetime.now(timezone.utc)
            else:
                now = datetime.fromisoformat(timestamp_str)

            result_data = {
                "utc_time": now.astimezone(timezone.utc).isoformat(),
                "local_time": datetime.now().isoformat(),
                "timestamp": int(now.timestamp()),
            }

            if target_tz:
                # 使用系统命令获取时区时间
                runner = CommandRunner(timeout_s=10)
                tz_result = runner.run(
                    ["TZ=" + target_tz, "/bin/date", "+%Y-%m-%dT%H:%M:%S%z"]
                )
                if tz_result.get("ok"):
                    result_data["target_timezone_time"] = tz_result.get("stdout", "").strip()

            return {"ok": True, "data": result_data}

        except Exception as e:
            return {"ok": False, "error": f"时区转换失败: {str(e)}"}
