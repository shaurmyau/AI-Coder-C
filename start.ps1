$ErrorActionPreference = "Stop"
Set-Location "D:\AI-Coder"

$PYTHON = "D:\AI-Coder\venv\Scripts\python.exe"

if (-not (Test-Path $PYTHON)) {
    throw "Виртуальное окружение не найдено. Сначала запусти setup.ps1"
}

try {
    Invoke-RestMethod "http://127.0.0.1:11434/api/tags" | Out-Null
}
catch {
    throw "Ollama не запущена. Запусти Ollama и повтори попытку."
}

& $PYTHON -m agent.main
