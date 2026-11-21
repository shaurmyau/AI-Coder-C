
$Project = "D:\AI-Coder-C++"
$Archive = "$env:USERPROFILE\Desktop\AI-Coder-C-source.zip"

if (!(Test-Path $Project)) {
    throw "Проект не найден: $Project"
}

$Temp = Join-Path $env:TEMP "AI-Coder-C-source"
Remove-Item $Temp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $Temp | Out-Null

$Exclude = @(
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "vcpkg",
    "build",
    "dist",
    "node_modules",
    ".vs"
)

Get-ChildItem $Project -Force | Where-Object {
    $_.Name -notin $Exclude -and
    $_.Name -notin @(".env")
} | ForEach-Object {
    Copy-Item $_.FullName $Temp -Recurse -Force
}

Get-ChildItem $Temp -Recurse -File |
    Where-Object {
        $_.Extension -in @(
            ".db", ".sqlite", ".sqlite3",
            ".exe", ".dll", ".lib", ".obj", ".pdb"
        ) -or $_.Name -eq ".env"
    } |
    Remove-Item -Force

Remove-Item $Archive -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$Temp\*" -DestinationPath $Archive -CompressionLevel Optimal

Write-Host ""
Write-Host "Архив создан: $Archive" -ForegroundColor Green
