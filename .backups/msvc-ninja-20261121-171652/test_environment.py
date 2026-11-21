from pathlib import Path

from agent.environment import _project_requirements, _version_tuple, check_environment_report


def test_version_tuple_extracts_numeric_parts():
    assert _version_tuple("SFML 3.1.0") == (3, 1, 0)
    assert _version_tuple("v19.52.37029") == (19, 52, 37029)


def test_project_requirements_reads_cmake_and_vcpkg(tmp_path: Path):
    (tmp_path / "CMakeLists.txt").write_text(
        "find_package(SFML 3 CONFIG REQUIRED COMPONENTS Graphics)", encoding="utf-8"
    )
    (tmp_path / "vcpkg.json").write_text(
        '{"dependencies": ["sfml", "fmt"]}', encoding="utf-8"
    )

    requirements = _project_requirements(tmp_path)

    assert "CMake package SFML >= 3" in requirements
    assert "vcpkg: sfml" in requirements
    assert "vcpkg: fmt" in requirements


def test_environment_report_is_readable_for_workspace():
    report = check_environment_report(".")
    assert "ПРОВЕРКА ОКРУЖЕНИЯ" in report
    assert "CMake" in report
    assert "Совместимость" in report


def test_dotnet_sdk_check_passes_single_argument(monkeypatch, tmp_path):
    from agent import environment

    dotnet = tmp_path / "dotnet.exe"
    dotnet.touch()

    monkeypatch.setattr(
        environment.shutil,
        "which",
        lambda name: str(dotnet) if name == "dotnet" else None,
    )

    received = {}

    def fake_run(path, args, timeout=12):
        received["args"] = tuple(args)
        return "10.0.404 [C:/Program Files/dotnet/sdk]", ""

    monkeypatch.setattr(
        environment,
        "_run_version_path",
        fake_run,
    )

    result = environment._check_programs([".NET SDK"])

    assert received["args"] == ("--list-sdks",)
    assert len(result) == 1
    assert result[0].status == "OK"
    assert result[0].version == "10.0.404"


def test_visual_studio_program_discovery(monkeypatch, tmp_path):
    from agent import environment

    installation = tmp_path

    cmake_dir = (
        installation
        / "Common7"
        / "IDE"
        / "CommonExtensions"
        / "Microsoft"
        / "CMake"
        / "CMake"
        / "bin"
    )

    ninja_dir = cmake_dir.parent / "Ninja"

    cmake_dir.mkdir(parents=True)
    ninja_dir.mkdir(parents=True)

    for filename in ("cmake.exe", "ctest.exe"):
        (cmake_dir / filename).touch()

    (ninja_dir / "ninja.exe").touch()

    monkeypatch.setattr(
        environment.shutil,
        "which",
        lambda name: None,
    )

    monkeypatch.setattr(
        environment,
        "_visual_studio_installation",
        lambda: installation,
    )

    assert environment.find_program_path("CMake") == str(
        cmake_dir / "cmake.exe"
    )

    assert environment.find_program_path("CTest") == str(
        cmake_dir / "ctest.exe"
    )

    assert environment.find_program_path("Ninja") == str(
        ninja_dir / "ninja.exe"
    )


def test_msvc_discovery_prefers_x64_target_compiler(monkeypatch, tmp_path):
    from agent import environment

    x86_compiler = (
        tmp_path
        / "VC"
        / "Tools"
        / "MSVC"
        / "14.52.37025"
        / "bin"
        / "HostX86"
        / "x86"
        / "cl.exe"
    )

    x64_compiler = (
        tmp_path
        / "VC"
        / "Tools"
        / "MSVC"
        / "14.52.37025"
        / "bin"
        / "Hostx64"
        / "x64"
        / "cl.exe"
    )

    x86_compiler.parent.mkdir(parents=True)
    x64_compiler.parent.mkdir(parents=True)

    x86_compiler.touch()
    x64_compiler.touch()

    monkeypatch.setattr(
        environment.shutil,
        "which",
        lambda name: str(x86_compiler) if name == "cl" else None,
    )

    monkeypatch.setattr(
        environment,
        "_visual_studio_installation",
        lambda: tmp_path,
    )

    assert environment.find_program_path("MSVC") == str(x64_compiler)

