"""Tests: empty-password PDF preflight + cert label."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.crypto import try_open_encrypted_with_empty_password
from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.signing.contracts import CertificateInfo, PreflightLevel
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.ui.cert_label import common_name_from_subject, short_cert_label

USER_PDF = Path(
    r"D:\Hoc\Data khach hang\ICH CUBE\T09\10 XKTC_COGENT_Inv 202609010\DW20260826-1 FTA CO.pdf"
)
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"


def test_common_name_extraction() -> None:
    subject = (
        "User ID: MST:2300944637, Common Name: CÔNG TY TNHH JAEYOUNG VINA, "
        "State/Province: Tỉnh Bắc Ninh, Country: VN"
    )
    assert "JAEYOUNG" in common_name_from_subject(subject)
    label = short_cert_label(
        CertificateInfo(
            subject=subject,
            issuer="Common Name: E-CA, Organization: THAISONSOFT, Country: VN",
            serial="abc",
            fingerprint_sha256="00" * 32,
            not_valid_before="2024-01-01",
            not_valid_after="2028-07-06 04:09:36+00:00",
            key_algorithm="RSA",
            token_label="ECA Token v1.0",
            backend="pkcs11",
        )
    )
    assert "JAEYOUNG" in label
    assert "ECA Token" in label
    assert "2028-07-06" in label
    assert "User ID" not in label
    assert "State/Province" not in label


def test_plain_fixture_still_safe() -> None:
    pre = preflight_pdf(SOURCE_PDF)
    assert pre.level is PreflightLevel.SAFE
    assert pre.encrypted is False


def test_user_encrypted_pdf_not_blocked_if_empty_password() -> None:
    if not USER_PDF.is_file():
        return  # machine-specific sample
    pre = preflight_pdf(USER_PDF)
    assert pre.encrypted is False, pre.errors
    assert pre.level is not PreflightLevel.BLOCK
    assert pre.page_count >= 1


def test_sign_user_encrypted_pdf_lab(tmp_path: Path) -> None:
    if not USER_PDF.is_file():
        return
    engine = TestCertPdfSigner()
    out = tmp_path / "user_enc_signed.pdf"
    result = engine.sign(USER_PDF, out, profile=None)
    assert result.success is True, result.message
    ver = engine.verify(out, None)
    assert ver.cryptographically_valid is True, ver.details


def test_auth_helper_plain() -> None:
    from pyhanko.pdf_utils.reader import PdfFileReader

    with open(SOURCE_PDF, "rb") as fh:
        r = PdfFileReader(fh, strict=False)
        assert try_open_encrypted_with_empty_password(r) is True
