$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

Set-Location $ProjectRoot
$env:AI_CODER_ROOT = $ProjectRoot

$Candidates = @(
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRoot "venv\Scripts\python.exe")
)

$Python = $Candidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $Python) {
    throw "Python virtual environment not found. Run setup.ps1 first."
}

if (-not $env:VCPKG_ROOT) {
    $LocalVcpkg = Join-Path $ProjectRoot "tools\vcpkg"
    if (Test-Path $LocalVcpkg) {
        $env:VCPKG_ROOT = $LocalVcpkg
    }
}

try {
    Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 | Out-Null
}
catch {
    throw "Ollama is not responding at http://127.0.0.1:11434. Start Ollama and retry."
}

& $Python -m agent.main
exit $LASTEXITCODE
