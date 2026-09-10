"""Tests: history store + diagnostics export."""

from __future__ import annotations

from pathlib import Path

from golden_signing.diagnostics.export import build_diagnostics, export_diagnostics
from golden_signing.storage.history import SigningHistory


def test_history_record_and_export(tmp_path: Path) -> None:
    db = tmp_path / "h.db"
    h = SigningHistory(db)
    h.record(
        input_path="a.pdf",
        output_path="a_signed.pdf",
        status="SUCCESS",
        certificate="ab" * 32,
        profile_mode="visible",
    )
    h.record(
        input_path="b.pdf",
        output_path=None,
        status="SIGN_FAILED",
        error_code="SIGN_FAILED",
        message="boom",
    )
    rows = h.recent(10)
    assert len(rows) == 2
    assert rows[0].status == "SIGN_FAILED"  # newest first
    csv = h.export_csv(tmp_path / "out.csv")
    text = csv.read_text(encoding="utf-8")
    assert "a.pdf" in text
    assert "SIGN_FAILED" in text
    h.close()


def test_diagnostics_export(tmp_path: Path) -> None:
    d = build_diagnostics()
    assert d["app"] == "Golden Signing"
    assert "packages" in d
    out = export_diagnostics(tmp_path)
    assert out.is_file()
    assert "Golden Signing" in out.read_text(encoding="utf-8")
