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
- Диагностика окружения: check_environment (версии Python, Git, CMake, CTest, Ninja, Node.js/npm, Go, .NET, Rust/Cargo, Docker, Ollama, vcpkg, MSVC и зависимости проекта)
- C++: create_sfml_game_project, configure_cpp_project, build_cpp_project, run_cpp_tests, run_cpp_game

Перед выполнением разрешённых внешних команд агент автоматически проверяет доступность и версию известной программы. Перед CMake configure, C++ build и CTest запускается preflight-проверка CMake/MSVC и известной версии SFML из стандартного vcpkg triplet. Если обязательный инструмент отсутствует или известная версия SFML ниже требования CMakeLists.txt, этап останавливается. Версии Python-пакетов из requirements.txt и зависимости vcpkg/npm отображаются в диагностическом отчёте; окончательная проверка разрешения C++/CMake-зависимостей выполняется самим CMake.

Новые игровые проекты по умолчанию создаются в workspace. Для работы с внешним проектом добавь его каталог в AI_CODER_ALLOWED_ROOTS в .env, например AI_CODER_ALLOWED_ROOTS=D:/Games/rougeLikeGame. Можно перечислить несколько корней через точку с запятой. Агент сможет читать, редактировать, собирать и тестировать файлы только внутри workspace и явно разрешённых корней. Резервные копии изменяемых внешних файлов создаются в logs/backups/external. По умолчанию выполнение команд и запуск игры требуют подтверждения.

## Примечания

Для CTest проект должен объявлять enable_testing() и add_test(). Секреты не помещай в Git: настоящий .env игнорируется.
