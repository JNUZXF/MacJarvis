import os
from pathlib import Path


BASE_ALLOWED_ROOTS = [
    Path.home(),
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
]


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
    path = Path(path_str).expanduser().resolve()
    return path


def is_path_allowed(path: Path) -> bool:
    for root in get_allowed_roots():
        if root in path.parents or path == root:
            return True
    return False


def ensure_path_allowed(path: Path) -> None:
    if not is_path_allowed(path):
        raise ValueError("Path is not allowed")
