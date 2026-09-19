"""Token-backed PDF signing via pyHanko PKCS11Signer (real USB token)."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any

from golden_signing.pdf.integrity import sha256_file
from golden_signing.signing.contracts import (
    CertificateInfo,
    SigningProfile,
    SignResult,
    VerificationResult,
)
from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.signing.pus_safe import assert_pus_safe_invariants, resolve_signing_settings

__all__ = ["TokenPdfSigner"]


def _pkcs11_load_message(library_path: Path, exc: Exception) -> str:
    """Human-readable PKCS#11 load failure (bitness / missing file / other)."""
    from golden_signing.token.discovery import pe_machine_label, process_is_64bit

    text = str(exc)
    low = text.lower()
    arch = pe_machine_label(library_path)
    bitness = "64-bit" if process_is_64bit() else "32-bit"
    if "not a valid win32" in low or "193" in low or arch in ("x86", "x64") and arch != (
        "x64" if process_is_64bit() else "x86"
    ):
        return (
            f"Không load được PKCS#11 (sai kiến trúc DLL).\n"
            f"Thư viện: {library_path}\n"
            f"• DLL: {arch} · Golden Sign: {bitness}\n"
            f"• Cài middleware CA bản {'x64' if process_is_64bit() else '32-bit'} "
            f"hoặc trỏ GOLDEN_SIGNING_PKCS11 tới DLL đúng kiến trúc.\n"
            f"Chi tiết: {text}"
        )
    if "not found" in low or "không tìm thấy" in low:
        return f"Không tìm thấy PKCS#11: {library_path}\n{text}"
    return f"cannot load PKCS#11: {library_path}\n{text}"


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
        self._key_id: bytes | None = None
        self._csp_serial: str | None = None
        self.certificate_fingerprint_sha256 = ""
        self.cert_info: object | None = None
        self.text_color: tuple[float, float, float] | None = None
        self.show_background = True
        self.background_opacity = 0.55
        self.show_logo = False
        self.logo_path: Path | None = None
        self.sig_origin: tuple[int, int] | None = None
        self.sig_page = 0
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
            raise TokenError(_pkcs11_load_message(library_path, exc), code="PKCS11_LOAD") from exc
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
                                has_private_key=True,
                                pkcs11_library=str(library_path),
                            )
                        )
                    except Exception:  # noqa: BLE001
                        continue
            finally:
                with contextlib.suppress(Exception):
                    session.close()
        return out

    @staticmethod
    def _find_private_key_id(session: Any, signing_cert: Any) -> bytes | None:
        """Pick CKA_ID of the private key that belongs to signing_cert (CA2 tokens often have 2+ keys)."""
        import pkcs11
        from asn1crypto import x509 as asn1_x509

        try:
            certs = list(
                session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE})
            )
            keys = list(
                session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY})
            )
        except Exception:  # noqa: BLE001
            return None
        if not keys:
            return None

        target_der = None
        try:
            target_der = signing_cert.dump()
        except Exception:  # noqa: BLE001
            target_der = None
        cert_obj_id: bytes | None = None
        cert_modulus = None
        if target_der is not None:
            try:
                cert = asn1_x509.Certificate.load(target_der)
                try:
                    spki = cert["tbs_certificate"]["subject_public_key_info"]
                    if spki.algorithm == "rsa":
                        cert_modulus = int(spki["public_key"].native["modulus"])
                except Exception:  # noqa: BLE001
                    cert_modulus = None
            except Exception:  # noqa: BLE001
                cert_modulus = None

        for obj in certs:
            try:
                der = bytes(obj[pkcs11.Attribute.VALUE])
                if target_der is not None and der == target_der:
                    try:
                        cert_obj_id = bytes(obj[pkcs11.Attribute.ID])
                    except Exception:  # noqa: BLE001
                        cert_obj_id = None
                    break
            except Exception:  # noqa: BLE001
                continue

        # 1) Same CKA_ID as certificate object
        if cert_obj_id is not None:
            for k in keys:
                try:
                    kid = bytes(k[pkcs11.Attribute.ID])
                except Exception:  # noqa: BLE001
                    continue
                if kid == cert_obj_id:
                    return kid

        # 2) RSA modulus match with cert public key
        if cert_modulus is not None:
            for k in keys:
                try:
                    mod = k[pkcs11.Attribute.MODULUS]
                    if int.from_bytes(bytes(mod), "big") == cert_modulus:
                        kid = bytes(k[pkcs11.Attribute.ID])
                        return kid
                except Exception:  # noqa: BLE001
                    continue

        # 3) Exactly one private key
        if len(keys) == 1:
            try:
                return bytes(keys[0][pkcs11.Attribute.ID])
            except Exception:  # noqa: BLE001
                return None
        return None

    @staticmethod
    def open_session_with_pin(
        library_path: Path,
        pin: str,
        *,
        cert_label: str | None = None,
        cert_serial: str | None = None,
    ) -> tuple[Any, Any, bytes | None]:
        """Return (pkcs11_session, asn1_certificate, private_key_id). PIN not retained after return."""
        import hashlib

        import pkcs11
        from asn1crypto import x509 as asn1_x509

        try:
            lib = pkcs11.lib(str(library_path))
            slots = list(lib.get_slots(token_present=True))
        except Exception as exc:  # noqa: BLE001
            raise TokenError(_pkcs11_load_message(library_path, exc), code="PKCS11_LOAD") from exc
        if not slots:
            raise TokenError("no token present")

        last_err: Exception | None = None
        for slot in slots:
            try:
                token = slot.get_token()
                session = token.open(
                    rw=False,
                    user_pin=pin,
                    user_type=pkcs11.UserType.USER,
                )
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                name = type(exc).__name__.upper()
                text = str(exc).upper()
                if (
                    "PIN" in name
                    or "AUTH" in name
                    or "PIN" in text
                    or "AUTH" in text
                    or "LOGIN" in text
                ):
                    raise TokenError(
                        "PIN không đúng hoặc bị hủy",
                        code="WRONG_PIN",
                    ) from exc
                if "REMOVED" in name or "DEVICE" in name or "REMOVED" in text:
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
                    cert = asn1_x509.Certificate.load(der)
                    serial_hex = format(cert.serial_number, "x")
                    want = (cert_serial or "").strip()
                    if not want:
                        if len(certs) > 1:
                            last_err = TokenError(
                                "Token có nhiều CKS nhưng thiếu serial để chọn — không mở session mặc định.",
                                code="CERT_SERIAL_REQUIRED",
                            )
                            session.close()
                            continue
                        chosen = cert
                        chosen_der = der
                        break
                    if serial_hex.lower() == want.lower().lstrip("0") or serial_hex.lower() == want.lower():
                        chosen = cert
                        chosen_der = der
                        break
                    if cert_label is not None:
                        try:
                            clabel = bytes(obj[pkcs11.Attribute.LABEL]).decode("utf-8", "replace")
                        except Exception:  # noqa: BLE001
                            clabel = ""
                        if cert_label == clabel or cert_label in clabel:
                            chosen = cert
                            chosen_der = der
                            break
                if chosen is None:
                    session.close()
                    serials = []
                    for obj in certs:
                        try:
                            d = bytes(obj[pkcs11.Attribute.VALUE])
                            serials.append(format(asn1_x509.Certificate.load(d).serial_number, "x"))
                        except Exception:  # noqa: BLE001
                            continue
                    last_err = TokenError(
                        f"Token không có CKS khớp serial đã chọn.\n"
                        f"• Serial yêu cầu: {cert_serial or '(bất kỳ)'}\n"
                        f"• Serial trên token: {', '.join(serials) if serials else '(trống)'}\n"
                        f"• Library: {library_path}",
                        code="CERT_NOT_ON_TOKEN",
                    )
                    continue
                _ = hashlib.sha256(chosen_der or b"").hexdigest()
                key_id = TokenPdfSigner._find_private_key_id(session, chosen)
                return session, chosen, key_id
            except TokenError:
                session.close()
                raise
            except Exception as exc:  # noqa: BLE001
                with contextlib.suppress(Exception):
                    session.close()
                last_err = exc
                continue

        if "not a valid win32" in str(last_err).lower() or getattr(last_err, "code", "") == "PKCS11_LOAD":
            raise TokenError(str(last_err), code="PKCS11_LOAD") from last_err
        if getattr(last_err, "code", "") == "CERT_NOT_ON_TOKEN":
            raise TokenError(str(last_err), code="CERT_NOT_ON_TOKEN") from last_err
        raise TokenError(f"token login/list failed: {last_err}", code="TOKEN_LOGIN") from last_err

    def close_session(self) -> None:
        """Best-effort close PKCS#11 session (multi-token switch / Reset CKS)."""
        session = self._session
        self._session = None
        if session is None:
            return
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def serial_on_library(library_path: Path, serial: str) -> bool:
        """True if token at library_path currently exposes this cert serial."""
        if not serial:
            return False
        try:
            certs = TokenPdfSigner.list_certificates(library_path)
        except Exception:  # noqa: BLE001
            return False
        target = serial.lower().lstrip("0")
        return any(str(c.serial).lower().lstrip("0") == target for c in certs)

    def bind_session(
        self,
        session: Any,
        signing_cert: Any,
        key_id: bytes | None = None,
    ) -> None:
        import hashlib

        self._session = session
        self._signing_cert = signing_cert
        self._key_id = key_id
        self.cert_info: object | None = None
        if signing_cert is not None:
            self.certificate_fingerprint_sha256 = hashlib.sha256(signing_cert.dump()).hexdigest()

    def bind_csp(self, signing_cert: Any, serial: str) -> None:
        """Bind Windows store cert (CSP/CNG private key) — no PKCS#11 session."""
        import hashlib

        self._session = "windows-csp"
        self._signing_cert = signing_cert
        self._csp_serial = serial
        self._key_id = None
        self.cert_info = None
        if signing_cert is not None:
            self.certificate_fingerprint_sha256 = hashlib.sha256(signing_cert.dump()).hexdigest()

    def _make_pyhanko_signer(self) -> Any:
        if self._csp_serial:
            from golden_signing.signing.windows_csp_signer import WindowsCspSigner

            cert = self._signing_cert
            if cert is None:
                raise TokenError("CSP signer chưa có certificate", code="CSP_CERT_MISSING")
            return WindowsCspSigner(cert, self._csp_serial)
        if self._session is None or self._signing_cert is None:
            raise TokenError("token session not bound; call open_session_with_pin + bind_session")
        from pyhanko.sign.pkcs11 import PKCS11Signer

        kwargs: dict[str, Any] = {"signing_cert": self._signing_cert}
        if self._key_id:
            kwargs["key_id"] = self._key_id
        try:
            return PKCS11Signer(self._session, **kwargs)
        except Exception as exc:  # noqa: BLE001
            text = str(exc)
            if "more than one private key" in text.lower():
                # Try every private key CKA_ID on the session — do NOT drop key_id
                try:
                    import pkcs11

                    keys = list(
                        self._session.get_objects(
                            {pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY}
                        )
                    )
                    tried: list[str] = []
                    for k in keys:
                        try:
                            kid = bytes(k[pkcs11.Attribute.ID])
                        except Exception:  # noqa: BLE001
                            continue
                        tried.append(kid.hex()[:16])
                        try:
                            return PKCS11Signer(
                                self._session, signing_cert=self._signing_cert, key_id=kid
                            )
                        except Exception:  # noqa: BLE001
                            continue
                    raise TokenError(
                        "Token có nhiều private key — đã thử các key "
                        f"({', '.join(tried) if tried else 'n/a'}) vẫn lỗi.\n"
                        "Chọn đúng CKS trên token hoặc dùng middleware/token chỉ có 1 key ký.",
                        code="MULTI_KEY",
                    ) from exc
                except TokenError:
                    raise
                except Exception as inner:  # noqa: BLE001
                    raise TokenError(
                        f"token sign failed: Found more than one private key ({inner})",
                        code="MULTI_KEY",
                    ) from exc
            raise TokenError(f"token sign failed: {text}", code="SIGN_FAILED") from exc

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
            from golden_signing.signing.pyhanko_sign import pyhanko_sign_file

            pyhanko_sign_file(
                input_path=input_path,
                output_path=output_path,
                pyhanko_signer=py_signer,
                profile=profile,
                signer_display=None,
                cert_info=self.cert_info,
                text_color=self.text_color,
                show_background=self.show_background,
                background_opacity=getattr(self, "background_opacity", 0.55),
                show_logo=self.show_logo,
                logo_path=self.logo_path,
                origin=self.sig_origin,
                page=self.sig_page,
            )
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
            text = str(exc)
            low = text.lower()
            if "more than one private key" in low:
                code = "MULTI_KEY"
                message = (
                    "token sign failed: Found more than one private key.\n"
                    "Token CA2 có nhiều private key — Golden Sign đã chọn key khớp CKS; "
                    "nếu vẫn lỗi hãy Quét lại token và chọn đúng chứng thư."
                )
            elif "REMOVED" in text.upper() or "DEVICE" in text.upper():
                code = "TOKEN_LOST"
                message = f"token sign failed: {exc}"
            else:
                code = "SIGN_FAILED"
                message = f"token sign failed: {exc}"
            return SignResult(
                success=False,
                error_code=code,
                message=message,
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
        from golden_signing.signing.verify_pdf import verify_signed_pdf

        return verify_signed_pdf(output_path)
