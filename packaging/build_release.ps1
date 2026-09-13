# Build Golden Sign onedir + zip release + checksums.txt
# Run from repo root: packaging\build_release.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Version = "1.0.0"
$DistName = "GoldenSign"
$ZipName = "GoldenSign-$Version-win64.zip"

Write-Host "=== PyInstaller onedir ==="
& $Py -m PyInstaller --noconfirm --clean packaging\golden_sign.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$AppDir = Join-Path $Root "dist\GoldenSign"
if (-not (Test-Path (Join-Path $AppDir "GoldenSign.exe"))) {
    throw "Missing GoldenSign.exe in $AppDir"
}

Write-Host "=== Bundle installer scripts ==="
Copy-Item packaging\install.ps1, packaging\uninstall.ps1 -Destination $AppDir -Force
# Convenience launcher for double-click install
@"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
"@ | Set-Content -Path (Join-Path $AppDir "Cai-dat.bat") -Encoding ASCII

Write-Host "=== Zip ==="
$OutDir = Join-Path $Root "dist\release"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ZipPath = Join-Path $OutDir $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $ZipPath

Write-Host "=== SHA256 ==="
$hash = (Get-FileHash -Algorithm SHA256 $ZipPath).Hash.ToLower()
$sums = Join-Path $OutDir "checksums.txt"
"{0}  {1}" -f $hash, $ZipName | Set-Content -Path $sums -Encoding ascii
Write-Host "Wrote $ZipPath"
Write-Host "SHA256 $hash"
Get-ChildItem $OutDir | Format-Table Name, Length
