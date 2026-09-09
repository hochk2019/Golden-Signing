"""Pkcs11Backend unit tests without hardware (T5)."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

from golden_signing.signing.exceptions import TokenError
from golden_signing.token.pkcs11 import Pkcs11Backend, _is_device_removed


def test_missing_library_raises_token_error(tmp_path: Path) -> None:
    backend = Pkcs11Backend(tmp_path / "missing-pkcs11.dll")
    with pytest.raises(TokenError):
        backend.load()
    with pytest.raises(TokenError):
        backend.list_slots()


def test_device_removed_heuristic() -> None:
    assert _is_device_removed(Exception("CKR_DEVICE_REMOVED"))
    assert _is_device_removed(Exception("token not present"))
    assert not _is_device_removed(Exception("bad padding"))


def test_sign_without_session() -> None:
    backend = Pkcs11Backend(Path("C:/Windows/System32/opensc-pkcs11.dll"))
    # Do not load; sign should fail cleanly if session missing after failed load
    with contextlib.suppress(TokenError):
        backend.load()
    with pytest.raises(TokenError):
        backend.sign(b"\x00" * 32, "sha256")
