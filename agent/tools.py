import os
import re
import shlex
import socket
import ipaddress
import hashlib
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from dotenv import load_dotenv
from langchain_core.tools import tool

from agent.config import (BACKUP_DIR, PROJECT_ROOT, WORKSPACE, ALLOWED_ROOTS, allowed_root_for, display_path, safe_workspace_path)
from agent.cpp_tools import CPP_TOOLS
from agent.environment import preflight_program, preflight_python_module

load_dotenv()

ROOT = PROJECT_ROOT
BACKUPS = BACKUP_DIR


ALLOWED_COMMANDS = {
    "python", "python.exe", "py", "pytest", "pip", "pip.exe",
    "git", "git.exe", "node", "npm", "npx",
    "go", "dotnet", "cargo", "rustc",
    "docker", "uv", "cmake", "gcc", "clang", "cl", "cl.exe", "ctest", "vcpkg", "vcpkg.exe", "msbuild", "ninja"
}

BLOCKED_FLAGS = {
    "-c", "/c", "/k", "-encodedcommand",
    "-command", "-executionpolicy"
}

def safe_path(relative_path):
    """Resolve a workspace-relative path or an explicitly allow-listed absolute path."""
    return safe_workspace_path(relative_path)


def backup_file(target):
    if not target.exists() or not target.is_file():
        return

    root = allowed_root_for(target)
    relative = target.relative_to(root)
    if root == WORKSPACE:
        backup = BACKUPS / "workspace" / relative
    else:
        root_id = hashlib.sha256(str(root).casefold().encode("utf-8")).hexdigest()[:12]
        backup = BACKUPS / "external" / root_id / relative

    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)


def _display_path(path):
    return display_path(path)


@tool
def list_files(path: str = ".") -> str:
    """РџРѕРєР°Р·С‹РІР°РµС‚ СЃРѕРґРµСЂР¶РёРјРѕРµ РєР°С‚Р°Р»РѕРіР° РїСЂРѕРµРєС‚Р°."""
    target = safe_path(path)

    if not target.exists():
        return "РљР°С‚Р°Р»РѕРі РЅРµ РЅР°Р№РґРµРЅ"

    return "\n".join(
        f"{'[DIR]' if p.is_dir() else '[FILE]'} {_display_path(p)}"
        for p in sorted(target.iterdir())
    )[:15000]


@tool
def search_files(query: str, extension: str = "", path: str = ".") -> str:
    """Ищет текст внутри файлов указанного каталога; path может быть разрешённой внешней папкой."""
    try:
        base = safe_path(path)
    except ValueError as exc:
        return str(exc)

    if not base.exists():
        return f"Каталог не найден: {_display_path(base)}"

    candidates = [base] if base.is_file() else base.rglob("*")
    results = []
    count = 0

    for file_path in candidates:
        if not file_path.is_file():
            continue
        if any(part.lower() in {
            ".git", "node_modules", ".venv", "venv", "__pycache__", "build"
        } for part in file_path.parts):
            continue
        if extension and file_path.suffix.lower() != extension.lower():
            continue
        try:
            if file_path.stat().st_size > 500_000:
                continue
            content = file_path.read_text(encoding="utf-8")
            for line_number, line in enumerate(content.splitlines(), 1):
                if query.lower() in line.lower():
                    results.append(
                        f"{_display_path(file_path)}:{line_number}: {line[:300]}"
                    )
                    count += 1
                    if count >= 100:
                        return "\n".join(results)
        except (UnicodeError, OSError):
            continue

    return "\n".join(results) if results else "Совпадений не найдено"


@tool
def read_file(path: str) -> str:
    """Р§РёС‚Р°РµС‚ С‚РµРєСЃС‚РѕРІС‹Р№ С„Р°Р№Р» РїСЂРѕРµРєС‚Р°."""
    target = safe_path(path)

    if not target.is_file():
        return "Р¤Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ"

    if target.stat().st_size > 500_000:
        return "Р¤Р°Р№Р» СЃР»РёС€РєРѕРј Р±РѕР»СЊС€РѕР№. РСЃРїРѕР»СЊР·СѓР№ РїРѕРёСЃРє РёР»Рё СЂР°Р·РґРµР»Рё СЂР°Р±РѕС‚Сѓ."

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeError:
        return "РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ С„Р°Р№Р» РєР°Рє UTF-8"


