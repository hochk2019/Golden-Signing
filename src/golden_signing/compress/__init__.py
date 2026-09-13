"""PDF compression package (v1.1)."""

from golden_signing.compress.engine import (
    CompressionError,
    CompressionProfile,
    CompressionResult,
    CompressionTier,
    compress_pdf,
    default_profile,
    has_signature,
    save_profile,
)

__all__ = [
    "CompressionError",
    "CompressionProfile",
    "CompressionResult",
    "CompressionTier",
    "compress_pdf",
    "default_profile",
    "has_signature",
    "save_profile",
]
