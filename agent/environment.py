"""Environment discovery and preflight checks for external tools and dependencies."""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from agent.config import VCPKG_ROOT, safe_workspace_path


@dataclass
class VersionCheck:
    name: str
    executable: str | None
    version: str | None
    status: str
    details: str = ""


PROGRAMS: dict[str, tuple[str, ...]] = {
    "Python": ("python", "--version"),
    "Git": ("git", "--version"),
    "CMake": ("cmake", "--version"),
    "CTest": ("ctest", "--version"),
    "Ninja": ("ninja", "--version"),
    "Node.js": ("node", "--version"),
    "npm": ("npm", "--version"),
    "Go": ("go", "version"),
    ".NET SDK": ("dotnet", "--version"),
    "Rust": ("rustc", "--version"),
    "Cargo": ("cargo", "--version"),
    "Docker": ("docker", "--version"),
    "Ollama": ("ollama", "--version"),
    "vcpkg": ("vcpkg", "version"),
    "MSVC": ("cl", "/Bv"),
}

_VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+){0,3}(?:[-+][0-9A-Za-z.-]+)?)")


def _version_tuple(value: str) -> tuple[int, ...]:
    match = _VERSION_RE.search(value)
    if not match:
        return ()
    return tuple(int(part) for part in re.findall(r"\d+", match.group(1))[:4])


def _run_version(executable: str, args: Sequence[str], timeout: int = 12) -> tuple[str | None, str]:
    path = shutil.which(executable)
    if not path:
        return None, f"{executable} не найден в PATH"

    try:
        result = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Не удалось получить версию: {exc}"

    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0 and not output:
        return None, f"Команда проверки завершилась с кодом {result.returncode}"
    return output[:1200] or None, ""


