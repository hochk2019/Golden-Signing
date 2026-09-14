"""Compression dialog must keep saved values when reopened."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.compress.engine import CompressionProfile, CompressionTier  # noqa: E402
from golden_signing.ui.compression_dialog import CompressionSettingsDialog  # noqa: E402
from golden_signing.ui.theme import apply_theme  # noqa: E402


def test_dialog_keeps_saved_profile_on_open() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    saved = CompressionProfile(
        name="PUS custom 400",
        tier=CompressionTier.PUS_SAFE.value,
        target_bytes=400 * 1024,
        jpeg_quality=55,
        max_dpi=110,
    )
    dlg = CompressionSettingsDialog(saved)
    assert dlg._target_kb.value() == 400
    assert dlg._quality.value() == 55
    assert dlg._dpi.value() == 110
    assert dlg._name.text() == "PUS custom 400"
    # switching tier loads that preset (not keep old)
    dlg._tier.setCurrentIndex(1)  # Balanced
    assert dlg._quality.value() == 85
    dlg.close()
