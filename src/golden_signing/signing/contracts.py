"""Signing domain contracts.

UI must not import infrastructure. Infrastructure implements these Protocols.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable


class SignatureMode(StrEnum):
    INVISIBLE = "invisible"
    VISIBLE = "visible"
    ASK = "ask"


class PusProfile(StrEnum):
    PUS_SAFE = "pus-safe"
    MODERN_PADES = "modern-pades"
    CUSTOM = "custom"


class PreflightLevel(StrEnum):
    SAFE = "safe"
    WARN = "warn"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class CertificateInfo:
    subject: str
    issuer: str
    serial: str
    fingerprint_sha256: str
    not_valid_before: str
    not_valid_after: str
    key_algorithm: str
    key_size: int | None = None
    token_label: str | None = None
    backend: str = "unknown"
    has_private_key: bool | None = None
    eku_oids: tuple[str, ...] = ()
    key_usage_digital_signature: bool | None = None


@dataclass(slots=True)
class SigningProfile:
    id: str
    name: str
    certificate_fingerprint_sha256: str
    mode: SignatureMode = SignatureMode.INVISIBLE
    pus_profile: PusProfile = PusProfile.PUS_SAFE
    verify_after_sign: bool = True
    atomic_commit: bool = True
    preserve_original: bool = True
    reason: str | None = None
    location: str | None = None
    contact: str | None = None
    filename_template: str = "{original_name}_signed.pdf"


@dataclass(slots=True)
class PreflightResult:
    level: PreflightLevel
    page_count: int
    encrypted: bool
    existing_signatures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pdf_version: str | None = None
    file_size_bytes: int = 0
    writable: bool = True
    has_acroform: bool = False
    incremental_revisions: int = 0


@dataclass(slots=True)
class SignResult:
    success: bool
    output_path: Path | None = None
    error_code: str | None = None
    message: str = ""
    duration_s: float = 0.0


@dataclass(slots=True)
class VerificationResult:
    cryptographically_valid: bool
    certificate_readable: bool
    document_modified: bool
    details: list[str] = field(default_factory=list)
    error_code: str | None = None


class SigningSession(Protocol):
    def close(self) -> None: ...


@runtime_checkable
class SignerBackend(Protocol):
    def list_certificates(self) -> Sequence[CertificateInfo]: ...

    def sign(self, digest: bytes, algorithm: str) -> bytes: ...

    def open_session(self) -> SigningSession: ...


@runtime_checkable
class PdfSigningEngine(Protocol):
    def preflight(self, input_path: Path, profile: SigningProfile) -> PreflightResult: ...

    def sign(
        self,
        input_path: Path,
        output_path: Path,
        signer: SignerBackend,
        profile: SigningProfile,
    ) -> SignResult: ...

    def verify(self, output_path: Path, profile: SigningProfile) -> VerificationResult: ...
