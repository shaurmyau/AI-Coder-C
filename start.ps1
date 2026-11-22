$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

Set-Location $ProjectRoot
$env:AI_CODER_ROOT = $ProjectRoot

function Add-PathEntry {
    param([string]$Entry)

    if (-not $Entry -or -not (Test-Path -LiteralPath $Entry -PathType Container)) {
        return
    }

    $normalized = [System.IO.Path]::GetFullPath($Entry).TrimEnd([char]92)
    $entries = @($env:Path -split ';' | Where-Object { $_.Trim() })
    $alreadyPresent = $entries | Where-Object {
        $_.Trim().TrimEnd([char]92) -ieq $normalized
    }

    if (-not $alreadyPresent) {
        $env:Path = "$normalized;$env:Path"
    }
}

# Import the Visual Studio developer environment into this process.
$ProgramFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$VsWhere = $null
if ($ProgramFilesX86) {
    $VsWhere = Join-Path $ProgramFilesX86 "Microsoft Visual Studio\Installer\vswhere.exe"
}

$VsInstallPath = $null
if ($VsWhere -and (Test-Path -LiteralPath $VsWhere)) {
    $VsInstallPath = & $VsWhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1
    if (-not $VsInstallPath) {
        $VsInstallPath = & $VsWhere -latest -products '*' -property installationPath 2>$null | Select-Object -First 1
    }
}

$VsDevCmdCandidates = @()
if ($VsInstallPath) {
    $VsDevCmdCandidates += Join-Path $VsInstallPath "Common7\Tools\VsDevCmd.bat"
}
if ($ProgramFilesX86) {
    $VsDevCmdCandidates += Join-Path $ProgramFilesX86 "Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat"
    $VsDevCmdCandidates += Join-Path $ProgramFilesX86 "Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
}

$VsDevCmd = $VsDevCmdCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if ($VsDevCmd) {
    Write-Host "Loading Visual Studio environment: $VsDevCmd" -ForegroundColor Cyan
    $VsCommand = 'call "' + $VsDevCmd + '" -no_logo -arch=x64 -host_arch=x64 && set'
    $VsOutput = & $env:ComSpec /d /c $VsCommand
    $VsExitCode = $LASTEXITCODE

    if ($VsExitCode -eq 0) {
        foreach ($line in $VsOutput) {
            $separator = $line.IndexOf('=')
            if ($separator -le 0) {
                continue
            }

            $name = $line.Substring(0, $separator)
            $value = $line.Substring($separator + 1)
            if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$') {
                [Environment]::SetEnvironmentVariable($name, $value, [EnvironmentVariableTarget]::Process)
            }
        }
    }
    else {
        Write-Warning "VsDevCmd.bat failed with exit code $VsExitCode. MSVC may be unavailable."
    }
}
else {
    Write-Warning "VsDevCmd.bat not found. MSVC tools will be reported as unavailable."
}

# Add installed LLVM and vcpkg paths to this agent process.
$LlvmCandidates = @()
if ($env:LLVM_BIN) {
    $LlvmCandidates += $env:LLVM_BIN
}
if ($env:ProgramFiles) {
    $LlvmCandidates += Join-Path $env:ProgramFiles "LLVM\bin"
}
$LlvmBin = $LlvmCandidates |
    Where-Object { Test-Path -LiteralPath (Join-Path $_ "clang++.exe") } |
    Select-Object -First 1
if ($LlvmBin) {
    Add-PathEntry $LlvmBin
}

$VcpkgCandidates = @()
if ($env:VCPKG_ROOT) {
    $VcpkgCandidates += $env:VCPKG_ROOT
}
$VcpkgCandidates += Join-Path $ProjectRoot "tools\vcpkg"
$VcpkgRoot = $VcpkgCandidates |
    Where-Object { Test-Path -LiteralPath (Join-Path $_ "vcpkg.exe") } |
    Select-Object -First 1

if ($VcpkgRoot) {
    $env:VCPKG_ROOT = $VcpkgRoot
    Add-PathEntry $VcpkgRoot
}
else {
    Write-Warning "vcpkg.exe not found. VCPKG_ROOT was not configured."
}

$Candidates = @(
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    (Join-Path $ProjectRoot "venv\Scripts\python.exe")
)

$Python = $Candidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if (-not $Python) {
    throw "Python virtual environment not found. Run setup.ps1 first."
}

Write-Host ""
Write-Host "=== AI CODER TOOLCHAIN ===" -ForegroundColor Cyan
foreach ($name in @("clang++", "cl", "msbuild", "vcpkg", "cmake", "ninja", "g++", "gdb")) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) {
        Write-Host "[OK] $name : $($command.Source)" -ForegroundColor Green
    }
    else {
        Write-Host "[NOT FOUND] $name" -ForegroundColor Yellow
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
