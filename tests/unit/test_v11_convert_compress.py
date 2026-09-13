"""Tests: document detect, office convert (optional), compression."""

from __future__ import annotations

from pathlib import Path

import pytest

from golden_signing.compress.engine import (
    CompressionError,
    CompressionTier,
    compress_pdf,
    default_profile,
    has_signature,
)
from golden_signing.document.types import DocumentType, detect_document_type


def test_detect_pdf_magic(tmp_path: Path) -> None:
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    assert detect_document_type(p) is DocumentType.PDF


def test_detect_unknown(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")
    assert detect_document_type(p) is DocumentType.UNKNOWN


def _make_text_pdf(path: Path) -> None:
    import pikepdf

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(595, 842))
        pdf.save(path)


def test_compress_lossless_text_pdf(tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    _make_text_pdf(src)
    # Add some compressible content via save twice
    out = tmp_path / "out.pdf"
    result = compress_pdf(src, out, default_profile(CompressionTier.LOSSLESS))
    assert out.is_file()
    assert result.before_bytes > 0
    assert result.after_bytes > 0


def test_skip_when_under_target(tmp_path: Path) -> None:
    src = tmp_path / "small.pdf"
    _make_text_pdf(src)
    out = tmp_path / "out.pdf"
    profile = default_profile(CompressionTier.PUS_SAFE)
    profile.target_bytes = 10 * 1024 * 1024  # huge target
    result = compress_pdf(src, out, profile)
    assert result.skipped is True
    assert out.is_file()


def test_block_signed_pdf(tmp_path: Path) -> None:
    # Private fixture if present
    priv = Path(__file__).resolve().parent.parent / "fixtures" / "private" / "ecus_signed.pdf"
    if not priv.is_file():
        pytest.skip("no signed fixture")
    out = tmp_path / "x.pdf"
    with pytest.raises(CompressionError) as ei:
        compress_pdf(priv, out, default_profile())
    assert ei.value.code == "SIGNED_PDF"


def test_has_signature_false_on_blank(tmp_path: Path) -> None:
    src = tmp_path / "b.pdf"
    _make_text_pdf(src)
    assert has_signature(src) is False

# Note: Office COM conversion is verified via standalone spike (`.spike/v11`)
# and integration scripts; in-process COM can hard-crash the pytest host.
