"""Token dialog smoke (offscreen)."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit  # noqa: E402

from golden_signing.ui.theme import apply_theme  # noqa: E402
from golden_signing.ui.token_dialogs import CertPickerDialog, PinDialog  # noqa: E402


def _fake_cert() -> SimpleNamespace:
    return SimpleNamespace(
        subject="CN=CÔNG TY TNHH TEST, MST:0123456789",
        issuer="CN=ECA",
        not_valid_after="2027-12-31 00:00:00",
        serial="ABC123",
        token_label="ECA Token",
        fingerprint_sha256="aa" * 32,
    )


def test_cert_picker_selects_first() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    certs = [_fake_cert(), _fake_cert()]
    dlg = CertPickerDialog(certs)
    assert dlg.selected_cert() is not None
    dlg.select_index(1)
    assert dlg._selected_index == 1
    texts = [c.text() for c in dlg.findChildren(QLabel)]
    assert any("CÔNG TY TNHH TEST" in t for t in texts)
    dlg.close()


def test_pin_dialog_mask_and_accept() -> None:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    dlg = PinDialog(company="CÔNG TY TEST")
    assert dlg._edit.echoMode() == QLineEdit.EchoMode.Password
    dlg._toggle.click()
    assert dlg._edit.echoMode() == QLineEdit.EchoMode.Normal
    dlg._edit.setText("123456")
    dlg._accept_if_valid()
    assert dlg.result() == 1  # Accepted
    assert dlg.pin() == "123456"
    dlg.close()
