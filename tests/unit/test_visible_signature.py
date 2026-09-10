"""Phase 6: visible signature + output UX unit tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from golden_signing.signing.appearance import DEFAULT_VISIBLE_BOX, signing_extras  # noqa: E402
from golden_signing.signing.contracts import SignatureMode  # noqa: E402
from golden_signing.signing.pdf_signer import TestCertPdfSigner  # noqa: E402
from golden_signing.signing.profiles import pus_safe_profile  # noqa: E402
from golden_signing.signing.pyhanko_sign import build_sign_call_kwargs  # noqa: E402
from golden_signing.ui.main_window import MainWindow  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


def test_signing_extras_invisible_empty() -> None:
    assert signing_extras(None, visible=False) == {}


def test_signing_extras_visible_has_field() -> None:
    extras = signing_extras(None, visible=True, signer_display="Test")
    assert "new_field_spec" in extras
    assert "stamp_style" in extras
    assert DEFAULT_VISIBLE_BOX[2] > DEFAULT_VISIBLE_BOX[0]


def test_build_kwargs_invisible_no_field_spec() -> None:
    fp = "ab" * 32
    profile = pus_safe_profile(certificate_fingerprint_sha256=fp)
    kwargs = build_sign_call_kwargs(profile)
    assert "new_field_spec" not in kwargs
    assert kwargs["signature_meta"].field_name == "GoldenSigning"


def test_build_kwargs_visible() -> None:
    fp = "ab" * 32
    profile = pus_safe_profile(certificate_fingerprint_sha256=fp)
    profile.mode = SignatureMode.VISIBLE
    kwargs = build_sign_call_kwargs(profile, signer_display="CN")
    assert "new_field_spec" in kwargs
    assert kwargs["signature_meta"].field_name == "GoldenSigningVisible"


def test_visible_sign_lab(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    profile = pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)
    profile.mode = SignatureMode.VISIBLE
    out = tmp_path / "vis.pdf"
    result = engine.sign(SOURCE_PDF, out, profile=profile)
    assert result.success is True, result.message
    data = out.read_bytes()
    # visible field name appears in output
    assert b"GoldenSigningVisible" in data
    ver = engine.verify(out, profile)
    assert ver.cryptographically_valid is True, ver.details


def test_ui_mode_and_output_controls(qapp: QApplication) -> None:
    win = MainWindow()
    assert win._mode_combo.count() == 2
    assert win._mode_combo.itemData(0) == "invisible"
    assert win._out_edit is not None
    win._out_edit.setText("C:/tmp/out")
    assert win._resolve_output_dir([]) == Path("C:/tmp/out")
    win._mode_combo.setCurrentIndex(1)
    assert win._mode_combo.currentData() == "visible"
    win.close()
