# AI Coder — C++ Game Developer

Локальный AI-агент на Ollama + LangChain/LangGraph с SQLite-памятью, файловыми и веб-инструментами, а также инструментами разработки C++ игр.

## Стек

- Python, Ollama (qwen3.5:9b), LangChain / LangGraph, SQLite
- C++20, MSVC x64, CMake, vcpkg, SFML 3.x

## Установка

Открой PowerShell в каталоге проекта и выполни:

    Set-ExecutionPolicy -Scope Process Bypass
    .\setup.ps1
    Copy-Item .env.example .env

Проверь настройки .env, запусти Ollama, затем:

    ollama list
    .\start.ps1

## Инструменты

- Файлы: list_files, search_files, read_file, write_file, replace_in_file
- Python tests: run_tests
- Интернет: web_search, fetch_webpage
- C++: create_sfml_game_project, configure_cpp_project, build_cpp_project, run_cpp_tests, run_cpp_game

Новые игровые проекты создаются в workspace. По умолчанию выполнение команд и запуск игры требуют подтверждения.

## Примечания

Для CTest проект должен объявлять enable_testing() и add_test(). Секреты не помещай в Git: настоящий .env игнорируется.
