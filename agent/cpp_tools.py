"""C++20/CMake/vcpkg/SFML tools for AI Coder."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from langchain_core.tools import tool

from agent.config import VCPKG_ROOT, VCPKG_TOOLCHAIN, safe_workspace_path
from agent.environment import check_environment_report, find_program_path, preflight_cpp_project, preflight_program, _visual_studio_installation


def _confirm(label: str) -> bool:
    if os.environ.get("AI_CODER_AUTO_APPROVE", "false").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return False
    print("\n" + "=" * 64 + "\nТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ\n" + label + "\n" + "=" * 64)
    return input("Разрешить выполнение? (y/n): ").strip().lower() == "y"


def _project_dir(relative_path: str) -> Path:
    project = safe_workspace_path(relative_path)
    if not project.is_dir():
        raise ValueError(f"Каталог проекта не найден: {project}")
    return project


def _msvc_environment() -> dict[str, str]:
    """Load a clean Visual Studio x64 compiler environment."""
    env = os.environ.copy()

    if os.name != "nt":
        return env

    expected_cl = find_program_path("MSVC")

    if not expected_cl:
        raise RuntimeError(
            "Не удалось обнаружить MSVC x64 через Visual Studio."
        )

    expected_cl = str(Path(expected_cl).resolve())
    expected_norm = os.path.normcase(os.path.abspath(expected_cl))

    current_cl = shutil.which("cl.exe", path=env.get("PATH", ""))

    # Reuse the environment only when the exact x64 compiler is already
    # active and the compiler include/library paths are available.
    if (
        current_cl
        and os.path.normcase(os.path.abspath(current_cl)) == expected_norm
        and env.get("INCLUDE")
        and env.get("LIB")
    ):
        return env

    installation = _visual_studio_installation()

    if not installation:
        raise RuntimeError(
            "MSVC не найден. Не удалось определить установку Visual Studio."
        )

    dev_cmd = installation / "Common7" / "Tools" / "VsDevCmd.bat"

    if not dev_cmd.is_file():
        raise RuntimeError(
            f"Не найден VsDevCmd.bat: {dev_cmd}"
        )

    # The command line form is important: cmd.exe must receive the
    # nested quotes around the batch-file path as one command.
    command_line = (
        f'cmd.exe /d /c ""{dev_cmd}" '
        '-arch=amd64 -host_arch=amd64 >nul && set"'
    )

    try:
        result = subprocess.run(
            command_line,
            capture_output=True,
            text=True,
            encoding="mbcs",
            errors="replace",
            timeout=90,
            shell=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            f"Не удалось запустить VsDevCmd.bat: {exc}"
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            "Не удалось загрузить окружение MSVC:\n"
            + result.stderr[-4000:]
            + "\n"
            + result.stdout[-2000:]
        )

    loaded = env.copy()

    # Windows environment variable names are case-insensitive.
    # A normal Python dict is case-sensitive, so merge names explicitly.
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        if not key or key.startswith("="):
            continue

        existing_key = next(
            (
                existing
                for existing in loaded
                if existing.casefold() == key.casefold()
            ),
            None,
        )

        if existing_key is not None:
            del loaded[existing_key]

        canonical_key = (
            key.upper()
            if key.upper() in {"PATH", "INCLUDE", "LIB", "LIBPATH"}
            else key
        )

        loaded[canonical_key] = value

    # Put the exact Hostx64/x64 compiler directory first in PATH.
    # This avoids selecting an inherited HostX86/x86 compiler.
    compiler_dir = str(Path(expected_cl).parent)
    existing_path = loaded.get("PATH", "")

    ordered_entries = [compiler_dir]
    compiler_dir_norm = os.path.normcase(
        os.path.abspath(compiler_dir)
    )

    for entry in existing_path.split(os.pathsep):
        entry = entry.strip()

        if not entry:
            continue

        entry_norm = os.path.normcase(os.path.abspath(entry))

        if entry_norm != compiler_dir_norm:
            ordered_entries.append(entry)

    loaded["PATH"] = os.pathsep.join(ordered_entries)

    resolved_cl = shutil.which(
        "cl.exe",
        path=loaded["PATH"],
    )

    if not resolved_cl:
        raise RuntimeError(
            "cl.exe не найден после загрузки окружения Visual Studio."
        )

    resolved_norm = os.path.normcase(os.path.abspath(resolved_cl))

    if resolved_norm != expected_norm:
        raise RuntimeError(
            "Выбран неправильный компилятор MSVC.\n"
            f"Ожидался: {expected_cl}\n"
            f"Получен:  {resolved_cl}"
        )

    if not loaded.get("INCLUDE"):
        raise RuntimeError(
            "VsDevCmd не сформировал переменную INCLUDE."
        )

    if not loaded.get("LIB"):
        raise RuntimeError(
            "VsDevCmd не сформировал переменную LIB."
        )

    if loaded.get("VSCMD_ARG_HOST_ARCH", "").lower() != "x64":
        raise RuntimeError(
            "Visual Studio не подтвердила HOST ARCH x64."
        )

    if loaded.get("VSCMD_ARG_TGT_ARCH", "").lower() != "x64":
        raise RuntimeError(
            "Visual Studio не подтвердила TARGET ARCH x64."
        )

    return loaded


def _run(args: Sequence[str], cwd: Path, timeout: int = 900) -> str:
    if not _confirm("Команда: " + subprocess.list2cmdline(list(args))):
        return "Выполнение отменено. Для автономного режима настрой AI_CODER_AUTO_APPROVE=true в .env."
    try:
        result = subprocess.run(
            list(args), cwd=str(cwd), env=_msvc_environment(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, shell=False, check=False
        )
        return (
            f"EXIT CODE: {result.returncode}\n"
            f"STDOUT:\n{result.stdout[-12000:]}\n"
            f"STDERR:\n{result.stderr[-12000:]}"
        )
    except subprocess.TimeoutExpired:
        return f"Превышено время выполнения ({timeout} секунд)."
    except OSError as exc:
        return f"Не удалось запустить команду: {exc}"


@tool
def create_sfml_game_project(project_name: str) -> str:
    """Создаёт новый игровой проект C++20, CMake и SFML 3 в workspace."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", project_name):
        return "Имя проекта: только латинские буквы, цифры, дефис и подчёркивание."
    target = safe_workspace_path(project_name)
    if target.exists():
        return f"Каталог уже существует, файлы не изменены: {target}"
    if not _confirm(f"Создать проект {project_name}: {target}"):
        return "Создание отменено."

    (target / "src").mkdir(parents=True, exist_ok=True)
    cmake = f"""cmake_minimum_required(VERSION 3.24)
project({project_name} LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(SFML 3 CONFIG REQUIRED COMPONENTS Graphics Window System)
add_executable({project_name} src/main.cpp)
target_link_libraries({project_name} PRIVATE SFML::Graphics SFML::Window SFML::System)
"""
    source = r'''#include <SFML/Graphics.hpp>
#include <cmath>
#include <optional>

int main()
{
    sf::RenderWindow window(sf::VideoMode({1280u, 720u}), "SFML 3 - C++20 Game");
    window.setFramerateLimit(144);

    sf::RectangleShape player({48.0f, 48.0f});
    player.setFillColor(sf::Color(80, 190, 255));
    player.setPosition({616.0f, 336.0f});

    sf::Clock clock;
    constexpr float speed = 280.0f;

    while (window.isOpen())
    {
        while (const std::optional event = window.pollEvent())
        {
            if (event->is<sf::Event::Closed>())
                window.close();
        }

        const float dt = clock.restart().asSeconds();
        sf::Vector2f direction{0.0f, 0.0f};
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::W)) direction.y -= 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::S)) direction.y += 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::A)) direction.x -= 1.0f;
        if (sf::Keyboard::isKeyPressed(sf::Keyboard::Key::D)) direction.x += 1.0f;

        const float length = std::sqrt(direction.x * direction.x + direction.y * direction.y);
        if (length > 0.0f)
        {
            direction.x /= length;
            direction.y /= length;
            player.move(direction * speed * dt);
        }

        window.clear(sf::Color(22, 26, 36));
        window.draw(player);
        window.display();
    }
    return 0;
}
'''
    (target / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
    (target / "src" / "main.cpp").write_text(source, encoding="utf-8")
    (target / "README.md").write_text(
        "# " + project_name + "\n\nC++20 + SFML 3 starter. Управление: WASD.\n",
        encoding="utf-8"
    )
    (target / ".gitignore").write_text("build/\n.vs/\n*.user\n", encoding="utf-8")
    return f"Создан проект: {target}. Теперь вызови configure_cpp_project, затем build_cpp_project."


@tool
def configure_cpp_project(project_path: str = ".", build_type: str = "Debug") -> str:
    """Конфигурирует C++ проект через CMake, используя MSVC x64 и vcpkg x64-windows."""
    try:
        project = _project_dir(project_path)
        if not (project / "CMakeLists.txt").is_file():
            return f"CMakeLists.txt не найден: {project}"
        preflight = preflight_cpp_project(project, "CMake configure")
        if preflight and preflight.startswith("PRE-FLIGHT FAILED"):
            return preflight
        if build_type not in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}:
            return "build_type должен быть Debug, Release, RelWithDebInfo или MinSizeRel."
        cmake = find_program_path("CMake")
        if not cmake:
            return "CMake не найден в PATH."
        build = project / "build"
        args = [cmake, "-S", str(project), "-B", str(build),
                f"-DCMAKE_BUILD_TYPE={build_type}",
                "-DCMAKE_CXX_STANDARD=20", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
        if VCPKG_TOOLCHAIN.is_file():
            args += [f"-DCMAKE_TOOLCHAIN_FILE={VCPKG_TOOLCHAIN}",
                     "-DVCPKG_TARGET_TRIPLET=x64-windows"]
        return _run(args, project, 900)
    except Exception as exc:
        return f"Ошибка конфигурации: {exc}"


@tool
def build_cpp_project(project_path: str = ".", build_type: str = "Debug") -> str:
    """Собирает C++ проект через cmake --build."""
    try:
        project = _project_dir(project_path)
        build = project / "build"
        if not (build / "CMakeCache.txt").is_file():
            return "Сначала вызови configure_cpp_project."
        preflight = preflight_cpp_project(project, "C++ build")
        if preflight and preflight.startswith("PRE-FLIGHT FAILED"):
            return preflight
        if build_type not in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}:
            return "Недопустимый build_type."
        cmake = find_program_path("CMake")
        if not cmake:
            return "CMake не найден."
        return _run([cmake, "--build", str(build), "--config", build_type, "--parallel"],
                    project, 1800)
    except Exception as exc:
        return f"Ошибка сборки: {exc}"


