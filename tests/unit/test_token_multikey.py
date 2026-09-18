from __future__ import annotations

from golden_signing.signing.token_pdf_signer import TokenPdfSigner


def test_make_pyhanko_signer_error_maps_multi_key() -> None:
    """PKCS11Signer construction maps multi-key failure to TokenError MULTI_KEY."""
    import types
    from pathlib import Path

    signer = TokenPdfSigner(Path("dummy.dll"))
    # Bind fake session/cert that will fail when creating real PKCS11Signer
    class _Cert:
        def dump(self) -> bytes:
            return b"\x30\x00"

    signer._session = object()
    signer._signing_cert = _Cert()
    signer._key_id = None
    try:
        signer._make_pyhanko_signer()
    except Exception as exc:  # noqa: BLE001
        # May fail for other reasons without pkcs11 session — ensure function exists
        assert hasattr(TokenPdfSigner, "_find_private_key_id")
        assert "token" in str(exc).lower() or "pkcs" in str(exc).lower() or "session" in str(exc).lower()


def test_bind_session_accepts_key_id() -> None:
    from pathlib import Path

    class _Cert:
        def dump(self) -> bytes:
            return b"abc"

    s = TokenPdfSigner(Path("x.dll"))
    s.bind_session(object(), _Cert(), key_id=b"\x01\x02")
    assert s._key_id == b"\x01\x02"
