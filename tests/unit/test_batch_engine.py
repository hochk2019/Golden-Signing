"""Batch engine isolation, pause, cancel, retry (T2–T4)."""

from __future__ import annotations

import shutil
from pathlib import Path

from golden_signing.batch.queue import BatchEngine
from golden_signing.batch.recovery import classify_incomplete_jobs
from golden_signing.batch.state import JobState, SigningJob
from golden_signing.batch.worker import process_one_job
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"


def _profile(engine: TestCertPdfSigner):
    return pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)


def test_process_one_success(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    job = SigningJob(input_path=SOURCE_PDF)
    process_one_job(job, engine, _profile(engine), output_dir=tmp_path)
    assert job.state is JobState.SUCCESS
    assert job.output_path is not None and job.output_path.exists()


def test_process_missing_file(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    job = SigningJob(input_path=tmp_path / "nope.pdf")
    process_one_job(job, engine, _profile(engine), output_dir=tmp_path)
    assert job.state is JobState.IO_ERROR
    assert job.error_code == "IO_ERROR"


def test_process_non_pdf_preflight_fail(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    engine = TestCertPdfSigner()
    job = SigningJob(input_path=bad)
    process_one_job(job, engine, _profile(engine), output_dir=tmp_path)
    assert job.state is JobState.PREFLIGHT_FAILED


def test_batch_isolation_one_bad_file(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    out = tmp_path / "out"
    ok1 = tmp_path / "a.pdf"
    bad = tmp_path / "bad.pdf"
    ok2 = tmp_path / "b.pdf"
    shutil.copy(SOURCE_PDF, ok1)
    shutil.copy(SOURCE_PDF, ok2)
    bad.write_bytes(b"garbage")

    batch = BatchEngine(engine, _profile(engine), output_dir=out)
    batch.enqueue_paths([ok1, bad, ok2])
    result = batch.run()
    assert result.success == 2
    assert result.failed == 1
    assert result.all_terminal
    states = [j.state for j in result.jobs]
    assert states[0] is JobState.SUCCESS
    assert states[1] is JobState.PREFLIGHT_FAILED
    assert states[2] is JobState.SUCCESS


def test_cancel_queued(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    paths = []
    for i in range(3):
        p = tmp_path / f"f{i}.pdf"
        shutil.copy(SOURCE_PDF, p)
        paths.append(p)
    batch = BatchEngine(engine, _profile(engine), output_dir=tmp_path / "o")
    jobs = batch.enqueue_paths(paths)
    # cancel before run: all DISCOVERED → CANCELLED
    batch.cancel_queued()
    assert all(j.state is JobState.CANCELLED for j in jobs)
    result = batch.run()
    assert result.cancelled == 3
    assert result.success == 0


def test_pause_then_resume(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    paths = []
    for i in range(3):
        p = tmp_path / f"p{i}.pdf"
        shutil.copy(SOURCE_PDF, p)
        paths.append(p)
    batch = BatchEngine(engine, _profile(engine), output_dir=tmp_path / "o")

    # pause immediately — first run processes nothing if we pause before run...
    # run() clears pause at start; so pause via progress after first job
    seen: list[str] = []

    def on_progress(done: int, total: int, job: SigningJob) -> None:
        seen.append(job.id)
        if done == 1:
            batch.pause()

    batch._on_progress = on_progress  # noqa: SLF001 — test hook
    batch.enqueue_paths(paths)
    r1 = batch.run()
    # after pause mid-run, remaining not processed in same pass
    assert r1.success >= 1
    remaining = [j for j in batch.jobs if not j.is_terminal]
    assert remaining  # at least one left
    r2 = batch.run()  # resume (run clears pause)
    assert r2.success == 3
    assert r2.all_terminal


def test_retry_skips_non_retryable(tmp_path: Path) -> None:
    engine = TestCertPdfSigner()
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"nope")
    batch = BatchEngine(engine, _profile(engine), output_dir=tmp_path / "o")
    batch.enqueue_paths([bad])
    r1 = batch.run()
    assert r1.failed == 1
    r2 = batch.retry_failed()
    assert r2.failed == 1  # PREFLIGHT_FAILED not retried
    assert batch.jobs[0].attempts == 1


def test_recovery_resets_inflight() -> None:
    j1 = SigningJob(input_path=Path("x.pdf"), state=JobState.SIGNING)
    j2 = SigningJob(input_path=Path("y.pdf"), state=JobState.DISCOVERED)
    j3 = SigningJob(input_path=Path("z.pdf"), state=JobState.SUCCESS)
    fixed = classify_incomplete_jobs([j1, j2, j3])
    assert j1.state is JobState.SIGN_FAILED
    assert j2.state is JobState.DISCOVERED
    assert j3.state is JobState.SUCCESS
    assert len(fixed) == 1
