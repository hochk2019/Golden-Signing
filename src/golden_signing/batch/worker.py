"""Process a single SigningJob through preflight → sign (lab engine)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from golden_signing.batch.state import JobState, SigningJob
from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.security.redaction import redact
from golden_signing.signing.contracts import PreflightLevel, SigningProfile
from golden_signing.signing.exceptions import IoError

__all__ = ["LabSigner", "default_output_path", "process_one_job"]


class LabSigner(Protocol):
    """Minimal engine surface used by the batch worker."""

    certificate_fingerprint_sha256: str

    def sign(
        self,
        input_path: Path,
        output_path: Path,
        signer: object | None = None,
        profile: SigningProfile | None = None,
    ) -> object: ...


def default_output_path(input_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{input_path.stem}_signed{input_path.suffix}"


def _map_error_to_state(code: str | None) -> JobState:
    mapping = {
        "PREFLIGHT_FAILED": JobState.PREFLIGHT_FAILED,
        "TOKEN_ERROR": JobState.TOKEN_ERROR,
        "TOKEN_LOST": JobState.TOKEN_ERROR,
        "PIN_CANCELLED": JobState.PIN_CANCELLED,
        "WRONG_PIN": JobState.PIN_CANCELLED,
        "SIGN_FAILED": JobState.SIGN_FAILED,
        "FINALIZE_FAILED": JobState.FINALIZE_FAILED,
        "VERIFY_FAILED": JobState.VERIFY_FAILED,
        "PROFILE_INVARIANT": JobState.SIGN_FAILED,
        "OUTPUT_CONFLICT": JobState.OUTPUT_CONFLICT,
        "IO_ERROR": JobState.IO_ERROR,
    }
    return mapping.get(code or "", JobState.SIGN_FAILED)


def process_one_job(
    job: SigningJob,
    engine: LabSigner,
    profile: SigningProfile,
    *,
    output_dir: Path,
) -> SigningJob:
    """Mutate job in place through terminal or READY-fail states. Never raises for job errors."""
    if job.state is JobState.CANCELLED or job.state is JobState.SKIPPED:
        return job
    if job.is_terminal and job.state is not JobState.DISCOVERED:
        # already done
        return job

    job.state = JobState.PREFLIGHT
    job.attempts += 1

    if not job.input_path.exists():
        job.state = JobState.IO_ERROR
        job.error_code = "IO_ERROR"
        job.message = f"input missing: {job.input_path}"
        return job

    pre = preflight_pdf(job.input_path)
    if pre.level is PreflightLevel.BLOCK:
        job.state = JobState.PREFLIGHT_FAILED
        job.error_code = "PREFLIGHT_FAILED"
        job.message = "; ".join(pre.errors) or "preflight blocked"
        return job
    if pre.warnings:
        job.message = "; ".join(pre.warnings)

    job.state = JobState.READY
    if job.output_path is None:
        job.output_path = default_output_path(job.input_path, output_dir)

    job.state = JobState.SIGNING
    try:
        result = engine.sign(job.input_path, job.output_path, profile=profile)
    except IoError as exc:
        job.state = JobState.IO_ERROR
        job.error_code = exc.code
        job.message = redact(str(exc))
        return job
    except Exception as exc:  # noqa: BLE001
        job.state = JobState.SIGN_FAILED
        job.error_code = "SIGN_FAILED"
        job.message = redact(str(exc))
        return job

    success = getattr(result, "success", False)
    if success:
        job.state = JobState.VERIFYING
        job.state = JobState.COMMITTED
        job.state = JobState.SUCCESS
        job.error_code = None
        out = getattr(result, "output_path", None)
        if out is not None:
            job.output_path = Path(out)
        return job

    code = getattr(result, "error_code", None) or "SIGN_FAILED"
    job.error_code = code
    job.message = redact(getattr(result, "message", "") or "sign failed")
    job.state = _map_error_to_state(code)
    return job
