"""Shared paths and configuration for AI Coder."""

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

os.environ.setdefault("VCPKG_ROOT", str(VCPKG_ROOT))


def ensure_directories() -> None:
    """Create directories used by the agent."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def safe_workspace_path(relative_path: str | Path) -> Path:
    """Resolve a path and reject traversal outside the agent workspace."""
    candidate = Path(relative_path).expanduser()
    if not candidate.is_absolute():
        candidate = WORKSPACE / candidate

    resolved = candidate.resolve()
    try:
        resolved.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError("Доступ за пределами workspace запрещён.") from exc

    return resolved


ensure_directories()
