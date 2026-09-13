"""Batch job model and state machine (spec §5.2, §39)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class JobState(StrEnum):
    DISCOVERED = "DISCOVERED"
    PREFLIGHT = "PREFLIGHT"
    READY = "READY"
    WAITING_TOKEN = "WAITING_TOKEN"
    SIGNING = "SIGNING"
    FINALIZING = "FINALIZING"
    VERIFYING = "VERIFYING"
    COMMITTED = "COMMITTED"
    SUCCESS = "SUCCESS"
    # v1.1 conversion / compression
    CONVERTING = "CONVERTING"
    CONVERTED = "CONVERTED"
    COMPRESSING = "COMPRESSING"
    COMPRESSED = "COMPRESSED"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    COMPRESSION_FAILED = "COMPRESSION_FAILED"
    # existing failures
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    TOKEN_ERROR = "TOKEN_ERROR"
    PIN_CANCELLED = "PIN_CANCELLED"
    SIGN_FAILED = "SIGN_FAILED"
    FINALIZE_FAILED = "FINALIZE_FAILED"
    VERIFY_FAILED = "VERIFY_FAILED"
    OUTPUT_CONFLICT = "OUTPUT_CONFLICT"
    IO_ERROR = "IO_ERROR"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES: frozenset[JobState] = frozenset(
    {
        JobState.SUCCESS,
        JobState.SKIPPED,
        JobState.CANCELLED,
        JobState.PREFLIGHT_FAILED,
        JobState.TOKEN_ERROR,
        JobState.PIN_CANCELLED,
        JobState.SIGN_FAILED,
        JobState.FINALIZE_FAILED,
        JobState.VERIFY_FAILED,
        JobState.OUTPUT_CONFLICT,
        JobState.IO_ERROR,
        JobState.CONVERSION_FAILED,
        JobState.COMPRESSION_FAILED,
    }
)


@dataclass(slots=True)
class SigningJob:
    input_path: Path
    output_path: Path | None = None
    profile_id: str | None = None
    certificate_fingerprint_sha256: str | None = None
    state: JobState = JobState.DISCOVERED
    error_code: str | None = None
    message: str = ""
    attempts: int = 0
    id: str = field(default_factory=lambda: str(uuid4()))
    # v1.1
    document_type: str = ""
    working_pdf: Path | None = None
    compress: bool = False
    source_size: int | None = None
    final_size: int | None = None
    compressed_size: int | None = None

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
