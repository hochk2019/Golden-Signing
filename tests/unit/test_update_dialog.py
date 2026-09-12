"""Update dialog offscreen smoke (no network)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.ui.theme import apply_theme  # noqa: E402
from golden_signing.ui.update_dialog import UpdateCheckDialog  # noqa: E402


def test_update_dialog_constructs() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    settings = QSettings("HOCHK", "GoldenSigningTest")
    settings.setValue("update/repo", "")
    dlg = UpdateCheckDialog(settings)
    assert dlg.windowTitle() == "Cập nhật"
    assert dlg._check_btn.isEnabled()
    dlg.close()
