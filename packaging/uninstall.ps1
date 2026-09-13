# Golden Sign — per-user uninstaller
$ErrorActionPreference = "Stop"
$AppName = "Golden Sign"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\GoldenSign"
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldenSign"

Get-Process -Name "GoldenSign" -ErrorAction SilentlyContinue | ForEach-Object {
    try { $_.CloseMainWindow() | Out-Null; Start-Sleep -Milliseconds 400; $_.Kill() } catch {}
}

$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Golden Sign.lnk"
if (Test-Path $StartMenu) { Remove-Item $StartMenu -Force }

if (Test-Path $RegPath) { Remove-Item $RegPath -Recurse -Force }

# Remove install dir if we are not running from inside it
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Test-Path $InstallDir) -and ($here -ne $InstallDir)) {
    Remove-Item $InstallDir -Recurse -Force
} elseif (Test-Path $InstallDir) {
    # Schedule delete after process exit
    Start-Process cmd -ArgumentList "/c ping -n 3 127.0.0.1 >nul & rmdir /s /q `"$InstallDir`"" -WindowStyle Hidden
}

Write-Host "Đã gỡ $AppName. Dữ liệu người dùng (lịch sử/hồ sơ) giữ tại %LOCALAPPDATA%\GoldenSign — xóa tay nếu cần."
