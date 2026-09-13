"""Settings persist without token (isolated QSettings file)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.ui.main_window import MainWindow  # noqa: E402


def _isolated(path: Path) -> QSettings:
    return QSettings(str(path), QSettings.Format.IniFormat)


def test_save_and_load_app_defaults_roundtrip(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    settings = _isolated(tmp_path / "gs.ini")
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")

    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    win._select_mode("invisible")
    win._bg_check.setChecked(False)
    win._logo_check.setChecked(True)
    win._sig_page = 1  # noqa: SLF001
    win._sig_origin = (120, 80)  # noqa: SLF001
    settings.setValue("signatureLogoPath", str(logo))
    win._save_app_defaults()  # noqa: SLF001
    win.close()

    assert str(settings.value("defaultSignatureMode")) == "invisible"
    assert str(settings.value("signatureBg")) == "0"

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
    settings = _isolated(tmp_path / "gs2.ini")
    settings.setValue("signatureLogo", "1")
    settings.remove("signatureLogoPath")
    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    win._load_app_defaults()  # noqa: SLF001
    assert win._logo_check.isChecked() is False  # noqa: SLF001
    win.close()


def test_default_output_dir_syncs_into_main_field(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    settings = _isolated(tmp_path / "gs3.ini")
    out = tmp_path / "signed-out"
    out.mkdir()
    settings.setValue("defaultOutputDir", str(out))
    win = MainWindow()
    win._settings = settings  # noqa: SLF001
    win._sync_output_dir_from_settings()  # noqa: SLF001
    assert win._out_edit.text() == str(out)  # noqa: SLF001
    # resolve uses the visible field first
    win._out_edit.setText("")  # noqa: SLF001
    assert win._resolve_output_dir([]) == out  # noqa: SLF001
    win.close()


def test_settings_save_applies_signature_defaults(tmp_path: Path) -> None:
    from golden_signing.ui.settings_dialog import SettingsDialog

    app = QApplication.instance() or QApplication([])
    settings = _isolated(tmp_path / "gs4.ini")
    win = MainWindow()
    win._settings = settings  # noqa: SLF001

    dlg = SettingsDialog(settings, win)
    dlg._mode.setCurrentIndex(1)  # invisible  # noqa: SLF001
    dlg._bg.setChecked(False)  # noqa: SLF001
    dlg._out_edit.setText(str(tmp_path / "o"))  # noqa: SLF001
    dlg._save()  # noqa: SLF001
    assert dlg.result() == 1

    win._load_app_defaults()  # noqa: SLF001
    win._sync_output_dir_from_settings()  # noqa: SLF001
    assert win._mode_combo.currentData() == "invisible"  # noqa: SLF001
    assert win._bg_check.isChecked() is False  # noqa: SLF001
    assert win._out_edit.text() == str(tmp_path / "o")  # noqa: SLF001
    win.close()
    app.processEvents()
