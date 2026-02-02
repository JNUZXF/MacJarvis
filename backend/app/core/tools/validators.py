# File: backend/agent/tools/validators.py
# Purpose: Validate and normalize file paths for tool access control.
import contextvars
import getpass
import os
from pathlib import Path


BASE_ALLOWED_ROOTS = [
    # 默认允许全盘路径，避免额外配置导致路径被拒绝
    Path("/"),
]

_RUNTIME_ALLOWED_ROOTS: contextvars.ContextVar[list[Path]] = contextvars.ContextVar(
    "runtime_allowed_roots",
    default=[],
)


def get_allowed_roots() -> list[Path]:
    roots = list(BASE_ALLOWED_ROOTS)
    # 允许当前工作目录，避免容器/相对路径被拒绝
    try:
        roots.append(Path.cwd().resolve())
    except OSError:
        pass
    extra = os.getenv("AGENT_ALLOWED_ROOTS", "")
    if extra:
        for raw in extra.split(os.pathsep):
            raw = raw.strip()
            if not raw:
                continue
            try:
                roots.append(Path(raw).expanduser().resolve())
            except OSError:
                continue
    runtime_roots = _RUNTIME_ALLOWED_ROOTS.get()
    for root in runtime_roots:
        roots.append(root)
    # 去重
    seen = set()
    unique_roots = []
    for root in roots:
        if root in seen:
            continue
        unique_roots.append(root)
        seen.add(root)
    return unique_roots


def normalize_path(path_str: str) -> Path:
    expanded = os.path.expandvars(path_str)
    if "$(whoami)" in expanded:
        expanded = expanded.replace("$(whoami)", getpass.getuser())
    path = Path(expanded).expanduser().resolve()
    return path


def set_runtime_allowed_roots(paths: list[Path]) -> contextvars.Token:
    return _RUNTIME_ALLOWED_ROOTS.set(paths)


def reset_runtime_allowed_roots(token: contextvars.Token) -> None:
    _RUNTIME_ALLOWED_ROOTS.reset(token)


def is_path_allowed(path: Path) -> bool:
    for root in get_allowed_roots():
        if root in path.parents or path == root:
            return True
    return False


def ensure_path_allowed(path: Path) -> None:
    if not is_path_allowed(path):
        raise ValueError("Path is not allowed")
