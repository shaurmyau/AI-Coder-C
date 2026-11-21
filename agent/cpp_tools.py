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
    env = os.environ.copy()
    if os.name != "nt" or shutil.which("cl.exe", path=env.get("PATH")):
        return env

    pf = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = pf / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.is_file():
        raise RuntimeError("MSVC не найден. Запусти агента из Visual Studio Developer PowerShell.")

    found = subprocess.run(
        [str(vswhere), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
    )
    paths = found.stdout.strip().splitlines()
    if found.returncode or not paths:
        raise RuntimeError("Не удалось найти Visual Studio с компонентом MSVC.")

    dev_cmd = Path(paths[0]) / "Common7" / "Tools" / "VsDevCmd.bat"
    command = f'call "{dev_cmd}" -arch=amd64 -host_arch=amd64 >nul && set'
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", command],
        capture_output=True, text=True, encoding="mbcs", errors="replace", timeout=60
    )
    if result.returncode:
        raise RuntimeError("Не удалось загрузить окружение MSVC:\n" + result.stderr[-4000:])
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key:
                env[key] = value
    if not shutil.which("cl.exe", path=env.get("PATH")):
        raise RuntimeError("cl.exe не появился в PATH после загрузки VsDevCmd.")
    return env


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
        if build_type not in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}:
            return "build_type должен быть Debug, Release, RelWithDebInfo или MinSizeRel."
        cmake = shutil.which("cmake")
        if not cmake:
            return "CMake не найден в PATH."
        build = project / "build"
        args = [cmake, "-S", str(project), "-B", str(build),
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
        if build_type not in {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}:
            return "Недопустимый build_type."
        cmake = shutil.which("cmake")
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
        ctest = shutil.which("ctest")
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


CPP_TOOLS = [create_sfml_game_project, configure_cpp_project, build_cpp_project,
             run_cpp_tests, run_cpp_game]
