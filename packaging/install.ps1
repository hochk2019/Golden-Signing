# Golden Sign — per-user installer (no admin required)
# Copies payload next to this script into %LOCALAPPDATA%\Programs\GoldenSign
# Registers uninstall entry for Windows Settings → Apps.

$ErrorActionPreference = "Stop"
$AppName = "Golden Sign"
$Publisher = "HOC HK"
$Version = "1.1.2"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\GoldenSign"
$ExeName = "GoldenSign.exe"
$Payload = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Cài $AppName $Version vào $InstallDir ..."

if (-not (Test-Path (Join-Path $Payload $ExeName))) {
    Write-Error "Không tìm thấy $ExeName cạnh script. Hãy chạy từ thư mục đã giải nén."
}

# Close running instance
Get-Process -Name "GoldenSign" -ErrorAction SilentlyContinue | ForEach-Object {
    try { $_.CloseMainWindow() | Out-Null; Start-Sleep -Milliseconds 400; $_.Kill() } catch {}
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
# Copy payload except this installer script family
Get-ChildItem -Path $Payload | ForEach-Object {
    if ($_.Name -in @("install.ps1", "uninstall.ps1", "install.bat")) { return }
    $dest = Join-Path $InstallDir $_.Name
    if ($_.PSIsContainer) {
        Copy-Item $_.FullName -Destination $dest -Recurse -Force
    } else {
        Copy-Item $_.FullName -Destination $dest -Force
    }
}

# Uninstall registry (per-user)
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldenSign"
New-Item -Path $RegPath -Force | Out-Null
$UninstExe = Join-Path $InstallDir "uninstall.ps1"
Set-ItemProperty -Path $RegPath -Name "DisplayName" -Value $AppName
Set-ItemProperty -Path $RegPath -Name "DisplayVersion" -Value $Version
Set-ItemProperty -Path $RegPath -Name "Publisher" -Value $Publisher
Set-ItemProperty -Path $RegPath -Name "InstallLocation" -Value $InstallDir
Set-ItemProperty -Path $RegPath -Name "DisplayIcon" -Value (Join-Path $InstallDir $ExeName)
Set-ItemProperty -Path $RegPath -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UninstExe`""
Set-ItemProperty -Path $RegPath -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $RegPath -Name "NoRepair" -Value 1 -Type DWord

# Start Menu shortcut
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Golden Sign.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($StartMenu)
$Shortcut.TargetPath = Join-Path $InstallDir $ExeName
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = Join-Path $InstallDir $ExeName
$Shortcut.Save()

Write-Host "Cài xong. Mở Start Menu → Golden Sign."
Write-Host "Gỡ cài đặt: Settings → Apps → Golden Sign, hoặc uninstall.ps1 trong $InstallDir"
