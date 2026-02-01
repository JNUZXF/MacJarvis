# File: backend/agent/tools/developer/git.py
# Purpose: Git相关工具
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class GitStatusTool:
    """Git状态查询"""

    name: str = "git_status"
    description: str = "查询Git仓库的当前状态"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "repository_path": {
                        "type": "string",
                        "description": "Git仓库路径（默认当前目录）",
                    }
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        repo_path_str = args.get("repository_path", ".")

        try:
            repo_path = normalize_path(repo_path_str)
            ensure_path_allowed(repo_path)

            runner = CommandRunner(timeout_s=30)

            # 切换到仓库目录并执行git status
            result = runner.run(["/usr/bin/git", "-C", str(repo_path), "status", "--short"])

            if result.get("ok"):
                # 同时获取分支信息
                branch_result = runner.run(
                    ["/usr/bin/git", "-C", str(repo_path), "branch", "--show-current"]
                )

                return {
                    "ok": True,
                    "data": {
                        "status": result.get("stdout", ""),
                        "branch": branch_result.get("stdout", "").strip(),
                    },
                }
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Git状态查询失败: {str(e)}"}


@dataclass
class GitLogTool:
    """Git日志查看"""

    name: str = "git_log"
    description: str = "查看Git提交日志"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "repository_path": {"type": "string", "description": "Git仓库路径"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "显示的提交数量",
                    },
                },
                "required": [],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        repo_path_str = args.get("repository_path", ".")
        limit = int(args.get("limit", 10))

        try:
            repo_path = normalize_path(repo_path_str)
            ensure_path_allowed(repo_path)

            runner = CommandRunner(timeout_s=30)
            result = runner.run(
                [
                    "/usr/bin/git",
                    "-C",
                    str(repo_path),
                    "log",
                    f"-{limit}",
                    "--pretty=format:%H|%an|%ae|%ad|%s",
                    "--date=iso",
                ]
            )

            if result.get("ok"):
                return {"ok": True, "data": {"log": result.get("stdout", "")}}
            else:
                return result

        except Exception as e:
            return {"ok": False, "error": f"Git日志查询失败: {str(e)}"}
