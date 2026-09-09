"""Ephemeral RSA test certificate generation — LAB ONLY.

Never persist private key material to the repository, logs, or any durable
store. The private key returned here lives only in process memory and must be
discarded after the lab signing run. No USB token / PKCS#11 involvement.
"""

from __future__ import annotations

import datetime
import ipaddress
import uuid
from typing import TYPE_CHECKING, Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

if TYPE_CHECKING:
    from pyhanko.sign.signers.pdf_cms import SimpleSigner

DEFAULT_COMMON_NAME = "Golden Signing Test"
DEFAULT_KEY_SIZE = 2048
DEFAULT_VALID_DAYS = 30
BACKDATE_DAYS = 1

_TEST_MARKER = "Golden Signing Test"


def generate_test_certificate(
    *,
    common_name: str = DEFAULT_COMMON_NAME,
    key_size: int = DEFAULT_KEY_SIZE,
    valid_days: int = DEFAULT_VALID_DAYS,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """Generate a short-lived self-signed RSA certificate entirely in memory.

    Returns
    -------
    (certificate, private_key)
        ``certificate`` is a ``cryptography.x509.Certificate``; ``private_key``
        is an ``RSAPrivateKey``. Convert with :func:`to_simple_signer` for
        pyHanko (in-memory DER; no files).

    Notes
    -----
    - Lab only. The private key is ephemeral and must not be written to disk
      under any repository path, nor logged.
    - Validity window: now-1day .. now+valid_days (default +30 days).
    """
    if key_size < 2048:
        raise ValueError("key_size must be >= 2048 for RSA test certificates")
    if not common_name or not common_name.strip():
        raise ValueError("common_name must be non-empty")
    if _TEST_MARKER not in common_name:
        # Acceptance requires the CN to identify this as a test certificate.
        common_name = f"{common_name} ({_TEST_MARKER})"

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    now = datetime.datetime.now(datetime.UTC)
    not_before = now - datetime.timedelta(days=BACKDATE_DAYS)
    not_after = now + datetime.timedelta(days=valid_days)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "HK"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Golden Signing Lab"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(f"test-{uuid.uuid4().hex[:12]}.golden-signing.lab"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CODE_SIGNING]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    return cert, private_key


def certificate_fingerprint_sha256(cert: x509.Certificate) -> str:
    """SHA-256 fingerprint of the certificate DER, lowercase hex, no colons."""
    digest = cert.fingerprint(hashes.SHA256())
    return digest.hex()


def private_key_pem_in_memory(key: rsa.RSAPrivateKey) -> bytes:
    """Serialize a private key to PEM bytes in memory (never write to disk)."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def to_simple_signer(cert: x509.Certificate, key: rsa.RSAPrivateKey) -> SimpleSigner:
    """Build a pyHanko ``SimpleSigner`` from in-memory cryptography objects.

    DER reload stays in memory; nothing is written to disk. Lab path for T6.
    """
    from asn1crypto import keys as asn1_keys
    from asn1crypto import x509 as asn1_x509
    from pyhanko.sign.signers.pdf_cms import (  # type: ignore[attr-defined]
        SimpleCertificateStore,
        SimpleSigner,
    )

    asn1_cert = asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
    asn1_key = asn1_keys.PrivateKeyInfo.load(
        key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    store: Any = SimpleCertificateStore.from_certs([asn1_cert])  # type: ignore[no-untyped-call]
    return SimpleSigner(signing_cert=asn1_cert, signing_key=asn1_key, cert_registry=store)
