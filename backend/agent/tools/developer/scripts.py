# File: backend/agent/tools/developer/scripts.py
# Purpose: 脚本执行和进程管理工具
from dataclasses import dataclass
from typing import Any

from agent.tools.command_runner import CommandRunner
from agent.tools.validators import ensure_path_allowed, normalize_path


@dataclass
class RunPythonScriptTool:
    """执行Python脚本"""

    name: str = "run_python_script"
    description: str = "执行指定的Python脚本文件"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Python脚本路径"},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "脚本参数列表",
                    },
                    "working_directory": {"type": "string", "description": "工作目录"},
                },
                "required": ["script_path"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        script_path_str = args.get("script_path", "")
        script_args = args.get("args", [])
        working_dir = args.get("working_directory", "")

        if not script_path_str:
            return {"ok": False, "error": "script_path is required"}

        try:
            script_path = normalize_path(script_path_str)
            ensure_path_allowed(script_path)

            if not script_path.exists():
                return {"ok": False, "error": "脚本文件不存在"}

            cmd = ["/usr/bin/python3", str(script_path)] + script_args

            if working_dir:
                wd_path = normalize_path(working_dir)
                ensure_path_allowed(wd_path)
                runner = CommandRunner(timeout_s=120, cwd=str(wd_path))
            else:
                runner = CommandRunner(timeout_s=120)

            return runner.run(cmd)

        except Exception as e:
            return {"ok": False, "error": f"Python脚本执行失败: {str(e)}"}


@dataclass
class PortKillerTool:
    """查找并杀死占用指定端口的进程"""

    name: str = "port_killer"
    description: str = "查找并杀死占用指定端口的进程，开发者常用工具"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                        "description": "端口号",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "强制杀死进程（默认false）",
                    },
                    "show_process_info": {
                        "type": "boolean",
                        "description": "显示进程详细信息（默认true）",
                    },
                },
                "required": ["port"],
            }

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        port = int(args.get("port", 0))
        force = args.get("force", False)
        show_process_info = args.get("show_process_info", True)

        if not port or port < 1 or port > 65535:
            return {"ok": False, "error": "Invalid port number"}

        try:
            runner = CommandRunner(timeout_s=10)

            # 查找占用端口的进程
            # 使用lsof命令查找端口占用
            result = runner.run(["/usr/sbin/lsof", "-ti", f":{port}"])

            if not result.get("ok"):
                return {
                    "ok": True,
                    "data": {"message": f"端口 {port} 未被占用"},
                }

            pids = result.get("stdout", "").strip().split("\n")
            pids = [pid.strip() for pid in pids if pid.strip()]

            if not pids:
                return {
                    "ok": True,
                    "data": {"message": f"端口 {port} 未被占用"},
                }

            # 获取进程信息
            process_info = []
            if show_process_info:
                for pid in pids:
                    ps_result = runner.run(["/bin/ps", "-p", pid, "-o", "pid,comm,args"])
                    if ps_result.get("ok"):
                        process_info.append(ps_result.get("stdout", ""))

            # 杀死进程
            killed_pids = []
            for pid in pids:
                signal = "-9" if force else "-15"
                kill_result = runner.run(["/bin/kill", signal, pid])
                if kill_result.get("ok") or kill_result.get("exit_code") == 0:
                    killed_pids.append(pid)

            return {
                "ok": True,
                "data": {
                    "port": port,
                    "killed_pids": killed_pids,
                    "process_info": process_info if show_process_info else [],
                    "force": force,
                },
            }

        except Exception as e:
            return {"ok": False, "error": f"杀死进程失败: {str(e)}"}
