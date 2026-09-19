from __future__ import annotations

from pyhanko.sign.signers import Signer

from golden_signing.signing.windows_csp_signer import WindowsCspSigner


def test_windows_csp_signer_is_pyhanko_signer() -> None:
    assert issubclass(WindowsCspSigner, Signer)


def test_windows_csp_signer_dry_run() -> None:
    from asn1crypto import x509
    from cryptography import x509 as cx
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import datetime as dt

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = cx.Name([cx.NameAttribute(NameOID.COMMON_NAME, "TEST CSP")])
    cert = (
        cx.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    der = cert.public_bytes(serialization.Encoding.DER)
    asn = x509.Certificate.load(der)
    s = WindowsCspSigner(asn, "01")
    assert s.signing_cert is not None
    assert s.estimate_raw_signature_size_bytes() == 256
    out = s.sign_raw(b"\x00" * 32, dry_run=True)
    assert out == b"\x00" * 256
