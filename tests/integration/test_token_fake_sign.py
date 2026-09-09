"""Integration: manager + fake backend sign digest (T6)."""

from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from golden_signing.token.fake import FakeTokenBackend
from golden_signing.token.session import TokenSessionManager, TokenSessionState


def test_end_to_end_fake_token_sign() -> None:
    backend = FakeTokenBackend(token_label="VN-CA-LAB")
    mgr = TokenSessionManager(backend, pin_provider=lambda: "123456")
    mgr.open()
    assert mgr.state is TokenSessionState.LOGGED_IN

    certs = mgr.list_certificates()
    assert certs[0].token_label == "VN-CA-LAB"

    digest = hashlib.sha256(b"golden-signing-phase2").digest()
    signature = mgr.sign_digest(digest, "sha256")
    backend.public_key().verify(
        signature,
        digest,
        padding.PKCS1v15(),
        Prehashed(hashes.SHA256()),
    )

    # Unplug mid-batch must not crash the process
    backend.simulate_unplug()
    try:
        mgr.sign_digest(hashlib.sha256(b"next").digest())
        raise AssertionError("expected TokenLostError")
    except Exception as exc:  # noqa: BLE001
        assert type(exc).__name__ == "TokenLostError"

    backend.simulate_replug()
    assert mgr.recover() is TokenSessionState.LOGGED_IN
    assert mgr.sign_digest(hashlib.sha256(b"after-replug").digest())
    mgr.close()
