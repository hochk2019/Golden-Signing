"""Shared pyHanko signature verification (handles empty-password encryption)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.pdf.crypto import open_pdf_reader
from golden_signing.pdf.integrity import extract_byte_range, validate_byte_range
from golden_signing.signing.contracts import VerificationResult

__all__ = ["verify_signed_pdf"]


def verify_signed_pdf(output_path: Path) -> VerificationResult:
    if not output_path.exists():
        return VerificationResult(
            cryptographically_valid=False,
            certificate_readable=False,
            document_modified=True,
            details=["output missing"],
            error_code="IO_ERROR",
        )

    data = output_path.read_bytes()
    details: list[str] = []
    br = extract_byte_range(data)
    br_ok = br is not None and validate_byte_range(data, br)
    details.append(f"byte_range_valid={br_ok}")

    crypto_ok = False
    cert_ok = False
    reader = None
    try:
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko.sign.validation.pdf_embedded import collect_embedded_signatures

        reader = open_pdf_reader(output_path, strict=False)
        embedded = list(collect_embedded_signatures(reader))
        if not embedded:
            details.append("no embedded signatures found")
        for sig in embedded:
            try:
                result = validate_pdf_signature(sig, skip_diff=True)
                crypto_ok = bool(result.intact and result.valid)
                cert_ok = result.signing_cert is not None
                details.append(
                    f"field={sig.field_name} intact={result.intact} valid={result.valid}"
                )
                if crypto_ok:
                    break
            except Exception as exc:  # noqa: BLE001
                details.append(f"validate error: {exc}")
    except Exception as exc:  # noqa: BLE001
        details.append(f"pyhanko validate unavailable: {exc}")
        crypto_ok = False
        cert_ok = False
    finally:
        fh = getattr(reader, "_gs_fh", None) if reader is not None else None
        if fh is not None and not fh.closed:
            fh.close()

    return VerificationResult(
        cryptographically_valid=crypto_ok and br_ok,
        certificate_readable=cert_ok,
        document_modified=not (crypto_ok and br_ok),
        details=details,
        error_code=None if (crypto_ok and br_ok) else "VERIFY_FAILED",
    )
