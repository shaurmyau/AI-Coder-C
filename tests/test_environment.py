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
