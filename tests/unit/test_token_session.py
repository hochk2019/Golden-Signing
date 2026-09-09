"""Unit tests for TokenSessionManager (T4, T6)."""

from __future__ import annotations

import hashlib
import threading

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.token.fake import FakeTokenBackend
from golden_signing.token.session import TokenSessionManager, TokenSessionState


def _manager(pin: str | None = "123456") -> tuple[TokenSessionManager, FakeTokenBackend]:
    backend = FakeTokenBackend()
    provider = (lambda: pin) if pin is not None else None
    mgr = TokenSessionManager(backend, pin_provider=provider)
    return mgr, backend


def test_open_auto_login() -> None:
    mgr, backend = _manager()
    mgr.open()
    assert mgr.state is TokenSessionState.LOGGED_IN
    assert backend.logged_in is True


def test_missing_pin_provider() -> None:
    mgr, _ = _manager(pin=None)
    with pytest.raises(TokenError) as ei:
        mgr.open()
    assert getattr(ei.value, "code", "") == "PIN_REQUIRED"


def test_sign_digest_verifies() -> None:
    mgr, backend = _manager()
    digest = hashlib.sha256(b"payload").digest()
    sig = mgr.sign_digest(digest, "sha256")
    backend.public_key().verify(
        sig,
        digest,
        padding.PKCS1v15(),
        Prehashed(hashes.SHA256()),
    )


def test_unplug_then_sign_is_token_lost() -> None:
    mgr, backend = _manager()
    mgr.open()
    backend.simulate_unplug()
    digest = hashlib.sha256(b"p").digest()
    with pytest.raises(TokenLostError):
        mgr.sign_digest(digest)
    assert mgr.state is TokenSessionState.TOKEN_LOST
    with pytest.raises(TokenLostError):
        mgr.sign_digest(digest)


def test_recover_after_replug() -> None:
    mgr, backend = _manager()
    mgr.open()
    backend.simulate_unplug()
    with pytest.raises(TokenLostError):
        mgr.sign_digest(hashlib.sha256(b"a").digest())
    backend.simulate_replug()
    state = mgr.recover()
    assert state is TokenSessionState.LOGGED_IN
    sig = mgr.sign_digest(hashlib.sha256(b"b").digest())
    assert sig


def test_pin_not_retained_on_manager() -> None:
    mgr, _ = _manager()
    mgr.open()
    assert not hasattr(mgr, "_pin")
    assert "_pin" not in mgr.__dict__


def test_concurrent_sign_serialized() -> None:
    mgr, backend = _manager()
    mgr.open()
    digest = hashlib.sha256(b"same").digest()
    results: list[bytes] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            results.append(mgr.sign_digest(digest))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(results) == 8
    assert backend.sign_count == 8


def test_close_resets_state() -> None:
    mgr, _ = _manager()
    mgr.open()
    mgr.close()
    assert mgr.state is TokenSessionState.CLOSED


def test_list_certificates() -> None:
    mgr, _ = _manager()
    certs = mgr.list_certificates()
    assert len(certs) == 1
