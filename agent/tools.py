"""Workspace-safe tools for the AI Coder agent."""

import ipaddress
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain_core.tools import tool

from agent.config import (
    BACKUP_DIR,
    PROJECT_ROOT,
    VCPKG_ROOT,
    WORKSPACE,
    safe_workspace_path,
)


ALLOWED_COMMANDS = {
    "python", "python.exe", "py", "pytest", "pip", "pip.exe",
    "git", "git.exe",
    "node", "npm", "npx",
    "go", "dotnet", "cargo", "rustc",
    "docker", "uv",
    "cmake", "ctest", "ninja", "make", "mingw32-make", "mingw32-make.exe",
    "gcc", "gcc.exe", "g++", "g++.exe", "clang", "clang.exe",
    "clang++", "clang++.exe", "cl", "cl.exe", "msbuild", "msbuild.exe",
    "vcpkg", "vcpkg.exe", "gdb", "gdb.exe", "where", "where.exe",
}

PYTHON_ALLOWED_MODULES = {"pytest", "unittest", "py_compile", "compileall", "pip"}
SHELL_OPERATOR_PATTERN = re.compile(r"[;&|<>\x60\r\n]")
MAX_FILE_SIZE = 500_000
MAX_TOOL_OUTPUT = 12_000


def safe_path(relative_path: str | Path) -> Path:
    """Use the shared path validator for all file operations."""
    return safe_workspace_path(relative_path)


def backup_file(target: Path) -> None:
    if not target.exists() or not target.is_file():
        return

    relative = target.relative_to(WORKSPACE)
    backup = BACKUP_DIR / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)


