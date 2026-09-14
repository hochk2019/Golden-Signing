"""Frozen-app helpers for update apply + relaunch."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__all__ = [
    "app_install_dir",
    "is_frozen",
    "launch_update_helper",
    "relaunch_app",
    "write_update_helper",
]


def is_frozen() -> bool:
    """True when running from PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def app_install_dir() -> Path | None:
    """Directory to replace on update (onedir root). None when running from source."""
    if not is_frozen():
        return None
    exe = Path(sys.executable).resolve()
    return exe.parent


def relaunch_app() -> None:
    """Start the current executable again (after staged swap)."""
    exe = sys.executable
    subprocess.Popen([exe], close_fds=True)  # noqa: S603


def write_update_helper(
    update_root: Path,
    install_dir: Path,
    staged_dir: Path,
    *,
    exe_name: str = "GoldenSign.exe",
    log_name: str = "apply_update.log",
) -> Path:
    """
    Write a PowerShell script that waits for this app to exit, then swaps
    staged_dir → install_dir and relaunches. Safe on Windows: you cannot
    rename/delete a directory that still contains the running executable.
    """
    update_root = Path(update_root)
    update_root.mkdir(parents=True, exist_ok=True)
    log_path = update_root / log_name
    ps1 = update_root / "apply_update.ps1"
    # Escape single quotes for PowerShell single-quoted strings
    def q(p: Path) -> str:
        return str(p).replace("'", "''")

    process_name = Path(exe_name).stem
    content = f"""$ErrorActionPreference = 'Continue'
$log = '{q(log_path)}'
function Log($m) {{ Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' ' + $m) }}
Log 'helper start'
$install = '{q(install_dir)}'
$staged = '{q(staged_dir)}'
$exeName = '{q(exe_name)}'
$procName = '{q(process_name)}'

# Wait until the app process exits (it launched us then quit)
for ($i = 0; $i -lt 200; $i++) {{
    $p = Get-Process -Name $procName -ErrorAction SilentlyContinue
    if (-not $p) {{ Log 'process exited'; break }}
    Start-Sleep -Milliseconds 150
}}
Start-Sleep -Milliseconds 400

$old = Join-Path (Split-Path -Parent $install) 'GoldenSign.old'
if (Test-Path -LiteralPath $old) {{
    Log 'removing old-live'
    Remove-Item -LiteralPath $old -Recurse -Force -ErrorAction SilentlyContinue
}}

if (Test-Path -LiteralPath $install) {{
    try {{
        Rename-Item -LiteralPath $install -NewName 'GoldenSign.old' -Force
        Log 'renamed live aside'
    }} catch {{
        Log ('rename failed: ' + $_.Exception.Message)
        Remove-Item -LiteralPath $install -Recurse -Force -ErrorAction SilentlyContinue
        Log 'force-removed live'
    }}
}}

if (Test-Path -LiteralPath $staged) {{
    Copy-Item -LiteralPath $staged -Destination $install -Recurse -Force
    Log 'copied staged -> install'
}} else {{
    Log 'ERROR: staged missing'
    exit 1
}}

$newExe = Join-Path $install $exeName
if (Test-Path -LiteralPath $newExe) {{
    Start-Process -FilePath $newExe
    Log 'relaunched'
}} else {{
    Log 'ERROR: new exe missing'
    exit 1
}}
"""
    ps1.write_text(content, encoding="utf-8")
    return ps1


def launch_update_helper(script: Path) -> None:
    """Start detached PowerShell so it survives this process exiting."""
    script = Path(script)
    creationflags = 0
    if sys.platform.startswith("win"):
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        creationflags = 0x00000008 | 0x00000200
    subprocess.Popen(  # noqa: S603
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script),
        ],
        close_fds=True,
        creationflags=creationflags,
    )
