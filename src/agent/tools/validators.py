from pathlib import Path


ALLOWED_ROOTS = [
    Path.home(),
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
]


def normalize_path(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    return path


def is_path_allowed(path: Path) -> bool:
    for root in ALLOWED_ROOTS:
        if root in path.parents or path == root:
            return True
    return False


def ensure_path_allowed(path: Path) -> None:
    if not is_path_allowed(path):
        raise ValueError("Path is not allowed")
