"""PDF signing engine — Phase 1 test-certificate path (spec §7, phase-1 S2).

Uses pyHanko. Never overwrites the source. Post-sign verification is mandatory
before SUCCESS (spec §38). No USB token in this module.
"""

from __future__ import annotations

import os
from pathlib import Path

from golden_signing.pdf.integrity import extract_byte_range, sha256_file, validate_byte_range
from golden_signing.signing.contracts import (
    SigningProfile,
    SignResult,
    VerificationResult,
)
from golden_signing.signing.test_certs import (
    certificate_fingerprint_sha256,
    generate_test_certificate,
    to_simple_signer,
)

__all__ = ["TestCertPdfSigner", "sign_with_test_certificate"]


class TestCertPdfSigner:  # noqa: N801 — lab engine, not a pytest test class
    """Lab-only PdfSigningEngine using an ephemeral in-memory certificate."""

    __test__ = False

    def __init__(self) -> None:
        cert, key = generate_test_certificate()
        self._cert = cert
        self._key = key
        self._signer = to_simple_signer(cert, key)
        self.certificate_fingerprint_sha256 = certificate_fingerprint_sha256(cert)

    def preflight(self, input_path: Path, profile: SigningProfile) -> object:
        from golden_signing.pdf.inspection import preflight_pdf

        return preflight_pdf(input_path)

    def sign(
        self,
        input_path: Path,
        output_path: Path,
        signer: object | None = None,
        profile: SigningProfile | None = None,
    ) -> SignResult:
        """Sign a *copy* of input_path to output_path. Source is never modified."""
        import time

        t0 = time.perf_counter()
        if not input_path.exists():
            return SignResult(
                success=False,
                error_code="IO_ERROR",
                message=f"input not found: {input_path}",
                duration_s=time.perf_counter() - t0,
            )
        if input_path.resolve() == output_path.resolve():
            return SignResult(
                success=False,
                error_code="OUTPUT_CONFLICT",
                message="refusing to overwrite source PDF",
                duration_s=time.perf_counter() - t0,
            )

        source_hash_before = sha256_file(input_path)

        try:
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
            from pyhanko.sign import sign_pdf
            from pyhanko.sign.signers import PdfSignatureMetadata

            reason = profile.reason if profile else None
            location = profile.location if profile else None
            meta = PdfSignatureMetadata(
                field_name="GoldenSigning",
                reason=reason,
                location=location,
                md_algorithm="sha256",
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = output_path.with_name(f".{output_path.name}.tmp-sign")
            try:
                with open(input_path, "rb") as inf:
                    writer = IncrementalPdfFileWriter(inf, strict=False)
                    with open(tmp_path, "wb") as outf:
                        sign_pdf(
                            writer,
                            signature_meta=meta,
                            signer=self._signer,
                            output=outf,
                            in_place=False,
                        )
                # Source must be untouched before promote
                if sha256_file(input_path) != source_hash_before:
                    tmp_path.unlink(missing_ok=True)
                    return SignResult(
                        success=False,
                        error_code="IO_ERROR",
                        message="source PDF hash changed during signing",
                        duration_s=time.perf_counter() - t0,
                    )
                os.replace(tmp_path, output_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            output_path.unlink(missing_ok=True)
            return SignResult(
                success=False,
                error_code="SIGN_FAILED",
                message=f"signing failed: {exc}",
                duration_s=time.perf_counter() - t0,
            )

        # Source must be untouched
        if sha256_file(input_path) != source_hash_before:
            output_path.unlink(missing_ok=True)
            return SignResult(
                success=False,
                error_code="IO_ERROR",
                message="source PDF hash changed during signing",
                duration_s=time.perf_counter() - t0,
            )

        # Mandatory post-sign verification (profile.verify_after_sign default True)
        verify = self.verify(output_path, profile)
        if not verify.cryptographically_valid:
            output_path.unlink(missing_ok=True)
            return SignResult(
                success=False,
                error_code="VERIFY_FAILED",
                message="post-sign verification failed; output discarded",
                duration_s=time.perf_counter() - t0,
            )

        # ByteRange integrity
        data = output_path.read_bytes()
        br = extract_byte_range(data)
        if not br or not validate_byte_range(data, br):
            output_path.unlink(missing_ok=True)
            return SignResult(
                success=False,
                error_code="VERIFY_FAILED",
                message="ByteRange invalid after signing; output discarded",
                duration_s=time.perf_counter() - t0,
            )

        return SignResult(
            success=True,
            output_path=output_path,
            message="signed and verified",
            duration_s=time.perf_counter() - t0,
        )

    def verify(self, output_path: Path, profile: SigningProfile | None = None) -> VerificationResult:
        """Cryptographic verification via pyHanko; ByteRange structural check."""
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
        try:
            from pyhanko.pdf_utils.reader import PdfFileReader
            from pyhanko.sign.validation import validate_pdf_signature
            from pyhanko.sign.validation.pdf_embedded import collect_embedded_signatures

            with open(output_path, "rb") as fh:
                reader = PdfFileReader(fh, strict=False)
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
            # Hard-fail: never treat structural /Type/Sig presence as crypto-valid.
            details.append(f"pyhanko validate unavailable: {exc}")
            crypto_ok = False
            cert_ok = False

        document_modified = not (crypto_ok and br_ok)

        return VerificationResult(
            cryptographically_valid=crypto_ok and br_ok,
            certificate_readable=cert_ok,
            document_modified=document_modified,
            details=details,
            error_code=None if (crypto_ok and br_ok) else "VERIFY_FAILED",
        )


def sign_with_test_certificate(
    input_path: Path,
    output_path: Path,
    profile: SigningProfile | None = None,
) -> SignResult:
    """Convenience lab entrypoint."""
    engine = TestCertPdfSigner()
    return engine.sign(input_path, output_path, signer=None, profile=profile)
