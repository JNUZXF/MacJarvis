# File: backend/agent/tools/system/management.py
# Purpose: 系统管理工具（环境变量、Spotlight搜索等）
import os
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner


@dataclass
class GetEnvironmentVariablesTool:
    """获取环境变量"""

    name: str = "get_environment_variables"
    description: str = "获取系统环境变量"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "variable_name": {
                        "type": "string",
                        "description": "特定环境变量名（可选，留空返回所有）",
                    }
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        variable_name = args.get("variable_name", "")

        try:
            if variable_name:
                value = os.environ.get(variable_name)
                if value is None:
                    return {"ok": False, "error": f"环境变量 {variable_name} 不存在"}
                return {"ok": True, "data": {variable_name: value}}
            else:
                # 返回所有环境变量
                return {"ok": True, "data": dict(os.environ)}

        except Exception as e:
            return {"ok": False, "error": f"获取环境变量失败: {str(e)}"}


@dataclass
class SpotlightSearchTool:
    """Spotlight搜索"""

    name: str = "spotlight_search"
    description: str = "使用macOS Spotlight搜索文件和应用"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "返回结果数量",
                    },
                },
                "required": ["query"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query", "")
        limit = int(args.get("limit", 10))

        if not query:
            return {"ok": False, "error": "query is required"}

        try:
            runner = CommandRunner(timeout_s=30)
            # mdfind不支持-limit参数，需要通过管道限制结果
            result = runner.run(["/usr/bin/mdfind", query])

            if result.get("ok"):
                files = result.get("stdout", "").strip().split("\n")
                files = [f for f in files if f]
                # 手动限制结果数量
                files = files[:limit]
                return {"ok": True, "data": {"results": files, "count": len(files)}}
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Spotlight搜索失败: {str(e)}"}
