# AI Coder setup for Windows 11
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot
Write-Host "=== AI Coder: Python environment ===" -ForegroundColor Cyan
$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($PythonCommand) {
    & py -3 -m venv .venv
} else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) { throw "Python 3 is not installed or not in PATH." }
    & python -m venv .venv
}
if ($LASTEXITCODE -ne 0) { throw "Could not create .venv." }
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
Write-Host "Checking C++ tools..." -ForegroundColor Cyan
foreach ($Command in @("cmake", "git")) {
    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        Write-Host "$Command : OK"
    } else {
        Write-Warning "$Command not found in PATH."
    }
}
$Vcpkg = Join-Path $ProjectRoot "tools\vcpkg"
if (Test-Path (Join-Path $Vcpkg "scripts\buildsystems\vcpkg.cmake")) {
    $env:VCPKG_ROOT = $Vcpkg
    Write-Host "vcpkg : $Vcpkg"
} elseif ($env:VCPKG_ROOT -and (Test-Path (Join-Path $env:VCPKG_ROOT "scripts\buildsystems\vcpkg.cmake"))) {
    Write-Host "vcpkg : $env:VCPKG_ROOT"
} else {
    Write-Warning "vcpkg toolchain not found. Set VCPKG_ROOT in .env or install vcpkg."
}
Write-Host "Setup complete. Configure .env if needed, then run .\start.ps1" -ForegroundColor Green
