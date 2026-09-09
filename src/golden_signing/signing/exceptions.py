"""Stable error taxonomy. Codes must remain backward compatible across versions."""

from __future__ import annotations


class GoldenSigningError(Exception):
    code = "GS_ERROR"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.code)
        if code is not None:
            self.code = code
        self.message = message


class PreflightError(GoldenSigningError):
    code = "PREFLIGHT_FAILED"


class TokenError(GoldenSigningError):
    code = "TOKEN_ERROR"


class PinCancelledError(TokenError):
    code = "PIN_CANCELLED"


class TokenLostError(TokenError):
    code = "TOKEN_LOST"


class SignFailedError(GoldenSigningError):
    code = "SIGN_FAILED"


class FinalizeFailedError(GoldenSigningError):
    code = "FINALIZE_FAILED"


class VerifyFailedError(GoldenSigningError):
    code = "VERIFY_FAILED"


class OutputConflictError(GoldenSigningError):
    code = "OUTPUT_CONFLICT"


class IoError(GoldenSigningError):
    code = "IO_ERROR"


class CertificateExpiredError(GoldenSigningError):
    code = "CERT_EXPIRED"


# Never retry blindly
NON_RETRYABLE_CODES: frozenset[str] = frozenset(
    {
        CertificateExpiredError.code,
        VerifyFailedError.code,
        "UNSUPPORTED_PDF",
        "WRONG_PIN",
        PinCancelledError.code,
    }
)