@tool
def write_file(path: str, content: str) -> str:
    """РЎРѕР·РґР°С‘С‚ С„Р°Р№Р» РёР»Рё СЃРѕС…СЂР°РЅСЏРµС‚ РёР·РјРµРЅРµРЅРёСЏ СЃ СЂРµР·РµСЂРІРЅРѕР№ РєРѕРїРёРµР№."""
    target = safe_path(path)

    if len(content) > 500_000:
        return "РЎРѕРґРµСЂР¶РёРјРѕРµ РїСЂРµРІС‹С€Р°РµС‚ Р»РёРјРёС‚ 500 РљР‘"

    if target.exists():
        backup_file(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    return f"РЎРѕС…СЂР°РЅС‘РЅ С„Р°Р№Р»: {_display_path(target)}"


@tool
def replace_in_file(path: str, old_text: str, new_text: str) -> str:
    """РўРѕС‡РµС‡РЅРѕ Р·Р°РјРµРЅСЏРµС‚ СѓРЅРёРєР°Р»СЊРЅС‹Р№ С„СЂР°РіРјРµРЅС‚ С‚РµРєСЃС‚Р° РІ С„Р°Р№Р»Рµ."""
    target = safe_path(path)

    if not target.is_file():
        return "Р¤Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ"

    content = target.read_text(encoding="utf-8")

    if content.count(old_text) != 1:
        return "Р—Р°РјРµРЅР° РѕС‚РјРµРЅРµРЅР°: СЃС‚Р°СЂС‹Р№ С„СЂР°РіРјРµРЅС‚ РґРѕР»Р¶РµРЅ РІСЃС‚СЂРµС‡Р°С‚СЊСЃСЏ СЂРѕРІРЅРѕ РѕРґРёРЅ СЂР°Р·"

    backup_file(target)

    content = content.replace(old_text, new_text, 1)
    target.write_text(content, encoding="utf-8")

    return "Р¤СЂР°РіРјРµРЅС‚ СѓСЃРїРµС€РЅРѕ Р·Р°РјРµРЅС‘РЅ"


def execute(command):
    if re.search(r"[;&|<>`\r\n]", command):
        return "Р—Р°РїСЂРµС‰РµРЅС‹ РѕРїРµСЂР°С‚РѕСЂС‹ РѕР±РѕР»РѕС‡РєРё Рё С†РµРїРѕС‡РєРё РєРѕРјР°РЅРґ"

    try:
        args = shlex.split(command, posix=False)
        args = [a.strip('"') for a in args]
    except ValueError as exc:
        return f"РћС€РёР±РєР° СЂР°Р·Р±РѕСЂР°: {exc}"

    if not args:
        return "РџСѓСЃС‚Р°СЏ РєРѕРјР°РЅРґР°"

    executable = args[0].lower()

    if executable not in ALLOWED_COMMANDS:
        return f"РљРѕРјР°РЅРґР° {executable} РЅРµ СЂР°Р·СЂРµС€РµРЅР°"

    version_check = preflight_program(args[0])
    if version_check and version_check.startswith("PRE-FLIGHT FAILED"):
        return version_check
    if executable in {"python", "python.exe", "py"} and len(args) > 2 and args[1] == "-m":
        module_check = preflight_python_module(args[0], args[2])
        if module_check and module_check.startswith("PRE-FLIGHT FAILED"):
            return module_check

    if any(a.lower() in BLOCKED_FLAGS for a in args[1:]):
        return "РћРїР°СЃРЅС‹Р№ РїР°СЂР°РјРµС‚СЂ РєРѕРјР°РЅРґС‹ Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ"

    if executable in {"python", "python.exe", "py"}:
        if len(args) > 1 and args[1] == "-m":
            if len(args) < 3 or args[2] != "pytest":
                return "Python СЂР°Р·СЂРµС€С‘РЅ СЃ -m С‚РѕР»СЊРєРѕ РґР»СЏ Р·Р°РїСѓСЃРєР° pytest"

        elif len(args) > 1 and args[1].startswith("-"):
            return "Р—Р°РїСѓСЃРє Python СЃ РїСЂРѕРёР·РІРѕР»СЊРЅС‹РјРё РїР°СЂР°РјРµС‚СЂР°РјРё Р·Р°РїСЂРµС‰С‘РЅ"

        elif len(args) > 1:
            try:
                script = safe_path(args[1])
                if not script.is_file():
                    return "Python-СЃРєСЂРёРїС‚ РґРѕР»Р¶РµРЅ СЃСѓС‰РµСЃС‚РІРѕРІР°С‚СЊ РІ workspace"
                args[1] = str(script)
            except ValueError as exc:
                return str(exc)

    print("\n" + "=" * 55)
    print("Р—РђРџР РћРЎ РќРђ Р’Р«РџРћР›РќР•РќРР• РљРћРњРђРќР”Р«")
    print("Р Р°Р±РѕС‡Р°СЏ РїР°РїРєР°:", WORKSPACE)
    print("РљРѕРјР°РЅРґР°:", command)
    print("=" * 55)

    answer = input("Р Р°Р·СЂРµС€РёС‚СЊ РІС‹РїРѕР»РЅРµРЅРёРµ? (y/n): ").strip().lower()

    if answer != "y":
        return "РљРѕРјР°РЅРґР° РѕС‚РєР»РѕРЅРµРЅР° РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј"

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
        return "РџСЂРµРІС‹С€РµРЅРѕ РІСЂРµРјСЏ РІС‹РїРѕР»РЅРµРЅРёСЏ: 300 СЃРµРєСѓРЅРґ"
    except Exception as exc:
        return f"РћС€РёР±РєР° Р·Р°РїСѓСЃРєР°: {exc}"


@tool
def run_command(command: str) -> str:
    """Р—Р°РїСѓСЃРєР°РµС‚ СЂР°Р·СЂРµС€С‘РЅРЅСѓСЋ РєРѕРјР°РЅРґСѓ СЂР°Р·СЂР°Р±РѕС‚РєРё СЃ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµРј."""
    return execute(command)


@tool
def run_tests() -> str:
    """Р—Р°РїСѓСЃРєР°РµС‚ pytest РІ СЂР°Р±РѕС‡РµРј РїСЂРѕРµРєС‚Рµ СЃ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµРј."""
    return execute("python -m pytest -q")


@tool
def web_search(query: str) -> str:
    """РС‰РµС‚ РґРѕРєСѓРјРµРЅС‚Р°С†РёСЋ Рё С‚РµС…РЅРёС‡РµСЃРєСѓСЋ РёРЅС„РѕСЂРјР°С†РёСЋ РІ РёРЅС‚РµСЂРЅРµС‚Рµ."""
    try:
        results = DDGS().text(query, max_results=6)

        if not results:
            return "Р РµР·СѓР»СЊС‚Р°С‚С‹ РЅРµ РЅР°Р№РґРµРЅС‹"

        return "\n\n".join(
            f"TITLE: {r.get('title', '')}\n"
            f"URL: {r.get('href', '')}\n"
            f"DESCRIPTION: {r.get('body', '')}"
            for r in results
        )[:15000]

    except Exception as exc:
        return f"РћС€РёР±РєР° РїРѕРёСЃРєР°: {exc}"


@tool
def fetch_webpage(url: str) -> str:
    """Р—Р°РіСЂСѓР¶Р°РµС‚ РїСѓР±Р»РёС‡РЅСѓСЋ РІРµР±-СЃС‚СЂР°РЅРёС†Сѓ Рё РёР·РІР»РµРєР°РµС‚ С‚РµРєСЃС‚."""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return "Р Р°Р·СЂРµС€РµРЅС‹ С‚РѕР»СЊРєРѕ HTTP Рё HTTPS Р°РґСЂРµСЃР°"

        if parsed.username or parsed.password:
            return "URL СЃ СѓС‡С‘С‚РЅС‹РјРё РґР°РЅРЅС‹РјРё Р·Р°РїСЂРµС‰С‘РЅ"

        addresses = socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM
        )

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return "Р”РѕСЃС‚СѓРї Рє Р»РѕРєР°Р»СЊРЅС‹Рј Р°РґСЂРµСЃР°Рј Р·Р°РїСЂРµС‰С‘РЅ"

        response = requests.get(
            url,
            timeout=20,
            allow_redirects=False,
            headers={"User-Agent": "AI-Coder-Pro/2.0"}
        )

        if response.is_redirect:
            return "РџРµСЂРµРЅР°РїСЂР°РІР»РµРЅРёРµ РЅРµ РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё"

        response.raise_for_status()

        if len(response.content) > 2_000_000:
            return "РЎС‚СЂР°РЅРёС†Р° РїСЂРµРІС‹С€Р°РµС‚ Р»РёРјРёС‚ 2 РњР‘"

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup([
            "script", "style", "nav", "footer", "header"
        ]):
            element.decompose()

        return soup.get_text(separator="\n", strip=True)[:15000]

    except Exception as exc:
        return f"РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё: {exc}"


TOOLS = [
    list_files,
    search_files,
    read_file,
    write_file,
    replace_in_file,
    run_command,
    run_tests,
    web_search,
    fetch_webpage,
    *CPP_TOOLS
]