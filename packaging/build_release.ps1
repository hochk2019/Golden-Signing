# Build Golden Sign: slim onedir + portable zip + Inno Setup installer + checksums
# Run from repo root: packaging\build_release.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Version = "1.1.6"
$ZipName = "GoldenSign-$Version-win64.zip"
$SetupName = "GoldenSign-Setup-$Version.exe"

Write-Host "=== PyInstaller onedir (slim) ==="
& $Py -m PyInstaller --noconfirm --clean packaging\golden_sign.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$AppDir = Join-Path $Root "dist\GoldenSign"
if (-not (Test-Path (Join-Path $AppDir "GoldenSign.exe"))) {
    throw "Missing GoldenSign.exe in $AppDir"
}

$folderMB = [math]::Round(((Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host "Onedir size: $folderMB MB"

Write-Host "=== Bundle portable helpers ==="
Copy-Item packaging\install.ps1, packaging\uninstall.ps1 -Destination $AppDir -Force
@"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
"@ | Set-Content -Path (Join-Path $AppDir "Cai-dat.bat") -Encoding ASCII

$OutDir = Join-Path $Root "dist\release"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "=== Portable zip ==="
$ZipPath = Join-Path $OutDir $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $ZipPath

Write-Host "=== Inno Setup installer ==="
$ISCC = $null
$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
foreach ($c in $candidates) { if (Test-Path $c) { $ISCC = $c; break } }
if (-not $ISCC) {
    $isccCmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($isccCmd) { $ISCC = $isccCmd.Source }
}
if ($ISCC) {
    & $ISCC packaging\golden_sign.iss
    if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
} else {
    Write-Warning "ISCC.exe not found - skip Setup.exe. Install Inno Setup 6 and re-run."
}

Write-Host "=== SHA256 ==="
$sums = Join-Path $OutDir "checksums.txt"
$lines = @()
Get-ChildItem $OutDir -File | Where-Object { $_.Name -match '\.(zip|exe)$' } | ForEach-Object {
    $h = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower()
    $lines += "{0}  {1}" -f $h, $_.Name
    Write-Host "$($_.Name)  $h"
}
$lines | Set-Content -Path $sums -Encoding ascii

Write-Host "=== Release folder ==="
Get-ChildItem $OutDir | Format-Table Name, @{n='MB';e={[math]::Round($_.Length/1MB,2)}}
