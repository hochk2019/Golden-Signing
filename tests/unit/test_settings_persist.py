"""Settings persist without token (isolated QSettings file)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.ui.main_window import MainWindow  # noqa: E402


def test_save_and_load_app_defaults_roundtrip(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    ini = tmp_path / "gs.ini"
    settings = QSettings(str(ini), QSettings.Format.IniFormat)

    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    win._mode_combo.setCurrentIndex(0)  # invisible
    win._bg_check.setChecked(False)
    win._logo_check.setChecked(True)
    win._sig_page = 1  # noqa: SLF001
    win._sig_origin = (120, 80)  # noqa: SLF001
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    settings.setValue("signatureLogoPath", str(logo))
    win._save_active_profile()  # noqa: SLF001
    win.close()

    win2 = MainWindow()
    win2._settings = settings  # noqa: SLF001
    win2._load_app_defaults()  # noqa: SLF001
    assert win2._mode_combo.currentData() == "invisible"  # noqa: SLF001
    assert win2._bg_check.isChecked() is False  # noqa: SLF001
    assert win2._sig_page == 1  # noqa: SLF001
    assert win2._sig_origin == (120, 80)  # noqa: SLF001
    assert win2._logo_check.isChecked() is True  # noqa: SLF001
    win2.close()


def test_no_logo_path_forces_logo_off(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    ini = tmp_path / "gs2.ini"
    settings = QSettings(str(ini), QSettings.Format.IniFormat)
    settings.setValue("signatureLogo", "1")
    settings.remove("signatureLogoPath")
    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    win._load_app_defaults()  # noqa: SLF001
    assert win._logo_check.isChecked() is False  # noqa: SLF001
    win.close()
