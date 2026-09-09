"""Token backend contracts (Phase 2, spec §7.3, TOKEN_COMPATIBILITY).

UI must not import PKCS#11. Session manager serializes crypto per token.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from golden_signing.signing.contracts import CertificateInfo, SigningSession

__all__ = [
    "TokenBackend",
    "TokenSessionState",
    "TokenSlotInfo",
]


class TokenSessionState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    LOGGED_IN = "logged_in"
    TOKEN_LOST = "token_lost"


@dataclass(frozen=True, slots=True)
class TokenSlotInfo:
    slot_id: int
    label: str
    token_present: bool
    token_label: str | None = None
    manufacturer: str | None = None


@runtime_checkable
class TokenBackend(Protocol):
    """Operational surface for a hardware/software token backend."""

    def list_slots(self) -> Sequence[TokenSlotInfo]: ...

    def list_certificates(self) -> Sequence[CertificateInfo]: ...

    def open_session(self) -> SigningSession: ...

    def sign(self, digest: bytes, algorithm: str) -> bytes: ...

    def health_check(self) -> bool: ...
