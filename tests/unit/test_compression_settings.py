"""Compression settings persist (QSettings JSON) + apply on sign."""

from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.compress.engine import CompressionProfile, CompressionTier  # noqa: E402
from golden_signing.ui.main_window import MainWindow  # noqa: E402


def test_compression_profile_roundtrip(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "gs.ini"), QSettings.Format.IniFormat)
    win = MainWindow()
    win._settings = settings  # noqa: SLF001

    prof = CompressionProfile(
        name="My PUS",
        tier=CompressionTier.PUS_SAFE.value,
        target_bytes=300 * 1024,
        jpeg_quality=65,
        max_dpi=120,
    )
    from dataclasses import asdict

    settings.setValue("compressionProfile", json.dumps(asdict(prof)))
    loaded = win._load_compression_profile()  # noqa: SLF001
    assert loaded.name == "My PUS"
    assert loaded.target_bytes == 300 * 1024
    assert loaded.jpeg_quality == 65
    assert loaded.max_dpi == 120
    win.close()


def test_compression_profile_default_when_empty(tmp_path) -> None:
    QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "gs2.ini"), QSettings.Format.IniFormat)
    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    settings.remove("compressionProfile")
    loaded = win._load_compression_profile()  # noqa: SLF001
    assert loaded.tier == CompressionTier.PUS_SAFE.value
    win.close()
