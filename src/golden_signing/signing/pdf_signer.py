"""PDF signing engine — Phase 1 test-certificate path (spec §7, phase-1 S2).

Uses pyHanko. Never overwrites the source. Post-sign verification is mandatory
before SUCCESS (spec §38). No USB token in this module.
"""

from __future__ import annotations

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
        self.cert_info: object | None = None

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

        settings = None
        if profile is not None:
            from golden_signing.signing.pus_safe import (
                assert_pus_safe_invariants,
                resolve_signing_settings,
            )

            settings = resolve_signing_settings(profile)
            try:
                assert_pus_safe_invariants(settings)
            except Exception as exc:  # noqa: BLE001
                return SignResult(
                    success=False,
                    error_code="PROFILE_INVARIANT",
                    message=str(exc),
                    duration_s=time.perf_counter() - t0,
                )

        try:
            from golden_signing.signing.pyhanko_sign import pyhanko_sign_file

            pyhanko_sign_file(
                input_path=input_path,
                output_path=output_path,
                pyhanko_signer=self._signer,
                profile=profile,
                signer_display="Golden Signing Lab",
                cert_info=self.cert_info,
            )
            # Source must be untouched before promote
            if sha256_file(input_path) != source_hash_before:
                output_path.unlink(missing_ok=True)
                return SignResult(
                    success=False,
                    error_code="IO_ERROR",
                    message="source PDF hash changed during signing",
                    duration_s=time.perf_counter() - t0,
                )
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
        from golden_signing.signing.verify_pdf import verify_signed_pdf

        return verify_signed_pdf(output_path)


def sign_with_test_certificate(
    input_path: Path,
    output_path: Path,
    profile: SigningProfile | None = None,
) -> SignResult:
    """Convenience lab entrypoint."""
    engine = TestCertPdfSigner()
    return engine.sign(input_path, output_path, signer=None, profile=profile)
