"""Phase 10 — app paths + icon helpers."""

from __future__ import annotations

from golden_signing.storage.app_paths import app_icon_path, brand_mark_path, data_dir


def test_app_icon_exists() -> None:
    path = app_icon_path()
    assert path.is_file()
    assert path.suffix.lower() in {".ico", ".png"}


def test_brand_mark_exists() -> None:
    assert brand_mark_path().is_file()


def test_data_dir_uses_goldensign_name() -> None:
    d = data_dir()
    assert d.name == "GoldenSign" or d.name.startswith(".goldensign")