@tool
def run_cpp_tests(project_path: str = ".", build_type: str = "Debug") -> str:
    """Запускает CTest с выводом ошибок."""
    try:
        project = _project_dir(project_path)
        build = project / "build"
        if not (build / "CMakeCache.txt").is_file():
            return "Сначала вызови configure_cpp_project."
        preflight = preflight_cpp_project(project, "CTest")
        if preflight and preflight.startswith("PRE-FLIGHT FAILED"):
            return preflight
        ctest_check = preflight_program("ctest")
        if ctest_check and ctest_check.startswith("PRE-FLIGHT FAILED"):
            return ctest_check
        ctest = find_program_path("CTest")
        if not ctest:
            return "CTest не найден."
        return _run([ctest, "--test-dir", str(build), "-C", build_type,
                     "--output-on-failure"], project, 900)
    except Exception as exc:
        return f"Ошибка CTest: {exc}"


@tool
def run_cpp_game(project_path: str = ".", executable: str = "") -> str:
    """Запускает EXE из build каталога проекта."""
    try:
        project = _project_dir(project_path)
        build = (project / "build").resolve()
        if not build.is_dir():
            return "Каталог build не найден."
        if executable:
            candidate = Path(executable)
            if not candidate.is_absolute():
                candidate = project / candidate
            exe = candidate.resolve()
            try:
                exe.relative_to(project)
            except ValueError:
                return "EXE должен находиться внутри проекта."
            if exe.suffix.lower() != ".exe" or not exe.is_file():
                return "Укажи существующий EXE внутри проекта."
        else:
            candidates = [p for p in build.rglob("*.exe") if "CMakeFiles" not in p.parts]
            if len(candidates) != 1:
                return "Найдено EXE: " + (", ".join(str(p.relative_to(project)) for p in candidates)
                                          if candidates else "нет. Сначала собери проект.")
            exe = candidates[0].resolve()
        if not _confirm(f"Запустить игру: {exe}"):
            return "Запуск отменён."
        process = subprocess.Popen([str(exe)], cwd=str(project), env=_msvc_environment(),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   shell=False)
        return f"Игра запущена. PID: {process.pid}\nEXE: {exe}"
    except Exception as exc:
        return f"Ошибка запуска: {exc}"


@tool
def check_environment(project_path: str = ".") -> str:
    """Определяет версии установленных программ, инструментов и зависимостей проекта."""
    try:
        return check_environment_report(project_path)
    except Exception as exc:
        return f"Ошибка диагностики окружения: {exc}"


CPP_TOOLS = [check_environment, create_sfml_game_project, configure_cpp_project,
             build_cpp_project, run_cpp_tests, run_cpp_game]
