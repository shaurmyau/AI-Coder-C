import os
import re
import shlex
import socket
import ipaddress
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

ROOT = Path(r"D:\AI-Coder-C++").resolve()
WORKSPACE = (ROOT / "workspace").resolve()
BACKUPS = (ROOT / "logs" / "backups").resolve()

ALLOWED_COMMANDS = {
    "python", "python.exe", "py", "pytest", "pip", "pip.exe",
    "git", "git.exe", "node", "npm", "npx",
    "go", "dotnet", "cargo", "rustc",
    "docker", "uv", "cmake", "gcc", "clang", "g++", "cd", "cl", "g++.exe"
}

BLOCKED_FLAGS = {
    "-c", "/c", "/k", "-encodedcommand",
    "-command", "-executionpolicy"
}

def safe_path(relative_path):
    target = (WORKSPACE / relative_path).resolve()

    # if not target.is_relative_to(WORKSPACE):
    #     raise ValueError("Доступ за пределами workspace запрещён")

    return target


def backup_file(target):
    if not target.exists() or not target.is_file():
        return

    relative = target.relative_to(WORKSPACE)
    backup = BACKUPS / relative

    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)


@tool
def list_files(path: str = ".") -> str:
    """Показывает содержимое каталога проекта."""
    target = safe_path(path)

    if not target.exists():
        return "Каталог не найден"

    return "\n".join(
        f"{'[DIR]' if p.is_dir() else '[FILE]'} {p.relative_to(WORKSPACE)}"
        for p in sorted(target.iterdir())
    )[:15000]


@tool
def search_files(query: str, extension: str = "") -> str:
    """Ищет текст внутри файлов проекта."""
    results = []
    count = 0

    for path in WORKSPACE.rglob("*"):
        if not path.is_file():
            continue

        if any(x in path.parts for x in (
            ".git", "node_modules", ".venv", "__pycache__"
        )):
            continue

        if extension and path.suffix.lower() != extension.lower():
            continue

        try:
            if path.stat().st_size > 500_000:
                continue

            content = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(content.splitlines(), 1):
                if query.lower() in line.lower():
                    results.append(
                        f"{path.relative_to(WORKSPACE)}:{line_number}: {line[:300]}"
                    )
                    count += 1

                    if count >= 100:
                        return "\n".join(results)

        except (UnicodeError, OSError):
            continue

    return "\n".join(results) if results else "Совпадений не найдено"


@tool
def read_file(path: str) -> str:
    """Читает текстовый файл проекта."""
    target = safe_path(path)

    if not target.is_file():
        return "Файл не найден"

    if target.stat().st_size > 500_000:
        return "Файл слишком большой. Используй поиск или раздели работу."

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeError:
        return "Не удалось прочитать файл как UTF-8"


@tool
def write_file(path: str, content: str) -> str:
    """Создаёт файл или сохраняет изменения с резервной копией."""
    target = safe_path(path)

    if len(content) > 500_000:
        return "Содержимое превышает лимит 500 КБ"

    if target.exists():
        backup_file(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return f"Сохранён файл: {target.relative_to(WORKSPACE)}"


@tool
def replace_in_file(path: str, old_text: str, new_text: str) -> str:
    """Точечно заменяет уникальный фрагмент текста в файле."""
    target = safe_path(path)

    if not target.is_file():
        return "Файл не найден"

    content = target.read_text(encoding="utf-8")

    if content.count(old_text) != 1:
        return "Замена отменена: старый фрагмент должен встречаться ровно один раз"

    backup_file(target)

    content = content.replace(old_text, new_text, 1)
    target.write_text(content, encoding="utf-8")

    return "Фрагмент успешно заменён"


def execute(command):
    # if re.search(r"[;&|<>`\r\n]", command):
    #     return "Запрещены операторы оболочки и цепочки команд"

    try:
        args = shlex.split(command, posix=False)
        args = [a.strip('"') for a in args]
    except ValueError as exc:
        return f"Ошибка разбора: {exc}"

    if not args:
        return "Пустая команда"

    executable = Path(args[0]).name.lower()

    if executable not in ALLOWED_COMMANDS:
        return f"Команда {executable} не разрешена"

    if any(a.lower() in BLOCKED_FLAGS for a in args[1:]):
        return "Опасный параметр команды заблокирован"

    if executable in {"python", "python.exe", "py"}:
        if len(args) > 1 and args[1] == "-m":
            if len(args) < 3 or args[2] != "pytest":
                return "Python разрешён с -m только для запуска pytest"

        elif len(args) > 1 and args[1].startswith("-"):
            return "Запуск Python с произвольными параметрами запрещён"

        elif len(args) > 1:
            try:
                script = safe_path(args[1])
                if not script.is_file():
                    return "Python-скрипт должен существовать в workspace"
                args[1] = str(script)
            except ValueError as exc:
                return str(exc)

    print("\n" + "=" * 55)
    print("ЗАПРОС НА ВЫПОЛНЕНИЕ КОМАНДЫ")
    print("Рабочая папка:", WORKSPACE)
    print("Команда:", command)
    print("=" * 55)

    answer = input("Разрешить выполнение? (y/n): ").strip().lower()

    if answer != "y":
        return "Команда отклонена пользователем"

    try:
        result = subprocess.run(
            args,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            shell=False
        )

        return (
            f"EXIT CODE: {result.returncode}\n"
            f"STDOUT:\n{result.stdout[-10000:]}\n"
            f"STDERR:\n{result.stderr[-10000:]}"
        )

    except subprocess.TimeoutExpired:
        return "Превышено время выполнения: 300 секунд"
    except Exception as exc:
        return f"Ошибка запуска: {exc}"


@tool
def run_command(command: str) -> str:
    """Запускает разрешённую команду разработки с подтверждением."""
    return execute(command)


@tool
def run_tests() -> str:
    """Запускает pytest в рабочем проекте с подтверждением."""
    return execute("python -m pytest -q")


@tool
def web_search(query: str) -> str:
    """Ищет документацию и техническую информацию в интернете."""
    try:
        results = DDGS().text(query, max_results=6)

        if not results:
            return "Результаты не найдены"

        return "\n\n".join(
            f"TITLE: {r.get('title', '')}\n"
            f"URL: {r.get('href', '')}\n"
            f"DESCRIPTION: {r.get('body', '')}"
            for r in results
        )[:15000]

    except Exception as exc:
        return f"Ошибка поиска: {exc}"


@tool
def fetch_webpage(url: str) -> str:
    """Загружает публичную веб-страницу и извлекает текст."""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return "Разрешены только HTTP и HTTPS адреса"

        if parsed.username or parsed.password:
            return "URL с учётными данными запрещён"

        addresses = socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM
        )

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return "Доступ к локальным адресам запрещён"

        response = requests.get(
            url,
            timeout=20,
            allow_redirects=False,
            headers={"User-Agent": "AI-Coder-Pro/2.0"}
        )

        if response.is_redirect:
            return "Перенаправление не выполняется автоматически"

        response.raise_for_status()

        if len(response.content) > 2_000_000:
            return "Страница превышает лимит 2 МБ"

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup([
            "script", "style", "nav", "footer", "header"
        ]):
            element.decompose()

        return soup.get_text(separator="\n", strip=True)[:15000]

    except Exception as exc:
        return f"Ошибка загрузки: {exc}"


TOOLS = [
    list_files,
    search_files,
    read_file,
    write_file,
    replace_in_file,
    run_command,
    run_tests,
    web_search,
    fetch_webpage
]
