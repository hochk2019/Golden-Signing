"""Smoke tests that must pass in Phase 0 without Qt, token, or network."""

from __future__ import annotations

from pathlib import Path

import golden_signing
from golden_signing.batch.state import TERMINAL_STATES, JobState, SigningJob
from golden_signing.security.integrity import atomic_write_bytes
from golden_signing.signing import (
    NON_RETRYABLE_CODES,
    CertificateInfo,
    PusProfile,
    SignatureMode,
    SigningProfile,
)


def test_version() -> None:
    assert golden_signing.__version__ == "1.1.9"


def test_signing_job_terminal() -> None:
    job = SigningJob(input_path=Path("a.pdf"))
    assert not job.is_terminal
    job.state = JobState.SUCCESS
    assert job.is_terminal
    assert JobState.SUCCESS in TERMINAL_STATES


def test_atomic_write(tmp_path: Path) -> None:
    target = tmp_path / "out.bin"
    atomic_write_bytes(target, b"hello")
    assert target.read_bytes() == b"hello"


def test_atomic_write_rejects_failed_verify(tmp_path: Path) -> None:
    target = tmp_path / "out.bin"
    try:
        atomic_write_bytes(target, b"hello", verify=lambda p: False)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    assert not target.exists()


def test_profile_defaults() -> None:
    p = SigningProfile(
        id="x",
        name="PUS Safe",
        certificate_fingerprint_sha256="ab" * 32,
        mode=SignatureMode.INVISIBLE,
        pus_profile=PusProfile.PUS_SAFE,
    )
    assert p.verify_after_sign is True
    assert p.preserve_original is True


def test_non_retryable_codes() -> None:
    assert "CERT_EXPIRED" in NON_RETRYABLE_CODES
    assert "VERIFY_FAILED" in NON_RETRYABLE_CODES


def test_certificate_info_frozen() -> None:
    c = CertificateInfo(
        subject="CN=Test",
        issuer="CN=CA",
        serial="01",
        fingerprint_sha256="cd" * 32,
        not_valid_before="2024-01-01",
        not_valid_after="2026-01-01",
        key_algorithm="RSA",
        key_size=2048,
    )
    assert c.backend == "unknown"
