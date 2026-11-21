"""Centralized project paths and workspace boundary validation."""

import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(DEFAULT_PROJECT_ROOT / ".env", override=False)

PROJECT_ROOT = Path(
    os.environ.get("AI_CODER_ROOT", str(DEFAULT_PROJECT_ROOT))
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
BACKUP_DIR = _path_from_env("AI_CODER_BACKUP_DIR", LOG_DIR / "backups")
VCPKG_ROOT = _path_from_env("VCPKG_ROOT", PROJECT_ROOT / "tools" / "vcpkg")
VCPKG_TOOLCHAIN = VCPKG_ROOT / "scripts" / "buildsystems" / "vcpkg.cmake"

os.environ.setdefault("VCPKG_ROOT", str(VCPKG_ROOT))


def ensure_directories() -> None:
    """Create directories managed by the agent."""
    for directory in (WORKSPACE, LOG_DIR, BACKUP_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def safe_workspace_path(relative_path: str | Path) -> Path:
    """Resolve a path and reject any access outside WORKSPACE."""
    raw = str(relative_path).strip().strip('"').strip("'")
    if not raw:
        raise ValueError("Путь не может быть пустым.")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        parts = candidate.parts
        if parts and os.path.normcase(parts[0]) == os.path.normcase(WORKSPACE.name):
            candidate = PROJECT_ROOT / candidate
        else:
            candidate = WORKSPACE / candidate

    resolved = candidate.resolve()
    try:
        resolved.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError(
            f"Доступ запрещён: путь находится вне workspace: {resolved}"
        ) from exc

    return resolved


ensure_directories()
