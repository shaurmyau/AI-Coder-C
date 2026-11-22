$ErrorActionPreference = "Stop"

# Пути к установленным инструментам
$llvmBin = "C:\Program Files\LLVM\bin"
$vcpkgRoot = "D:\AI-Coder-C++\tools\vcpkg"
$vsDevCmd = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat"

# Проверяем наличие файлов
if (-not (Test-Path "$llvmBin\clang++.exe")) {
    throw "Не найден clang++.exe"
}

if (-not (Test-Path "$vcpkgRoot\vcpkg.exe")) {
    throw "Не найден vcpkg.exe"
}

if (-not (Test-Path $vsDevCmd)) {
    throw "Не найден VsDevCmd.bat"
}

# Добавляем LLVM и vcpkg в постоянный пользовательский PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$entries = @($userPath -split ';' | Where-Object { $_.Trim() })

foreach ($path in @($llvmBin, $vcpkgRoot)) {
    $exists = $entries | Where-Object {
        $_.TrimEnd('\') -ieq $path.TrimEnd('\')
    }

    if (-not $exists) {
        $entries += $path
    }
}

[Environment]::SetEnvironmentVariable("Path", ($entries -join ';'), "User")

# Задаём VCPKG_ROOT
[Environment]::SetEnvironmentVariable("VCPKG_ROOT", $vcpkgRoot, "User")

# Обновляем переменные текущего PowerShell
$env:Path = "$llvmBin;$vcpkgRoot;$env:Path"
$env:VCPKG_ROOT = $vcpkgRoot

# Загружаем окружение Visual Studio
Write-Host "`n=== ЗАГРУЗКА VISUAL STUDIO ===" -ForegroundColor Cyan

$vsOutput = & $env:ComSpec /d /c "call `"$vsDevCmd`" -no_logo -arch=x64 -host_arch=x64 && set"

if ($LASTEXITCODE -ne 0) {
    throw "Не удалось загрузить окружение Visual Studio"
}

foreach ($line in $vsOutput) {
    if ($line -match '^([^=]+)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]

        if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            [Environment]::SetEnvironmentVariable(
                $name,
                $value,
                [EnvironmentVariableTarget]::Process
            )
        }
    }
}

# Проверяем обнаружение инструментов
Write-Host "`n=== ПРОВЕРКА ИНСТРУМЕНТОВ ===" -ForegroundColor Cyan

$tools = @(
    "clang++",
    "vcpkg",
    "cl",
    "msbuild",
    "cmake",
    "ctest",
    "ninja",
    "g++",
    "gcc",
    "gdb"
)

foreach ($tool in $tools) {
    $cmd = Get-Command $tool -ErrorAction SilentlyContinue

    if ($cmd) {
        Write-Host "[OK] $tool : $($cmd.Source)" -ForegroundColor Green
    }
    else {
        Write-Host "[NOT FOUND] $tool" -ForegroundColor Red
    }
}

Write-Host "`nVCPKG_ROOT = $env:VCPKG_ROOT"
Write-Host "`nНастройка завершена." -ForegroundColor Green