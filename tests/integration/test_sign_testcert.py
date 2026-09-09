"""Integration: sign ecus_source.pdf copy with ephemeral test certificate (T6)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.pdf.integrity import extract_byte_range, sha256_file, validate_byte_range
from golden_signing.signing.contracts import PreflightLevel
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"
SOURCE_SHA256 = "76df3ed717a0077e4def2612005467ba8a21e095ffbe9dc076d14a150ec9b272"


def test_sign_source_with_test_cert(tmp_path: Path) -> None:
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256

    engine = TestCertPdfSigner()
    profile = pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)

    out = tmp_path / "ecus_source_signed.pdf"
    result = engine.sign(SOURCE_PDF, out, profile=profile)
    assert result.success is True, result.message
    assert out.exists()
    # Source untouched
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256

    # Output verifies
    ver = engine.verify(out, profile)
    assert ver.cryptographically_valid is True, ver.details
    assert ver.certificate_readable is True

    # Preflight on output: WARN (has signature), 4 pages
    pre = preflight_pdf(out)
    assert pre.page_count == 4
    assert pre.level is PreflightLevel.WARN
    assert pre.has_acroform is True
    assert pre.existing_signatures

    # ByteRange valid
    data = out.read_bytes()
    br = extract_byte_range(data)
    assert br is not None
    assert validate_byte_range(data, br) is True


def test_refuses_overwrite_source(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    result = engine.sign(SOURCE_PDF, SOURCE_PDF, profile=None)
    assert result.success is False
    assert result.error_code == "OUTPUT_CONFLICT"
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256


def test_verify_missing_file(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    ver = engine.verify(tmp_path / "nope.pdf")
    assert ver.cryptographically_valid is False
    assert ver.error_code == "IO_ERROR"
