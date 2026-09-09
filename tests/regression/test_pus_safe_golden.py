"""Golden regression: PUS Safe lab sign preserves source (T3)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.pdf.integrity import extract_byte_range, sha256_file, validate_byte_range
from golden_signing.signing.contracts import PreflightLevel, SignatureMode
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile
from golden_signing.signing.pus_safe import assert_pus_safe_invariants, resolve_signing_settings

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"
SIGNED_PDF = FIXTURES / "ecus_signed.pdf"
SOURCE_SHA256 = "76df3ed717a0077e4def2612005467ba8a21e095ffbe9dc076d14a150ec9b272"
SIGNED_SHA256 = "11921502135884cbdcd35f366dd2ccc7176c1d22843bd1efb4668f412cd8e475"


def test_fixture_hashes_stable() -> None:
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256
    assert sha256_file(SIGNED_PDF) == SIGNED_SHA256


def test_pus_safe_settings_on_golden_sign(tmp_path: Path) -> None:
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256
    engine = TestCertPdfSigner()
    profile = pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)
    settings = resolve_signing_settings(profile)
    assert_pus_safe_invariants(settings)
    assert settings.mode is SignatureMode.INVISIBLE
    assert settings.verify_after_sign is True

    out = tmp_path / "golden_pus_safe.pdf"
    result = engine.sign(SOURCE_PDF, out, profile=profile)
    assert result.success is True, result.message
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256

    ver = engine.verify(out, profile)
    assert ver.cryptographically_valid is True, ver.details

    data = out.read_bytes()
    br = extract_byte_range(data)
    assert br is not None
    assert validate_byte_range(data, br) is True

    pre = preflight_pdf(out)
    assert pre.page_count == 4
    assert pre.level is PreflightLevel.WARN
    assert pre.existing_signatures