@tool
def list_files(path: str = ".") -> str:
    """Показывает файлы и каталоги внутри workspace."""
    target = safe_path(path)

    if not target.exists():
        return "Путь не найден."
    if target.is_file():
        return f"[FILE] {target.relative_to(WORKSPACE)}"

    entries = []
    for item in sorted(target.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        kind = "[DIR]" if item.is_dir() else "[FILE]"
        entries.append(f"{kind} {item.relative_to(WORKSPACE)}")
    return "\n".join(entries)[:MAX_TOOL_OUTPUT]


@tool
def search_files(query: str, extension: str = "") -> str:
    """Ищет текст в файлах workspace, пропуская большие и служебные каталоги."""
    if not query:
        return "Поисковый запрос пуст."

    results = []
    skipped = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist"}

    for path in WORKSPACE.rglob("*"):
        if not path.is_file() or any(part in skipped for part in path.parts):
            continue
        if extension and path.suffix.lower() != extension.lower():
            continue

        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
            content = path.read_text(encoding="utf-8-sig")
            for line_number, line in enumerate(content.splitlines(), 1):
                if query.casefold() in line.casefold():
                    results.append(
                        f"{path.relative_to(WORKSPACE)}:{line_number}: {line[:300]}"
                    )
                    if len(results) >= 100:
                        return "\n".join(results)
        except (OSError, UnicodeError):
            continue

    return "\n".join(results) if results else "Совпадений не найдено."


@tool
def read_file(path: str) -> str:
    """Читает текстовый файл из workspace."""
    target = safe_path(path)

    if not target.is_file():
        return "Файл не найден."
    if target.stat().st_size > MAX_FILE_SIZE:
        return "Файл слишком большой. Используй поиск или читай его частями."

    try:
        return target.read_text(encoding="utf-8-sig")
    except UnicodeError:
        return "Не удалось прочитать файл как UTF-8."


@tool
def write_file(path: str, content: str) -> str:
    """Создаёт или перезаписывает файл внутри workspace, сохраняя резервную копию."""
    target = safe_path(path)

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return "Содержимое превышает лимит 500 КБ."

    if target.exists():
        backup_file(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="")
    return f"Сохранён файл: {target.relative_to(WORKSPACE)}"


@tool
def replace_in_file(path: str, old_text: str, new_text: str) -> str:
    """Заменяет ровно одно вхождение текста внутри файла."""
    target = safe_path(path)

    if not target.is_file():
        return "Файл не найден."

    content = target.read_text(encoding="utf-8-sig")
    occurrences = content.count(old_text)
    if occurrences != 1:
        return (
            "Замена отменена: старый фрагмент должен встречаться ровно один раз; "
            f"найдено: {occurrences}."
        )

    backup_file(target)
    updated = content.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8", newline="")
    return f"Фрагмент успешно заменён: {target.relative_to(WORKSPACE)}"


@tool
def check_environment() -> str:
    """Проверяет доступность Python, Git, CMake, компиляторов C/C++ и отладчика."""
    lines = [
        "ДИАГНОСТИКА ОКРУЖЕНИЯ",
        f"Python: {sys.version.split()[0]}",
        f"Python executable: {sys.executable}",
        f"Project root: {PROJECT_ROOT}",
        f"Workspace: {WORKSPACE}",
        f"vcpkg root: {VCPKG_ROOT} ({'found' if VCPKG_ROOT.exists() else 'not found'})",
        "",
        "Инструменты:",
    ]

    candidates = (
        "git", "cmake", "ctest", "ninja", "g++", "gcc", "clang++", "pip", "pytest",
        "cl", "msbuild", "gdb", "vcpkg",
    )

    for name in candidates:
        executable = shutil.which(name)
        if not executable:
            lines.append(f"[NOT FOUND] {name}")
            continue

        if name in {"cl", "msbuild"}:
            version_args = [executable, "/Bv"] if name == "cl" else [executable, "-version"]
        else:
            version_args = [executable, "--version"]

        try:
            result = subprocess.run(
                version_args,
                cwd=str(WORKSPACE),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                shell=False,
            )
            output = (result.stdout or result.stderr).strip().splitlines()
            version = output[0][:180] if output else f"version command exit {result.returncode}"
            lines.append(f"[OK] {name}: {executable} — {version}")
        except (OSError, subprocess.SubprocessError) as exc:
            lines.append(f"[FOUND, VERSION CHECK FAILED] {name}: {executable} — {exc}")

    return "\n".join(lines)


def execute(command: str, working_directory: Path = WORKSPACE) -> str:
    """Run one approved executable in a known project directory without a shell."""
    if not isinstance(command, str) or not command.strip():
        return "Пустая команда."

    working_directory = Path(working_directory).resolve()
    allowed_directories = {WORKSPACE.resolve(), PROJECT_ROOT.resolve()}
    if working_directory not in allowed_directories:
        return "Запуск разрешён только из корня проекта или workspace."

    if SHELL_OPERATOR_PATTERN.search(command):
        return (
            "Команды оболочки и цепочки команд не поддерживаются. "
            "Запускай по одной команде за раз; рабочая папка уже установлена в workspace."
        )

    try:
        parsed_args = shlex.split(command, posix=False)
        args = [
            item[1:-1] if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'" else item
            for item in parsed_args
        ]
    except ValueError as exc:
        return f"Ошибка разбора команды: {exc}"

    if not args:
        return "Пустая команда."

    executable = Path(args[0]).name.lower()
    if executable in {"cd", "cd.exe"}:
        return (
            "Команда cd не нужна и не поддерживается: процессы запускаются "
            f"из рабочей папки {WORKSPACE}. Используй относительные пути от workspace."
        )
    if executable not in ALLOWED_COMMANDS:
        # Разрешаем запуск собранных EXE только внутри workspace.
        if Path(args[0]).suffix.lower() != ".exe":
            return f"Команда {executable} не разрешена."

        try:
            local_executable = safe_path(args[0])
        except ValueError as exc:
            return str(exc)

        if not local_executable.is_file():
            return "Разрешён запуск только существующего EXE внутри workspace."

        if local_executable.suffix.lower() != ".exe":
            return "Разрешён запуск только файлов с расширением .exe."

        # Запускаем по абсолютному проверенному пути.
        args[0] = str(local_executable)

    if executable in {"pip", "pip.exe"}:
        args = [sys.executable, "-m", "pip", *args[1:]]

    elif executable in {"python", "python.exe", "py"}:
        if len(args) < 2:
            return "Укажи Python-скрипт или разрешённый модуль через -m."
        if args[1] == "-m":
            if len(args) < 3 or args[2] not in PYTHON_ALLOWED_MODULES:
                allowed = ", ".join(sorted(PYTHON_ALLOWED_MODULES))
                return f"Разрешены только Python-модули: {allowed}."
        elif args[1].startswith("-"):
            return "Запуск Python с произвольными параметрами запрещён."
        else:
            try:
                script = safe_path(args[1])
            except ValueError as exc:
                return str(exc)
            if not script.is_file():
                return "Python-скрипт должен существовать внутри workspace."
            args[1] = str(script)

        # Always use the same interpreter and virtual environment as the running agent.
        args[0] = sys.executable

    try:
        timeout_seconds = int(os.environ.get("AI_CODER_COMMAND_TIMEOUT", "300"))
        timeout_seconds = max(1, min(timeout_seconds, 1800))
    except ValueError:
        timeout_seconds = 300

    resolved_executable = shutil.which(args[0]) or args[0]
    print("\n" + "=" * 60)
    print("ЗАПРОС НА ВЫПОЛНЕНИЕ КОМАНДЫ")
    print("Рабочая папка:", working_directory)
    print("Исполняемый файл:", resolved_executable)
    print("Команда:", command)
    print("=" * 60)

    answer = input("Разрешить выполнение? (y/n): ").strip().lower()
    if answer not in {"y", "yes", "д", "да"}:
        return "Команда отклонена пользователем."

    started_at = time.perf_counter()
    try:
        result = subprocess.run(
            args,
            cwd=str(working_directory),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
        )
        elapsed = time.perf_counter() - started_at
        stdout = result.stdout[-MAX_TOOL_OUTPUT:]
        stderr = result.stderr[-MAX_TOOL_OUTPUT:]
        return (
            f"COMMAND: {command}\n"
            f"CWD: {working_directory}\n"
            f"ELAPSED: {elapsed:.2f}s\n"
            f"EXIT CODE: {result.returncode}\n"
            f"STDOUT:\n{stdout or '(empty)'}\n"
            f"STDERR:\n{stderr or '(empty)'}"
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started_at
        partial_stdout = exc.stdout or ""
        partial_stderr = exc.stderr or ""
        if isinstance(partial_stdout, bytes):
            partial_stdout = partial_stdout.decode("utf-8", errors="replace")
        if isinstance(partial_stderr, bytes):
            partial_stderr = partial_stderr.decode("utf-8", errors="replace")
        return (
            f"TIMEOUT: команда выполнялась дольше {timeout_seconds} секунд.\n"
            f"ELAPSED: {elapsed:.2f}s\n"
            f"STDOUT:\n{str(partial_stdout)[-MAX_TOOL_OUTPUT:]}\n"
            f"STDERR:\n{str(partial_stderr)[-MAX_TOOL_OUTPUT:]}"
        )
    except OSError as exc:
        return (
            f"ОШИБКА ЗАПУСКА: {exc}\n"
            f"Проверь наличие исполняемого файла и PATH. Команда: {command}"
        )


@tool
def run_command(command: str) -> str:
    """Запускает одну разрешённую команду из workspace после подтверждения пользователя. Shell и cd не используются."""
    return execute(command)


@tool
def run_tests() -> str:
    """Запускает Python-тесты из корня репозитория, а не из workspace."""
    tests_directory = PROJECT_ROOT / "tests"
    if not tests_directory.is_dir():
        return f"Каталог Python-тестов не найден: {tests_directory}"
    return execute("python -m pytest -q tests", working_directory=PROJECT_ROOT)


@tool
def build_cpp_project(build_directory: str = "build", configuration: str = "Debug") -> str:
    """Конфигурирует и собирает CMake-проект внутри workspace с точными кодами возврата."""
    allowed_configurations = {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}
    if configuration not in allowed_configurations:
        return "Недопустимая конфигурация. Разрешены: " + ", ".join(sorted(allowed_configurations))

    try:
        build_path = safe_path(build_directory)
        relative_build_path = build_path.relative_to(WORKSPACE)
    except (ValueError, OSError) as exc:
        return f"Недопустимый каталог сборки: {exc}"

    if not relative_build_path.parts:
        return "Каталог сборки не может совпадать с корнем workspace."
    if not (WORKSPACE / "CMakeLists.txt").is_file():
        return f"CMakeLists.txt не найден в {WORKSPACE}."
    if not shutil.which("cmake"):
        return "CMake не найден в PATH. Запусти start.ps1 с настроенным окружением."

    build_arg = relative_build_path.as_posix()
    commands = [
        ["cmake", "-S", ".", "-B", build_arg],
        ["cmake", "--build", build_arg, "--config", configuration, "--parallel"],
    ]
    print("\n" + "=" * 60)
    print("ПЛАН СБОРКИ CMAKE")
    print("Рабочая папка:", WORKSPACE)
    print("Конфигурация:", configuration)
    print("1.", " ".join(commands[0]))
    print("2.", " ".join(commands[1]))
    print("=" * 60)
    answer = input("Разрешить конфигурацию и сборку? (y/n): ").strip().lower()
    if answer not in {"y", "yes", "д", "да"}:
        return "Сборка отклонена пользователем."

    try:
        timeout_seconds = int(os.environ.get("AI_CODER_COMMAND_TIMEOUT", "300"))
        timeout_seconds = max(1, min(timeout_seconds, 1800))
    except ValueError:
        timeout_seconds = 300

    reports = []
    for args in commands:
        command_text = " ".join(args)
        started_at = time.perf_counter()
        try:
            result = subprocess.run(
                args,
                cwd=str(WORKSPACE),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
            )
            elapsed = time.perf_counter() - started_at
            reports.append(
                f"COMMAND: {command_text}\n"
                f"ELAPSED: {elapsed:.2f}s\n"
                f"EXIT CODE: {result.returncode}\n"
                f"STDOUT:\n{(result.stdout or '')[-MAX_TOOL_OUTPUT:] or '(empty)'}\n"
                f"STDERR:\n{(result.stderr or '')[-MAX_TOOL_OUTPUT:] or '(empty)'}"
            )
            if result.returncode != 0:
                reports.append("Сборка остановлена: предыдущая команда завершилась с ошибкой.")
                break
        except subprocess.TimeoutExpired as exc:
            reports.append(
                f"COMMAND: {command_text}\nTIMEOUT: превышено {timeout_seconds} секунд.\n"
                f"STDOUT: {str(exc.stdout or '')[-MAX_TOOL_OUTPUT:]}\n"
                f"STDERR: {str(exc.stderr or '')[-MAX_TOOL_OUTPUT:]}"
            )
            break
        except OSError as exc:
            reports.append(f"COMMAND: {command_text}\nОШИБКА ЗАПУСКА: {exc}")
            break

    return "\n\n".join(reports)


@tool
def run_cpp_tests(build_directory: str = "build", configuration: str = "Debug") -> str:
    """Запускает только реально сконфигурированные CTest-тесты."""
    allowed_configurations = {"Debug", "Release", "RelWithDebInfo", "MinSizeRel"}
    if configuration not in allowed_configurations:
        return "Недопустимая конфигурация CMake."
    try:
        build_path = safe_path(build_directory)
    except ValueError as exc:
        return f"Недопустимый каталог сборки: {exc}"

    if not (build_path / "CTestTestfile.cmake").is_file():
        return (
            "CTest-тесты не сконфигурированы: CTestTestfile.cmake отсутствует. "
            "Это не означает, что тесты прошли. Проверь enable_testing()/include(CTest) "
            "и add_test() в CMakeLists.txt."
        )

    return execute(
        f'ctest --test-dir "{build_path}" -C {configuration} '
        "--output-on-failure --no-tests=error"
    )


@tool
def run_gui(executable: str, arguments: str = "") -> str:
    """Запускает GUI EXE отдельно от агента и проверяет, остался ли процесс жив после старта."""
    try:
        target = safe_path(executable)
    except ValueError as exc:
        return str(exc)
    if target.suffix.lower() != ".exe" or not target.is_file():
        return "Укажи существующий EXE внутри workspace."

    try:
        parsed_arguments = shlex.split(arguments, posix=False) if arguments.strip() else []
        parsed_arguments = [
            item[1:-1] if len(item) >= 2 and item[0] == item[-1] and item[0] in "\\\"'" else item
            for item in parsed_arguments
        ]
    except ValueError as exc:
        return f"Ошибка разбора аргументов GUI: {exc}"

    print("\n" + "=" * 60)
    print("ЗАПУСК GUI-ПРИЛОЖЕНИЯ")
    print("Исполняемый файл:", target)
    print("Рабочая папка:", WORKSPACE)
    print("=" * 60)
    answer = input("Разрешить запуск GUI-приложения? (y/n): ").strip().lower()
    if answer not in {"y", "yes", "д", "да"}:
        return "Запуск GUI-приложения отклонён пользователем."

    launch_options = {}
    if os.name == "nt":
        launch_options["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        )
    else:
        launch_options["start_new_session"] = True

    try:
        process = subprocess.Popen(
            [str(target), *parsed_arguments],
            cwd=str(WORKSPACE),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            **launch_options,
        )
    except OSError as exc:
        return f"Не удалось запустить GUI-приложение: {exc}"

    try:
        startup_timeout = float(os.environ.get("AI_CODER_GUI_STARTUP_TIMEOUT", "5.0"))
        startup_timeout = max(0.2, min(startup_timeout, 10.0))
    except ValueError:
        startup_timeout = 2.0

    try:
        return_code = process.wait(timeout=startup_timeout)
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            return (
                f"GUI-процесс запущен и остаётся активным после {startup_timeout:.1f} с. "
                f"PID: {process.pid}. Это подтверждает только жизнь процесса, "
                "но не видимость окна и не корректность игрового поведения."
            )
        return_code = process.returncode

    unsigned_code = int(return_code) & 0xFFFFFFFF
    return (
        f"GUI-процесс завершился в пределах контрольных {startup_timeout:.1f} с. "
        f"EXIT CODE: {return_code} (0x{unsigned_code:08X}). "
        "Код 0 сам по себе не подтверждает, что окно успело появиться. "
        "Ненулевой код означает, что запуск нельзя считать успешным."
    )


@tool
def web_search(query: str) -> str:
    """Ищет документацию и техническую информацию в интернете."""
    try:
        results = DDGS().text(query, max_results=6)
        if not results:
            return "Результаты не найдены."

        return "\n\n".join(
            f"TITLE: {item.get('title', '')}\n"
            f"URL: {item.get('href', '')}\n"
            f"DESCRIPTION: {item.get('body', '')}"
            for item in results
        )[:MAX_TOOL_OUTPUT]
    except Exception as exc:
        return f"Ошибка поиска: {exc}"


@tool
def fetch_webpage(url: str) -> str:
    """Загружает публичную веб-страницу и извлекает текст, не переходя по редиректам."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return "Разрешены только HTTP и HTTPS адреса."
        if parsed.username or parsed.password:
            return "URL с учётными данными запрещён."

        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return "Доступ к локальным адресам запрещён."

        response = requests.get(
            url,
            timeout=20,
            allow_redirects=False,
            headers={"User-Agent": "AI-Coder-Pro/2.0"},
        )
        if response.is_redirect:
            return "Перенаправление не выполняется автоматически."
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            return "Страница превышает лимит 2 МБ."

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        return soup.get_text(separator="\n", strip=True)[:MAX_TOOL_OUTPUT]
    except Exception as exc:
        return f"Ошибка загрузки: {exc}"


TOOLS = [
    check_environment,
    list_files,
    search_files,
    read_file,
    write_file,
    replace_in_file,
    run_command,
    run_tests,
    build_cpp_project,
    run_cpp_tests,
    run_gui,
    web_search,
    fetch_webpage,
]
