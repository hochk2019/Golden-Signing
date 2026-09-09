"""PKCS#11 token backend (python-pkcs11). Lab-safe: missing DLL/token never crashes."""

from __future__ import annotations

import contextlib
import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from golden_signing.signing.contracts import CertificateInfo, SigningSession
from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.token.base import TokenSlotInfo

__all__ = ["Pkcs11Backend"]

_DEVICE_REMOVED_MARKERS = (
    "CKR_DEVICE_REMOVED",
    "CKR_DEVICE_ERROR",
    "CKR_SESSION_HANDLE_INVALID",
    "CKR_TOKEN_NOT_PRESENT",
    "DeviceRemoved",
    "Token not present",
)


def _is_device_removed(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return any(m.lower() in text.lower() for m in _DEVICE_REMOVED_MARKERS)


class _Pkcs11Session(SigningSession):
    def __init__(self, backend: Pkcs11Backend) -> None:
        self._backend = backend

    def close(self) -> None:
        self._backend._close_session()


class Pkcs11Backend:
    """TokenBackend over a PKCS#11 shared library.

    Construction does not load the library. Call :meth:`load` explicitly.
    """

    def __init__(
        self,
        library_path: Path,
        *,
        token_label: str | None = None,
        slot_id: int | None = None,
    ) -> None:
        self.library_path = Path(library_path)
        self.token_label = token_label
        self.slot_id = slot_id
        self._lib: Any = None
        self._session: Any = None
        self._pin: str | None = None

    def load(self) -> None:
        if self._lib is not None:
            return
        if not self.library_path.is_file():
            raise TokenError(f"PKCS#11 library not found: {self.library_path}")
        try:
            import pkcs11

            self._lib = pkcs11.lib(str(self.library_path))
        except Exception as exc:  # noqa: BLE001
            raise TokenError(f"failed to load PKCS#11 library: {exc}") from exc

    def _require_lib(self) -> Any:
        if self._lib is None:
            self.load()
        return self._lib

    def list_slots(self) -> Sequence[TokenSlotInfo]:
        lib = self._require_lib()
        try:
            slots = list(lib.get_slots(token_present=False))
        except Exception as exc:  # noqa: BLE001
            if _is_device_removed(exc):
                raise TokenLostError(str(exc)) from exc
            raise TokenError(f"slot enumeration failed: {exc}") from exc

        out: list[TokenSlotInfo] = []
        for slot in slots:
            try:
                info = slot.get_token_info()
                present = bool(getattr(info, "flags", 0)) or True
                # python-pkcs11: token_info.label when present
                label = (info.label or "").strip() or None
                manufacturer = (info.manufacturer_id or "").strip() or None
                slot_desc = (slot.get_slot_info().slot_description or "").strip()
                out.append(
                    TokenSlotInfo(
                        slot_id=int(slot.slot_id),
                        label=slot_desc or f"slot-{slot.slot_id}",
                        token_present=present,
                        token_label=label,
                        manufacturer=manufacturer,
                    )
                )
            except Exception:  # noqa: BLE001
                out.append(
                    TokenSlotInfo(
                        slot_id=int(getattr(slot, "slot_id", -1)),
                        label="unknown",
                        token_present=False,
                    )
                )
        return out

    def _pick_slot(self) -> Any:
        lib = self._require_lib()
        try:
            slots = list(lib.get_slots(token_present=True))
        except Exception as exc:  # noqa: BLE001
            if _is_device_removed(exc):
                raise TokenLostError(str(exc)) from exc
            raise TokenError(f"no slots: {exc}") from exc
        if not slots:
            raise TokenError("no token present in any slot")
        for slot in slots:
            if self.slot_id is not None and int(slot.slot_id) != self.slot_id:
                continue
            if self.token_label:
                try:
                    label = (slot.get_token_info().label or "").strip()
                except Exception:  # noqa: BLE001
                    continue
                if label != self.token_label:
                    continue
            return slot
        raise TokenError("no matching token slot")

    def open_session(self) -> SigningSession:
        try:
            slot = self._pick_slot()
            self._session = slot.open(rw=False)
        except TokenLostError:
            raise
        except Exception as exc:  # noqa: BLE001
            if _is_device_removed(exc):
                raise TokenLostError(str(exc)) from exc
            raise TokenError(f"open session failed: {exc}") from exc
        return _Pkcs11Session(self)

    def _close_session(self) -> None:
        sess = self._session
        self._session = None
        self._pin = None
        if sess is not None:
            with contextlib.suppress(Exception):
                sess.close()

    def login(self, pin: str) -> None:
        if self._session is None:
            raise TokenError("session not open")
        try:
            self._session.login(pin)
            # Drop local PIN reference immediately after login
            self._pin = None
        except Exception as exc:  # noqa: BLE001
            self._pin = None
            if _is_device_removed(exc):
                raise TokenLostError(str(exc)) from exc
            text = str(exc)
            if "PIN" in text.upper() or "AUTH" in text.upper():
                raise TokenError(text, code="WRONG_PIN") from exc
            raise TokenError(f"login failed: {exc}") from exc

    def list_certificates(self) -> Sequence[CertificateInfo]:
        if self._session is None:
            # enumeration may work without login on some tokens; try open ephemeral
            try:
                slot = self._pick_slot()
                session = slot.open(rw=False)
            except Exception as exc:  # noqa: BLE001
                if _is_device_removed(exc):
                    raise TokenLostError(str(exc)) from exc
                raise TokenError(f"cannot open session for cert list: {exc}") from exc
            own = True
        else:
            session = self._session
            own = False
        try:
            import pkcs11
            from asn1crypto import x509 as asn1_x509

            certs: list[CertificateInfo] = []
            for obj in session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE}):
                try:
                    der = bytes(obj[pkcs11.Attribute.VALUE])
                    cert = asn1_x509.Certificate.load(der)
                    token_label = None
                    with contextlib.suppress(Exception):
                        token_label = (session.get_token_info().label or "").strip() or None
                    key_size: int | None = None
                    algo = "unknown"
                    try:
                        pk = cert.public_key
                        algo = pk.algorithm.upper() if hasattr(pk, "algorithm") else "unknown"
                        bit_size = getattr(pk, "byte_size", None)
                        key_size = int(bit_size) * 8 if bit_size else getattr(pk, "bit_size", None)
                    except Exception:  # noqa: BLE001
                        pass
                    certs.append(
                        CertificateInfo(
                            subject=cert.subject.human_friendly,
                            issuer=cert.issuer.human_friendly,
                            serial=format(cert.serial_number, "x"),
                            fingerprint_sha256=hashlib.sha256(der).hexdigest(),
                            not_valid_before=str(cert.not_valid_before),
                            not_valid_after=str(cert.not_valid_after),
                            key_algorithm=algo,
                            key_size=key_size,
                            token_label=token_label,
                            backend="pkcs11",
                        )
                    )
                except Exception:  # noqa: BLE001
                    continue
            return certs
        except TokenLostError:
            raise
        except Exception as exc:  # noqa: BLE001
            if _is_device_removed(exc):
                raise TokenLostError(str(exc)) from exc
            raise TokenError(f"certificate enumeration failed: {exc}") from exc
        finally:
            if own:
                with contextlib.suppress(Exception):
                    session.close()

    def sign(self, digest: bytes, algorithm: str) -> bytes:
        if self._session is None:
            raise TokenError("session not open")
        try:
            import pkcs11

            algo = algorithm.lower().replace("-", "").replace("_", "")
            mechanism = {
                "sha256": pkcs11.Mechanism.SHA256_RSA_PKCS,
                "sha256rsa": pkcs11.Mechanism.SHA256_RSA_PKCS,
                "sha256rsapkcs": pkcs11.Mechanism.SHA256_RSA_PKCS,
                "sha1": pkcs11.Mechanism.SHA1_RSA_PKCS,
                "sha384": pkcs11.Mechanism.SHA384_RSA_PKCS,
                "sha512": pkcs11.Mechanism.SHA512_RSA_PKCS,
            }.get(algo)
            if mechanism is None:
                raise TokenError(f"unsupported algorithm: {algorithm}")

            keys = list(
                self._session.get_objects(
                    {
                        pkcs11.Attribute.CLASS: pkcs11.ObjectClass.PRIVATE_KEY,
                        pkcs11.Attribute.SIGN: True,
                    }
                )
            )
            if not keys:
                raise TokenError("no signing private key on token")
            private_key = keys[0]
            return bytes(private_key.sign(digest, mechanism=mechanism))
        except TokenError:
            raise
        except Exception as exc:  # noqa: BLE001
            if _is_device_removed(exc):
                self._session = None
                raise TokenLostError(str(exc)) from exc
            raise TokenError(f"sign failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            self._require_lib()
            slot = self._pick_slot()
            info = slot.get_token_info()
            return bool(info)
        except Exception:  # noqa: BLE001
            return False