def _installed_sfml_version() -> str | None:
    candidates = [
        VCPKG_ROOT / "installed" / "x64-windows" / "share" / "sfml" / "SFMLConfigVersion.cmake",
        VCPKG_ROOT / "installed" / "x64-windows" / "share" / "SFML" / "SFMLConfigVersion.cmake",
    ]
    for file_path in candidates:
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = re.search(r"PACKAGE_VERSION\s+\"([0-9]+(?:\.[0-9]+){1,3})\"", content)
        if match:
            return match.group(1)

    status_file = VCPKG_ROOT / "installed" / "vcpkg" / "status"
    if status_file.is_file():
        try:
            content = status_file.read_text(encoding="utf-8", errors="replace")
            match = re.search(
                r"(?ms)^Package:\s*sfml(?:\n(?:(?!\nPackage:).)*)?^Version:\s*([^\r\n]+)",
                content,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()
        except OSError:
            pass
    return None


def _project_requirements(project: Path) -> list[str]:
    requirements: list[str] = []
    cmake_file = project / "CMakeLists.txt"
    if cmake_file.is_file():
        text = cmake_file.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(
            r"find_package\s*\(\s*([A-Za-z0-9_+-]+)\s*(?:(\d+(?:\.\d+){0,3}))?",
            text,
            re.IGNORECASE,
        ):
            name, version = match.groups()
            requirements.append(f"CMake package {name}" + (f" >= {version}" if version else ""))

    manifest = project / "vcpkg.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for dependency in data.get("dependencies", []):
                name = dependency if isinstance(dependency, str) else dependency.get("name", "")
                if name:
                    requirements.append(f"vcpkg: {name}")
        except (OSError, json.JSONDecodeError):
            requirements.append("vcpkg.json (не удалось разобрать)")

    requirements_file = project / "requirements.txt"
    if requirements_file.is_file():
        for line in requirements_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                requirements.append(f"Python: {line}")

    package_file = project / "package.json"
    if package_file.is_file():
        try:
            data = json.loads(package_file.read_text(encoding="utf-8"))
            for name, version in {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }.items():
                requirements.append(f"npm: {name}@{version}")
        except (OSError, json.JSONDecodeError):
            requirements.append("package.json (не удалось разобрать)")
    return requirements


def _check_programs(names: Sequence[str] | None = None) -> list[VersionCheck]:
    selected = set(names or PROGRAMS)
    results: list[VersionCheck] = []
    for name, (executable, *args) in PROGRAMS.items():
        if name not in selected:
            continue
        path = shutil.which(executable)
        if not path:
            results.append(VersionCheck(name, None, None, "NOT FOUND", "Нет в PATH"))
            continue
        output, error = _run_version(executable, args)
        if error:
            results.append(VersionCheck(name, path, None, "ERROR", error))
            continue
        version_match = _VERSION_RE.search(output or "")
        version = version_match.group(1) if version_match else (output or "").splitlines()[0][:100]
        results.append(VersionCheck(name, path, version, "OK", (output or "").splitlines()[0][:180]))
    return results


def _python_package_versions(project: Path | None) -> list[VersionCheck]:
    checks: list[VersionCheck] = []
    if project is None:
        return checks
    requirements = project / "requirements.txt"
    if not requirements.is_file():
        return checks

    for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", line)
        if not match:
            continue
        package, constraint = match.groups()
        try:
            installed = importlib.metadata.version(package)
            status = "OK"
            details = f"Требование: {constraint or 'любая версия'}"
            if constraint:
                try:
                    from packaging.requirements import Requirement
                    requirement = Requirement(line)
                    if requirement.specifier and installed not in requirement.specifier:
                        status = "VERSION MISMATCH"
                        details = f"Установлена {installed}; требуется {requirement.specifier}"
                except (ImportError, ValueError):
                    details += " (автоматическое сравнение ограничения недоступно)"
        except importlib.metadata.PackageNotFoundError:
            installed, status, details = None, "NOT INSTALLED", "Пакет отсутствует в текущем Python"
        checks.append(VersionCheck(f"Python package {package}", sys.executable, installed, status, details))
    return checks


def _npm_package_versions(project: Path | None) -> list[VersionCheck]:
    checks: list[VersionCheck] = []
    if project is None:
        return checks
    manifest = project / "package.json"
    if not manifest.is_file():
        return checks
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [VersionCheck("npm dependencies", None, None, "ERROR", "package.json не читается")]

    for name, required in {
        **data.get("dependencies", {}),
        **data.get("devDependencies", {}),
    }.items():
        package_file = project / "node_modules" / name / "package.json"
        try:
            installed = json.loads(package_file.read_text(encoding="utf-8")).get("version")
            status = "OK"
            details = f"Требуется: {required}"
        except (OSError, json.JSONDecodeError):
            installed, status, details = None, "NOT INSTALLED", f"Требуется: {required}"
        checks.append(VersionCheck(f"npm package {name}", str(package_file), installed, status, details))
    return checks


def _vcpkg_package_versions(project: Path | None) -> list[VersionCheck]:
    checks: list[VersionCheck] = []
    if project is None:
        return checks
    manifest = project / "vcpkg.json"
    if not manifest.is_file():
        return checks
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [VersionCheck("vcpkg dependencies", None, None, "ERROR", "vcpkg.json не читается")]

    vcpkg = VCPKG_ROOT / ("vcpkg.exe" if os.name == "nt" else "vcpkg")
    if not vcpkg.is_file():
        return [VersionCheck("vcpkg dependencies", str(vcpkg), None, "UNKNOWN", "vcpkg executable не найден")]
    try:
        result = subprocess.run(
            [str(vcpkg), "list"], cwd=str(project), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, shell=False, check=False,
        )
        installed_lines = result.stdout.splitlines() if result.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        installed_lines = []
    installed = {}
    for line in installed_lines:
        match = re.match(r"([A-Za-z0-9_.+-]+):([A-Za-z0-9_-]+)s+([^s]+)", line)
        if match:
            installed[match.group(1).lower()] = match.group(3)
    for dependency in data.get("dependencies", []):
        name = dependency if isinstance(dependency, str) else dependency.get("name", "")
        if not name:
            continue
        version = installed.get(name.lower())
        checks.append(VersionCheck(
            f"vcpkg package {name}", str(vcpkg), version,
            "OK" if version else "NOT INSTALLED",
            "Найден в установленном triplet" if version else "Пакет не найден в выводе vcpkg list",
        ))
    return checks


def check_environment_report(project_path: str = ".") -> str:
    """Return detected versions of development tools and project dependencies."""
    project: Path | None = None
    try:
        candidate = safe_workspace_path(project_path)
        if candidate.is_dir():
            project = candidate
    except (ValueError, OSError):
        project = None

    checks = _check_programs()
    checks.extend(_python_package_versions(project))
    checks.extend(_npm_package_versions(project))
    checks.extend(_vcpkg_package_versions(project))
    sfml = _installed_sfml_version()
    if sfml:
        checks.append(VersionCheck("SFML (vcpkg x64-windows)", str(VCPKG_ROOT), sfml, "OK"))
    elif project and (project / "CMakeLists.txt").is_file():
        cmake_text = (project / "CMakeLists.txt").read_text(encoding="utf-8", errors="replace")
        if re.search(r"find_package\s*\(\s*SFML", cmake_text, re.IGNORECASE):
            checks.append(VersionCheck(
                "SFML", None, None, "UNKNOWN",
                "Версия не найдена в стандартном vcpkg triplet; фактический поиск выполнит CMake",
            ))

    lines = ["ПРОВЕРКА ОКРУЖЕНИЯ", f"Python runtime: {sys.version.split()[0]}",
             f"Платформа: {sys.platform}", ""]
    for item in checks:
        version = item.version or "—"
        lines.append(f"[{item.status}] {item.name}: {version}")
        if item.details:
            lines.append(f"    {item.details}")
        if item.executable:
            lines.append(f"    Путь: {item.executable}")

    if project:
        requirements = _project_requirements(project)
        lines.extend(["", f"ТРЕБОВАНИЯ ПРОЕКТА: {project}"])
        lines.extend(f"- {item}" for item in requirements) if requirements else lines.append("- Явные требования не обнаружены")
    else:
        lines.extend(["", f"Проект не найден или недоступен: {project_path}"])

    lines.extend([
        "",
        "Примечание: наличие программы и её версия проверяются отдельно от совместимости.",
        "Совместимость CMake-пакетов и C++ ABI окончательно подтверждается успешной конфигурацией/сборкой проекта.",
    ])
    return "\n".join(lines)


def preflight_program(executable: str) -> str | None:
    """Check that a command exists and can report its version before execution."""
    key = Path(executable).name.lower()
    aliases = {
        "python.exe": "Python", "python": "Python", "py.exe": "Python", "py": "Python",
        "git.exe": "Git", "git": "Git", "cmake.exe": "CMake", "cmake": "CMake",
        "ctest.exe": "CTest", "ctest": "CTest", "ninja.exe": "Ninja", "ninja": "Ninja",
        "node.exe": "Node.js", "node": "Node.js", "npm.cmd": "npm", "npm": "npm",
        "go.exe": "Go", "go": "Go", "dotnet.exe": ".NET SDK", "dotnet": ".NET SDK",
        "rustc.exe": "Rust", "rustc": "Rust", "cargo.exe": "Cargo", "cargo": "Cargo",
        "docker.exe": "Docker", "docker": "Docker", "ollama.exe": "Ollama", "ollama": "Ollama",
        "vcpkg.exe": "vcpkg", "vcpkg": "vcpkg", "cl.exe": "MSVC", "cl": "MSVC",
    }
    name = aliases.get(key)
    if not name:
        return None
    executable_name, *args = PROGRAMS[name]
    output, error = _run_version(executable_name, args)
    if error:
        return f"PRE-FLIGHT FAILED: {name}: {error}. Команда не запущена."
    match = _VERSION_RE.search(output or "")
    version = match.group(1) if match else (output or "").splitlines()[0]
    return f"PRE-FLIGHT OK: {name} {version}"


def preflight_cpp_project(project: Path, stage: str) -> str | None:
    """Validate the toolchain before CMake configure/build/test stages."""
    cmake_path = shutil.which("cmake")
    if not cmake_path:
        return "PRE-FLIGHT FAILED: CMake не найден в PATH. Этап остановлен."

    output, error = _run_version("cmake", ("--version",))
    if error:
        return f"PRE-FLIGHT FAILED: не удалось определить версию CMake: {error}"

    if os.name == "nt" and not shutil.which("cl.exe"):
        vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        installed = False
        if vswhere.is_file():
            try:
                probe = subprocess.run(
                    [str(vswhere), "-latest", "-products", "*", "-requires",
                     "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=20, shell=False, check=False,
                )
                installed = probe.returncode == 0 and bool(probe.stdout.strip())
            except (OSError, subprocess.TimeoutExpired):
                installed = False
        if not installed:
            return (
                "PRE-FLIGHT FAILED: MSVC x64 не найден (нет cl.exe и установленного компонента "
                "Visual Studio C++ Build Tools). Этап " + stage + " остановлен."
            )

    cmake_file = project / "CMakeLists.txt"
    if not cmake_file.is_file():
        return "PRE-FLIGHT FAILED: CMakeLists.txt не найден."

    text = cmake_file.read_text(encoding="utf-8", errors="replace")
    sfml_match = re.search(
        r"find_package\s*\(\s*SFML\s*(\d+(?:\.\d+){0,3})?",
        text,
        re.IGNORECASE,
    )
    sfml_installed = _installed_sfml_version()
    if sfml_match and sfml_match.group(1) and sfml_installed:
        required = _version_tuple(sfml_match.group(1))
        installed = _version_tuple(sfml_installed)
        if required and installed and tuple((list(installed) + [0] * 4)[:4]) < tuple((list(required) + [0] * 4)[:4]):
            return (
                f"PRE-FLIGHT FAILED: проект требует SFML >= {sfml_match.group(1)}, "
                f"а в vcpkg обнаружена SFML {sfml_installed}. Этап {stage} остановлен."
            )

    cmake_version = _VERSION_RE.search(output or "")
    compiler = shutil.which("cl.exe") or shutil.which("c++") or shutil.which("g++")
    details = f"CMake {cmake_version.group(1) if cmake_version else 'version detected'}"
    if compiler:
        details += f"; compiler: {compiler}"
    if sfml_match:
        details += (
            f"; SFML requirement: {sfml_match.group(1) or 'unspecified'}"
            + (f", installed: {sfml_installed}" if sfml_installed else ", resolution delegated to CMake")
        )
    return f"PRE-FLIGHT OK ({stage}): {details}"
