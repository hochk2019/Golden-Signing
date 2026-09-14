"""Process a single SigningJob: convert → preflight → compress? → sign."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from golden_signing.batch.state import JobState, SigningJob
from golden_signing.document.types import DocumentType, detect_document_type
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
    if input_path.suffix.lower() in {".doc", ".docx", ".xls", ".xlsx"}:
        return output_dir / f"{input_path.stem}_signed.pdf"
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
        "CONVERSION_FAILED": JobState.CONVERSION_FAILED,
        "NO_CONVERTER": JobState.CONVERSION_FAILED,
        "OFFICE_COM_ERROR": JobState.CONVERSION_FAILED,
        "COMPRESSION_FAILED": JobState.COMPRESSION_FAILED,
        "SIGNED_PDF": JobState.COMPRESSION_FAILED,
    }
    return mapping.get(code or "", JobState.SIGN_FAILED)


def _workspace_dir() -> Path:
    from golden_signing.storage.app_paths import data_dir

    d = data_dir() / "workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{max(n, 0) // 1024} KB"


def process_one_job(
    job: SigningJob,
    engine: LabSigner,
    profile: SigningProfile,
    *,
    output_dir: Path,
    compress: bool = False,
    compression_profile: object | None = None,
    compress_only: bool = False,
    on_state: Callable[[SigningJob], None] | None = None,
) -> SigningJob:
    """Mutate job in place. Never raises for job errors."""

    def _tick() -> None:
        import contextlib

        if on_state is not None:
            with contextlib.suppress(Exception):
                on_state(job)

    if job.state is JobState.CANCELLED or job.state is JobState.SKIPPED:
        return job
    if job.is_terminal and job.state is not JobState.DISCOVERED:
        return job

    job.attempts += 1
    if not job.input_path.exists():
        job.state = JobState.IO_ERROR
        job.error_code = "IO_ERROR"
        job.message = f"input missing: {job.input_path}"
        return job

    try:
        job.source_size = job.input_path.stat().st_size
    except OSError:
        job.source_size = None

    kind = detect_document_type(job.input_path)
    job.document_type = kind.value
    sign_input = job.input_path

    if kind in (DocumentType.WORD, DocumentType.EXCEL):
        job.state = JobState.CONVERTING
        _tick()
        ws = _workspace_dir()
        pdf_path = ws / f"{job.id}.pdf"
        try:
            from golden_signing.document.office_convert import convert_office_to_pdf

            convert_office_to_pdf(job.input_path, pdf_path, doc_type=kind)
            job.working_pdf = pdf_path
            sign_input = pdf_path
            job.state = JobState.CONVERTED
        except Exception as exc:  # noqa: BLE001
            job.state = JobState.CONVERSION_FAILED
            job.error_code = getattr(exc, "code", "CONVERSION_FAILED")
            job.message = redact(str(exc))
            return job
    elif kind is not DocumentType.PDF:
        job.state = JobState.PREFLIGHT_FAILED
        job.error_code = "PREFLIGHT_FAILED"
        job.message = "Định dạng file không được hỗ trợ"
        return job

    job.state = JobState.PREFLIGHT
    pre = preflight_pdf(sign_input)
    if pre.level is PreflightLevel.BLOCK:
        job.state = JobState.PREFLIGHT_FAILED
        job.error_code = "PREFLIGHT_FAILED"
        job.message = "; ".join(pre.errors) or "preflight blocked"
        return job
    if pre.warnings:
        job.message = "; ".join(pre.warnings)

    if compress or compress_only:
        job.state = JobState.COMPRESSING
        _tick()
        ws = job.working_pdf.parent if job.working_pdf else _workspace_dir()
        cmp_path = ws / f"{job.id}_c.pdf"
        try:
            from golden_signing.compress.engine import compress_pdf, default_profile

            prof = compression_profile or default_profile()
            cresult = compress_pdf(sign_input, cmp_path, prof)  # type: ignore[arg-type]
            if job.working_pdf is None:
                job.working_pdf = sign_input
            sign_input = cmp_path
            job.state = JobState.COMPRESSED
            job.compressed_size = cresult.after_bytes
            job.message = (
                f"{_fmt_size(cresult.before_bytes)} → {_fmt_size(cresult.after_bytes)}"
                f" · {cresult.profile_name}"
            )
            if cresult.note:
                job.message = f"{job.message} · {cresult.note}"
        except Exception as exc:  # noqa: BLE001
            job.state = JobState.COMPRESSION_FAILED
            job.error_code = getattr(exc, "code", "COMPRESSION_FAILED")
            job.message = redact(str(exc))
            return job

        if compress_only:
            out = output_dir / f"{job.input_path.stem}_compressed.pdf"
            try:
                import shutil

                output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sign_input, out)
                job.output_path = out
                job.final_size = out.stat().st_size
                job.state = JobState.SUCCESS
                job.error_code = None
            except OSError as exc:
                job.state = JobState.IO_ERROR
                job.error_code = "IO_ERROR"
                job.message = redact(str(exc))
            return job

    job.state = JobState.READY
    if job.output_path is None:
        job.output_path = default_output_path(job.input_path, output_dir)

    job.state = JobState.SIGNING
    _tick()
    try:
        result = engine.sign(sign_input, job.output_path, profile=profile)
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
        if job.output_path and Path(job.output_path).is_file():
            import contextlib

            with contextlib.suppress(OSError):
                job.final_size = Path(job.output_path).stat().st_size
        return job

    code = getattr(result, "error_code", None) or "SIGN_FAILED"
    job.error_code = code
    job.message = redact(getattr(result, "message", "") or "sign failed")
    job.state = _map_error_to_state(code)
    return job
