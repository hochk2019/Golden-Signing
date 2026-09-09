"""Unit tests for FakeTokenBackend (T3)."""

from __future__ import annotations

import hashlib

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from golden_signing.signing.exceptions import TokenError, TokenLostError
from golden_signing.token.fake import FakeTokenBackend


def test_list_slots_and_certs() -> None:
    backend = FakeTokenBackend()
    slots = backend.list_slots()
    assert len(slots) == 1
    assert slots[0].token_present is True
    assert slots[0].token_label == "GOLDEN-TEST-TOKEN"
    certs = backend.list_certificates()
    assert len(certs) == 1
    assert certs[0].key_algorithm == "RSA"
    assert len(certs[0].fingerprint_sha256) == 64


def test_sign_requires_login() -> None:
    backend = FakeTokenBackend()
    backend.open_session()
    digest = hashlib.sha256(b"hello").digest()
    with pytest.raises(TokenError):
        backend.sign(digest, "sha256")


def test_sign_after_login() -> None:
    backend = FakeTokenBackend()
    backend.open_session()
    backend.login(backend.pin)
    digest = hashlib.sha256(b"hello").digest()
    sig = backend.sign(digest, "sha256")
    assert isinstance(sig, bytes)
    assert len(sig) > 0
    backend.public_key().verify(sig, digest, padding.PKCS1v15(), Prehashed(hashes.SHA256()))


def test_wrong_pin() -> None:
    backend = FakeTokenBackend()
    backend.open_session()
    with pytest.raises(TokenError) as ei:
        backend.login("000000")
    assert getattr(ei.value, "code", "") == "WRONG_PIN"


def test_unplug_raises_token_lost() -> None:
    backend = FakeTokenBackend()
    backend.open_session()
    backend.login(backend.pin)
    backend.simulate_unplug()
    digest = hashlib.sha256(b"x").digest()
    with pytest.raises(TokenLostError):
        backend.sign(digest, "sha256")
    assert backend.health_check() is False
