"""In-memory fake token backend for tests (never used in production paths)."""

from __future__ import annotations

import datetime
import threading
from collections.abc import Sequence

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.x509.oid import NameOID

from golden_signing.signing.contracts import CertificateInfo, SigningSession
from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.token.base import TokenSlotInfo

__all__ = ["FakeSigningSession", "FakeTokenBackend"]


class FakeSigningSession(SigningSession):
    def __init__(self, backend: FakeTokenBackend) -> None:
        self._backend = backend
        self.closed = False

    def close(self) -> None:
        self.closed = True
        self._backend._session_open = False


class FakeTokenBackend:
    """Thread-safe fake PKCS#11-like backend with unplug simulation."""

    def __init__(self, *, token_label: str = "GOLDEN-TEST-TOKEN") -> None:
        self._lock = threading.RLock()
        self._token_label = token_label
        self._plugged = True
        self._session_open = False
        self._logged_in = False
        self._pin = "123456"
        self._sign_count = 0
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.datetime.now(datetime.UTC)
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Golden Fake Org"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Golden Fake Signer"),
            ]
        )
        self._cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self._key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .sign(self._key, hashes.SHA256())
        )
        self._fingerprint = self._cert.fingerprint(hashes.SHA256()).hex()

    # --- test controls -------------------------------------------------

    def simulate_unplug(self) -> None:
        with self._lock:
            self._plugged = False

    def simulate_replug(self) -> None:
        with self._lock:
            self._plugged = True
            # dead handles must not be reused
            self._session_open = False
            self._logged_in = False

    @property
    def sign_count(self) -> int:
        return self._sign_count

    @property
    def pin(self) -> str:
        return self._pin

    def verify_pin(self, pin: str) -> bool:
        return pin == self._pin

    def _require_plugged(self) -> None:
        if not self._plugged:
            raise TokenLostError("token removed")

    # --- TokenBackend --------------------------------------------------

    def list_slots(self) -> Sequence[TokenSlotInfo]:
        with self._lock:
            return [
                TokenSlotInfo(
                    slot_id=0,
                    label="FakeSlot0",
                    token_present=self._plugged,
                    token_label=self._token_label if self._plugged else None,
                    manufacturer="GoldenFake",
                )
            ]

    def list_certificates(self) -> Sequence[CertificateInfo]:
        with self._lock:
            self._require_plugged()
            return [
                CertificateInfo(
                    subject=self._cert.subject.rfc4514_string(),
                    issuer=self._cert.issuer.rfc4514_string(),
                    serial=format(self._cert.serial_number, "x"),
                    fingerprint_sha256=self._fingerprint,
                    not_valid_before=self._cert.not_valid_before_utc.isoformat(),
                    not_valid_after=self._cert.not_valid_after_utc.isoformat(),
                    key_algorithm="RSA",
                    key_size=2048,
                    token_label=self._token_label,
                    backend="fake",
                )
            ]

    def open_session(self) -> SigningSession:
        with self._lock:
            self._require_plugged()
            self._session_open = True
            return FakeSigningSession(self)

    def login(self, pin: str) -> None:
        with self._lock:
            self._require_plugged()
            if not self._session_open:
                raise TokenError("session not open")
            if not self.verify_pin(pin):
                raise TokenError("WRONG_PIN", code="WRONG_PIN")
            self._logged_in = True

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    def sign(self, digest: bytes, algorithm: str) -> bytes:
        with self._lock:
            self._require_plugged()
            if not self._session_open or not self._logged_in:
                raise TokenError("not logged in")
            algo = algorithm.lower().replace("-", "").replace("_", "")
            if algo not in {"sha256", "sha256rsa", "sha256rsapkcs"}:
                raise TokenError(f"unsupported algorithm: {algorithm}")
            signature = self._key.sign(digest, padding.PKCS1v15(), Prehashed(hashes.SHA256()))
            self._sign_count += 1
            return signature

    def health_check(self) -> bool:
        with self._lock:
            return self._plugged

    def public_key(self) -> rsa.RSAPublicKey:
        return self._key.public_key()

    def certificate_der(self) -> bytes:
        return self._cert.public_bytes(serialization.Encoding.DER)

    def fingerprint_sha256(self) -> str:
        return self._fingerprint
