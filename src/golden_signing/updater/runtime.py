"""Frozen-app helpers for update apply + relaunch."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__all__ = ["app_install_dir", "is_frozen", "relaunch_app"]


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
