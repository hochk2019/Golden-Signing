"""Token-backed PDF signing via pyHanko PKCS11Signer (real USB token)."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any

from golden_signing.pdf.integrity import extract_byte_range, sha256_file, validate_byte_range
from golden_signing.signing.contracts import (
    CertificateInfo,
    SigningProfile,
    SignResult,
    VerificationResult,
)
from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.signing.pus_safe import assert_pus_safe_invariants, resolve_signing_settings

__all__ = ["TokenPdfSigner"]


class TokenPdfSigner:
    """Sign PDFs with a PKCS#11 USB token. PIN never stored on the instance."""

    def __init__(
        self,
        library_path: Path,
        *,
        cert_label: str | None = None,
        signing_cert: Any | None = None,
        session: Any | None = None,
    ) -> None:
        self.library_path = Path(library_path)
        self._cert_label = cert_label
        self._signing_cert = signing_cert
        self._session = session
        self.certificate_fingerprint_sha256 = ""
        if signing_cert is not None:
            import hashlib

            self.certificate_fingerprint_sha256 = hashlib.sha256(signing_cert.dump()).hexdigest()

    @staticmethod
    def list_certificates(library_path: Path) -> list[CertificateInfo]:
        """Enumerate certs on the token without PIN when the vendor allows it."""
        import pkcs11
        from asn1crypto import x509 as asn1_x509

        if not library_path.is_file():
            raise TokenError(f"PKCS#11 library not found: {library_path}")
        try:
            lib = pkcs11.lib(str(library_path))
            slots = list(lib.get_slots(token_present=True))
        except Exception as exc:  # noqa: BLE001
            raise TokenError(f"cannot load PKCS#11: {exc}") from exc
        if not slots:
            raise TokenError("no token present")

        out: list[CertificateInfo] = []
        for slot in slots:
            try:
                token = slot.get_token()
                label = (token.label or "").strip() or None
                session = token.open()
            except Exception as exc:  # noqa: BLE001
                raise TokenError(f"open token session failed: {exc}") from exc
            try:
                certs = list(
                    session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE})
                )
                for obj in certs:
                    try:
                        der = bytes(obj[pkcs11.Attribute.VALUE])
                        cert = asn1_x509.Certificate.load(der)
                        out.append(
                            CertificateInfo(
                                subject=cert.subject.human_friendly,
                                issuer=cert.issuer.human_friendly,
                                serial=format(cert.serial_number, "x"),
                                fingerprint_sha256=__import__("hashlib").sha256(der).hexdigest(),
                                not_valid_before=str(cert.not_valid_before),
                                not_valid_after=str(cert.not_valid_after),
                                key_algorithm="RSA",
                                key_size=None,
                                token_label=label,
                                backend="pkcs11",
                            )
                        )
                    except Exception:  # noqa: BLE001
                        continue
            finally:
                with contextlib.suppress(Exception):
                    session.close()
        return out

    @staticmethod
    def open_session_with_pin(
        library_path: Path,
        pin: str,
        *,
        cert_label: str | None = None,
    ) -> tuple[Any, Any]:
        """Return (pkcs11_session, asn1_certificate). PIN not retained after return."""
        import hashlib

        import pkcs11
        from asn1crypto import x509 as asn1_x509

        try:
            lib = pkcs11.lib(str(library_path))
            slots = list(lib.get_slots(token_present=True))
        except Exception as exc:  # noqa: BLE001
            raise TokenError(f"cannot load PKCS#11: {exc}") from exc
        if not slots:
            raise TokenError("no token present")

        last_err: Exception | None = None
        for slot in slots:
            try:
                token = slot.get_token()
                session = token.open()
                session.login(pin)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                text = str(exc).upper()
                if "PIN" in text or "AUTH" in text or "LOGIN" in text:
                    raise TokenError("PIN không đúng hoặc bị hủy", code="WRONG_PIN") from exc
                if "REMOVED" in text or "DEVICE" in text:
                    raise TokenLostError(str(exc)) from exc
                continue

            try:
                certs = list(
                    session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE})
                )
                chosen = None
                chosen_der: bytes | None = None
                for obj in certs:
                    der = bytes(obj[pkcs11.Attribute.VALUE])
                    try:
                        clabel = bytes(obj[pkcs11.Attribute.LABEL]).decode("utf-8", "replace")
                    except Exception:  # noqa: BLE001
                        clabel = ""
                    if cert_label is None or cert_label == clabel or cert_label in clabel:
                        chosen = asn1_x509.Certificate.load(der)
                        chosen_der = der
                        break
                if chosen is None:
                    session.close()
                    last_err = TokenError("no matching certificate on token")
                    continue
                _ = hashlib.sha256(chosen_der or b"").hexdigest()
                return session, chosen
            except TokenError:
                session.close()
                raise
            except Exception as exc:  # noqa: BLE001
                with contextlib.suppress(Exception):
                    session.close()
                last_err = exc
                continue

        raise TokenError(f"token login/list failed: {last_err}")

    def bind_session(self, session: Any, signing_cert: Any) -> None:
        import hashlib

        self._session = session
        self._signing_cert = signing_cert
        self.certificate_fingerprint_sha256 = hashlib.sha256(signing_cert.dump()).hexdigest()

    def _make_pyhanko_signer(self) -> Any:
        if self._session is None or self._signing_cert is None:
            raise TokenError("token session not bound; call open_session_with_pin + bind_session")
        from pyhanko.sign.pkcs11 import PKCS11Signer

        return PKCS11Signer(self._session, signing_cert=self._signing_cert)

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

        settings = None
        if profile is not None:
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

        source_hash_before = sha256_file(input_path)
        try:
            py_signer = self._make_pyhanko_signer()
        except TokenError as exc:
            return SignResult(
                success=False,
                error_code=exc.code,
                message=str(exc),
                duration_s=time.perf_counter() - t0,
            )

        try:
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
            from pyhanko.sign import sign_pdf
            from pyhanko.sign.signers import PdfSignatureMetadata

            reason = settings.reason if settings else None
            location = settings.location if settings else None
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
                            signer=py_signer,
                            output=outf,
                            in_place=False,
                        )
                if sha256_file(input_path) != source_hash_before:
                    tmp_path.unlink(missing_ok=True)
                    return SignResult(
                        success=False,
                        error_code="IO_ERROR",
                        message="source PDF hash changed during signing",
                        duration_s=time.perf_counter() - t0,
                    )
                import os

                os.replace(tmp_path, output_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            output_path.unlink(missing_ok=True)
            text = str(exc)
            code = "TOKEN_LOST" if "REMOVED" in text.upper() or "DEVICE" in text.upper() else "SIGN_FAILED"
            return SignResult(
                success=False,
                error_code=code,
                message=f"token sign failed: {exc}",
                duration_s=time.perf_counter() - t0,
            )

        verify = self.verify(output_path, profile)
        if not verify.cryptographically_valid:
            output_path.unlink(missing_ok=True)
            return SignResult(
                success=False,
                error_code="VERIFY_FAILED",
                message="post-sign verification failed; output discarded",
                duration_s=time.perf_counter() - t0,
            )
        return SignResult(
            success=True,
            output_path=output_path,
            message="signed with USB token and verified",
            duration_s=time.perf_counter() - t0,
        )

    def verify(self, output_path: Path, profile: SigningProfile | None = None) -> VerificationResult:
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
            details.append(f"pyhanko validate unavailable: {exc}")
            crypto_ok = False
            cert_ok = False

        return VerificationResult(
            cryptographically_valid=crypto_ok and br_ok,
            certificate_readable=cert_ok,
            document_modified=not (crypto_ok and br_ok),
            details=details,
            error_code=None if (crypto_ok and br_ok) else "VERIFY_FAILED",
        )
