"""Retry policy (spec §8.3). Transient only — never blind retry."""

from __future__ import annotations

from golden_signing.signing.exceptions import NON_RETRYABLE_CODES

__all__ = ["DEFAULT_MAX_ATTEMPTS", "NON_RETRYABLE_EXTRA", "is_retryable_error"]

DEFAULT_MAX_ATTEMPTS = 3

# Extra codes beyond exceptions.NON_RETRYABLE_CODES
NON_RETRYABLE_EXTRA: frozenset[str] = frozenset(
    {
        "VERIFY_FAILED",
        "PROFILE_INVARIANT",
        "WRONG_PIN",
        "PIN_CANCELLED",
        "UNSUPPORTED_PDF",
        "CERT_EXPIRED",
    }
)

# Spec §8.3: file lock, token reconnect, temporary I/O, timestamp network timeout
_RETRYABLE: frozenset[str] = frozenset(
    {
        "IO_ERROR",
        "TOKEN_ERROR",
        "TOKEN_LOST",
        "TEMPORARY_FAILURE",
        "FILE_LOCKED",
        "TIMESTAMP_TIMEOUT",
    }
)


def is_retryable_error(code: str | None) -> bool:
    if not code:
        return False
    c = code.upper()
    if c in NON_RETRYABLE_CODES or c in NON_RETRYABLE_EXTRA:
        return False
    # Unknown codes are not auto-retried (conservative).
    return c in _RETRYABLE
