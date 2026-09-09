"""Unit tests for retry policy."""

from __future__ import annotations

from golden_signing.batch.retry import is_retryable_error


def test_transient_retryable() -> None:
    assert is_retryable_error("IO_ERROR") is True
    assert is_retryable_error("TOKEN_ERROR") is True
    assert is_retryable_error("TOKEN_LOST") is True


def test_never_retry_critical() -> None:
    assert is_retryable_error("VERIFY_FAILED") is False
    assert is_retryable_error("WRONG_PIN") is False
    assert is_retryable_error("CERT_EXPIRED") is False
    assert is_retryable_error("PROFILE_INVARIANT") is False
    assert is_retryable_error("SIGN_FAILED") is False


def test_unknown_not_retryable() -> None:
    assert is_retryable_error("SOMETHING_NEW") is False
    assert is_retryable_error(None) is False
    assert is_retryable_error("") is False
