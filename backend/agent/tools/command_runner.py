# File: backend/agent/tools/command_runner.py
# Purpose: Execute system commands with timeout control.
import subprocess
from typing import Sequence


class CommandRunner:
    def __init__(self, timeout_s: int = 30) -> None:
        self.timeout_s = timeout_s

    def run(self, command: Sequence[str]) -> dict[str, str | int | bool]:
        try:
            completed = subprocess.run(
                list(command),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
            return {
                "ok": completed.returncode == 0,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "exit_code": completed.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Command timed out", "exit_code": -1}
        except OSError as exc:
            return {"ok": False, "error": str(exc), "exit_code": -1}
