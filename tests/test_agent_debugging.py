import subprocess
from types import SimpleNamespace

from agent import tools
from agent.config import PROJECT_ROOT, WORKSPACE


def test_run_tests_uses_repository_root(monkeypatch):
    observed = {}
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="2 passed", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tools.run_tests.invoke({})

    assert "EXIT CODE: 0" in result
    assert observed["kwargs"]["cwd"] == str(PROJECT_ROOT)
    assert observed["args"][-2:] == ["-q", "tests"]


def test_execute_rejects_working_directory_outside_project(tmp_path):
    result = tools.execute("git --version", working_directory=tmp_path)

    assert "только из корня проекта или workspace" in result


def test_build_cpp_project_stops_after_configure_failure(monkeypatch):
    observed = {"commands": []}
    monkeypatch.setattr(tools, "safe_path", lambda _path: WORKSPACE / "test-build")
    monkeypatch.setattr(tools.shutil, "which", lambda name: "cmake.exe" if name == "cmake" else None)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    def fake_run(args, **kwargs):
        observed["commands"].append((args, kwargs))
        return SimpleNamespace(returncode=1, stdout="", stderr="CMake configure failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tools.build_cpp_project.invoke({"build_directory": "test-build", "configuration": "Debug"})

    assert "EXIT CODE: 1" in result
    assert "CMake configure failed" in result
    assert len(observed["commands"]) == 1
    assert observed["commands"][0][1]["shell"] is False


def test_run_cpp_tests_does_not_treat_missing_ctest_as_success(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "safe_path", lambda _path: tmp_path)

    result = tools.run_cpp_tests.invoke({"build_directory": "build", "configuration": "Debug"})

    assert "CTest-тесты не сконфигурированы" in result
    assert "не означает, что тесты прошли" in result


def test_run_gui_starts_detached_and_reports_live_pid(monkeypatch, tmp_path):
    executable = tmp_path / "game.exe"
    executable.write_bytes(b"test")
    observed = {}

    class FakeProcess:
        pid = 4812
        returncode = None

        def wait(self, timeout):
            raise subprocess.TimeoutExpired(cmd="game.exe", timeout=timeout)

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        observed["args"] = args
        observed["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(tools, "safe_path", lambda _path: executable)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    result = tools.run_gui.invoke({"executable": "build/game.exe", "arguments": ""})

    assert "PID: 4812" in result
    assert "не доказывает" in result
    assert observed["args"] == [str(executable)]
    assert observed["kwargs"]["cwd"] == str(WORKSPACE)
    assert observed["kwargs"]["shell"] is False


def test_run_gui_reports_early_windows_crash_as_hex(monkeypatch, tmp_path):
    executable = tmp_path / "game.exe"
    executable.write_bytes(b"test")

    class CrashedProcess:
        pid = 4813
        returncode = 3221226525

        def wait(self, timeout):
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(tools, "safe_path", lambda _path: executable)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: CrashedProcess())

    result = tools.run_gui.invoke({"executable": "build/game.exe", "arguments": ""})

    assert "3221226525" in result
    assert "0xC000041D" in result
    assert "Ненулевой код означает" in result
