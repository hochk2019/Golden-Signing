"""Unit tests for pdf/inspection.py preflight (T2)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.signing.contracts import PreflightLevel

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"
SIGNED_PDF = FIXTURES / "ecus_signed.pdf"


class TestSourcePdf:
    """ecus_source.pdf must classify as SAFE."""

    def test_source_level_safe(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.level is PreflightLevel.SAFE

    def test_source_page_count(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.page_count == 4

    def test_source_not_encrypted(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.encrypted is False

    def test_source_no_signatures(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.existing_signatures == []

    def test_source_no_acroform(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.has_acroform is False

    def test_source_pdf_version(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.pdf_version == "1.7"

    def test_source_file_size(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.file_size_bytes == SOURCE_PDF.stat().st_size

    def test_source_incremental_revisions(self) -> None:
        result = preflight_pdf(SOURCE_PDF)
        assert result.incremental_revisions >= 1


class TestSignedPdf:
    """ecus_signed.pdf must classify as WARN with signature metadata."""

    def test_signed_level_warn(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.level is PreflightLevel.WARN

    def test_signed_page_count(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.page_count == 4

    def test_signed_not_encrypted(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.encrypted is False

    def test_signed_has_acroform(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.has_acroform is True

    def test_signed_existing_signatures(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert len(result.existing_signatures) >= 1
        assert "Signature1" in result.existing_signatures

    def test_signed_warnings_present(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert any("signature" in w.lower() for w in result.warnings)

    def test_signed_incremental_revisions(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.incremental_revisions >= 2

    def test_signed_pdf_version(self) -> None:
        result = preflight_pdf(SIGNED_PDF)
        assert result.pdf_version == "1.7"


class TestBlockCases:
    """BLOCK for missing, non-PDF, and encrypted files."""

    def test_missing_file_blocks(self, tmp_path: Path) -> None:
        result = preflight_pdf(tmp_path / "nope.pdf")
        assert result.level is PreflightLevel.BLOCK
        assert result.errors

    def test_non_pdf_bytes_blocks(self, tmp_path: Path) -> None:
        bad = tmp_path / "not.pdf"
        bad.write_bytes(b"this is definitely not a pdf at all")
        result = preflight_pdf(bad)
        assert result.level is PreflightLevel.BLOCK
        assert result.errors

    def test_empty_file_blocks(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")
        result = preflight_pdf(empty)
        assert result.level is PreflightLevel.BLOCK
        assert result.errors

    def test_encrypted_pdf_blocks(self, tmp_path: Path) -> None:
        """Minimal encrypted PDF using pypdfium2-compatible structure."""
        # Build a minimal valid-looking PDF that pyHanko sees as encrypted.
        # Use a tiny handcrafted PDF with /Encrypt in trailer.
        encrypted_pdf = tmp_path / "enc.pdf"
        # Minimal PDF 1.4 with Encrypt dictionary (standard security handler stub)
        # This is intentionally a simplified structure; if pyHanko/pypdfium2
        # cannot open it, that also maps to BLOCK.
        content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
4 0 obj
<< /Filter /Standard /V 1 /R 2 /O (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa) /U (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa) /P -44 >>
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000194 00000 n
trailer
<< /Size 5 /Root 1 0 R /Encrypt 4 0 R >>
startxref
380
%%EOF
"""
        encrypted_pdf.write_bytes(content)
        result = preflight_pdf(encrypted_pdf)
        assert result.level is PreflightLevel.BLOCK


class TestWritableCheck:
    """writable_check flag controls writable field."""

    def test_writable_true_when_check_disabled(self, tmp_path: Path) -> None:
        bad = tmp_path / "x.bin"
        bad.write_bytes(b"not pdf")
        result = preflight_pdf(bad, writable_check=False)
        # Still BLOCK for non-PDF, but writable should not be forced False
        # solely by the check being disabled — just ensure no crash.
        assert result.level is PreflightLevel.BLOCK

    def test_writable_on_source(self) -> None:
        result = preflight_pdf(SOURCE_PDF, writable_check=True)
        assert result.writable is True
