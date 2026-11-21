from types import SimpleNamespace
import subprocess
import sys

import pytest

from agent.config import WORKSPACE, safe_workspace_path
from agent import tools


def test_workspace_path_accepts_project_relative_path():
    assert safe_workspace_path("sample/main.cpp") == (WORKSPACE / "sample" / "main.cpp").resolve()


def test_workspace_path_rejects_parent_traversal():
    with pytest.raises(ValueError, match="вне workspace"):
        safe_workspace_path("../outside.txt")


def test_workspace_path_rejects_absolute_path_outside_workspace(tmp_path):
    outside_file = tmp_path / "secret.txt"
    with pytest.raises(ValueError, match="вне workspace"):
        safe_workspace_path(str(outside_file))


def test_gpp_is_in_the_command_allowlist():
    assert "g++" in tools.ALLOWED_COMMANDS
    assert "g++.exe" in tools.ALLOWED_COMMANDS


def test_cd_is_not_treated_as_an_executable():
    result = tools.execute("cd game")
    assert "cd" in result.lower()
    assert "workspace" in result.lower()


def test_shell_chaining_is_rejected():
    result = tools.execute("g++ --version && whoami")
    assert "цепочки команд" in result


def test_command_runs_from_workspace_without_a_shell(monkeypatch):
    observed = {}

    def fake_input(_prompt):
        return "y"

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="compiler version", stderr="")

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tools.execute("g++ --version")

    assert "EXIT CODE: 0" in result
    assert observed["kwargs"]["cwd"] == str(WORKSPACE)
    assert observed["kwargs"]["shell"] is False
    assert observed["args"] == ["g++", "--version"]


def test_python_module_uses_the_running_virtual_environment(monkeypatch):
    observed = {}

    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="compiled", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tools.execute("python -m py_compile agent/main.py")

    assert "EXIT CODE: 0" in result
    assert observed["args"][0] == sys.executable
    assert observed["kwargs"]["cwd"] == str(WORKSPACE)
