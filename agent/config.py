"""Shared paths and explicitly allow-listed project roots for AI Coder."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(
    os.environ.get("AI_CODER_ROOT", Path(__file__).resolve().parents[1])
).expanduser().resolve()

load_dotenv(PROJECT_ROOT / ".env", override=False)


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if not raw:
        return default.resolve()
    value = Path(raw).expanduser()
    if not value.is_absolute():
        value = PROJECT_ROOT / value
    return value.resolve()


WORKSPACE = _path_from_env("AI_CODER_WORKSPACE", PROJECT_ROOT / "workspace")
LOG_DIR = _path_from_env("AI_CODER_LOG_DIR", PROJECT_ROOT / "logs")
BACKUP_DIR = LOG_DIR / "backups"
VCPKG_ROOT = _path_from_env("VCPKG_ROOT", PROJECT_ROOT / "tools" / "vcpkg")
VCPKG_TOOLCHAIN = VCPKG_ROOT / "scripts" / "buildsystems" / "vcpkg.cmake"

# Additional roots are explicitly granted by the user in .env.
# Separate Windows paths with semicolons, e.g. D:/Games;D:/Projects/GameA.
_raw_allowed_roots = os.environ.get("AI_CODER_ALLOWED_ROOTS", "")
_configured_roots: list[Path] = [WORKSPACE]
for _item in _raw_allowed_roots.split(";"):
    _item = _item.strip().strip('"').strip("'")
    if _item:
        _root = Path(_item).expanduser()
        if not _root.is_absolute():
            _root = PROJECT_ROOT / _root
        _configured_roots.append(_root.resolve())

# Deduplicate paths while preserving order.
_seen_roots: set[str] = set()
ALLOWED_ROOTS: tuple[Path, ...] = tuple(
    root for root in _configured_roots
    if not (os.path.normcase(str(root)) in _seen_roots
            or _seen_roots.add(os.path.normcase(str(root))))
)

os.environ.setdefault("VCPKG_ROOT", str(VCPKG_ROOT))


def ensure_directories() -> None:
    """Create directories used by the agent."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def allowed_root_for(path: str | Path) -> Path:
    """Return the configured root containing path or raise PermissionError."""
    resolved = Path(path).expanduser().resolve()
    # Prefer the most specific allowed root when roots overlap.
    for root in sorted(ALLOWED_ROOTS, key=lambda item: len(str(item)), reverse=True):
        try:
            resolved.relative_to(root)
            return root
        except ValueError:
            continue
    roots = ", ".join(str(root) for root in ALLOWED_ROOTS)
    raise ValueError(
        f"Доступ к пути запрещён: {resolved}. Разрешённые корни: {roots}"
    )


def safe_workspace_path(relative_path: str | Path) -> Path:
    """Resolve a workspace-relative or allow-listed absolute project path."""
    raw = str(relative_path).strip().strip('"').strip("'")
    if not raw:
        raise ValueError("Путь к проекту не может быть пустым.")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        # Accept both "rougeLikeGame" (relative to WORKSPACE) and
        # "workspace/rougeLikeGame" (relative to PROJECT_ROOT).
        parts = candidate.parts
        if parts and os.path.normcase(parts[0]) == os.path.normcase(WORKSPACE.name):
            candidate = PROJECT_ROOT / candidate
        else:
            candidate = WORKSPACE / candidate

    resolved = candidate.resolve()
    allowed_root_for(resolved)
    return resolved


def display_path(path: str | Path) -> str:
    """Return a readable path relative to its authorized root."""
    resolved = Path(path).resolve()
    root = allowed_root_for(resolved)
    relative = resolved.relative_to(root)
    if root == WORKSPACE:
        return str(relative) or "."
    return f"[{root}]/{relative}"


ensure_directories()
