"""Shared app data directory and window icon helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

__all__ = ["app_icon_path", "brand_mark_path", "data_dir", "ensure_data_dir"]

_OLD_DIR_NAME = "GoldenSigning"
_NEW_DIR_NAME = "GoldenSign"


def brand_mark_path() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[3]
    return root / "assets" / "branding" / "golden-mark.png"


def app_icon_path() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[3]
    ico = root / "assets" / "branding" / "golden-app-icon.ico"
    if ico.is_file():
        return ico
    return brand_mark_path()


def _candidates() -> tuple[Path, Path]:
    local = Path.home() / "AppData" / "Local"
    return local / _NEW_DIR_NAME, local / _OLD_DIR_NAME


def data_dir() -> Path:
    """User data root (GoldenSign). One-time copy from legacy GoldenSigning."""
    new, old = _candidates()
    try:
        new.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path.home() / f".{_NEW_DIR_NAME.lower()}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    if not any(new.iterdir()) and old.is_dir():
        try:
            for item in old.iterdir():
                dest = new / item.name
                if dest.exists():
                    continue
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        except OSError:
            pass
    return new


def ensure_data_dir() -> Path:
    return data_dir()
