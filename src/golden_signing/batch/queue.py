"""Batch queue / engine (spec §5.2, §8). Sequential per-token signing."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from golden_signing.batch.retry import DEFAULT_MAX_ATTEMPTS, is_retryable_error
from golden_signing.batch.state import TERMINAL_STATES, JobState, SigningJob
from golden_signing.batch.worker import LabSigner, process_one_job
from golden_signing.signing.contracts import SigningProfile

__all__ = ["BatchEngine", "BatchResult"]

ProgressCallback = Callable[[int, int, SigningJob], None]


@dataclass(slots=True)
class BatchResult:
    total: int
    success: int
    failed: int
    cancelled: int
    skipped: int
    jobs: list[SigningJob] = field(default_factory=list)

    @property
    def all_terminal(self) -> bool:
        return all(j.is_terminal for j in self.jobs)


class BatchEngine:
    """Drive a list of SigningJobs sequentially with pause/cancel/retry."""

    def __init__(
        self,
        engine: LabSigner,
        profile: SigningProfile,
        *,
        output_dir: Path,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        on_progress: ProgressCallback | None = None,
        compress: bool = False,
        compression_profile: object | None = None,
        compress_only: bool = False,
    ) -> None:
        self._engine = engine
        self._profile = profile
        self._output_dir = Path(output_dir)
        self._max_attempts = max(1, max_attempts)
        self._on_progress = on_progress
        self._compress = compress
        self._compression_profile = compression_profile
        self._compress_only = compress_only
        self._lock = threading.RLock()
        self._paused = False
        self._cancel_queued = False
        self._jobs: list[SigningJob] = []

    @property
    def jobs(self) -> Sequence[SigningJob]:
        return list(self._jobs)

    def enqueue_paths(self, paths: Iterable[Path]) -> list[SigningJob]:
        with self._lock:
            created: list[SigningJob] = []
            for p in paths:
                job = SigningJob(input_path=Path(p))
                self._jobs.append(job)
                created.append(job)
            return created

    def enqueue_jobs(self, jobs: Iterable[SigningJob]) -> None:
        with self._lock:
            self._jobs.extend(jobs)

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def cancel_queued(self) -> None:
        with self._lock:
            self._cancel_queued = True
            for job in self._jobs:
                if job.state in (JobState.DISCOVERED, JobState.READY, JobState.PREFLIGHT):
                    job.state = JobState.CANCELLED
                    job.error_code = "CANCELLED"
                    job.message = "cancelled before start"

    def _should_stop_before_next(self) -> bool:
        with self._lock:
            return self._paused or self._cancel_queued

    def run(self) -> BatchResult:
        """Process non-terminal jobs. Safe to call again after resume()."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        total = len(self._jobs)
        done = 0

        with self._lock:
            self._paused = False
            # keep cancel flag if set via cancel_queued before run
            if not self._cancel_queued:
                self._cancel_queued = False

        for job in list(self._jobs):
            if job.is_terminal:
                done += 1
                continue
            if self._should_stop_before_next():
                # leave remaining non-terminal for later resume
                break
            process_one_job(
                job,
                self._engine,
                self._profile,
                output_dir=self._output_dir,
                compress=self._compress or self._compress_only,
                compression_profile=self._compression_profile,
                compress_only=self._compress_only,
            )
            done += 1
            if self._on_progress is not None:
                self._on_progress(done, total, job)

        # After a completed run pass, clear cancel so a later resume can proceed
        with self._lock:
            if self._cancel_queued and all(j.is_terminal for j in self._jobs):
                self._cancel_queued = False

        return self._summarize()

    def retry_failed(self) -> BatchResult:
        """Retry failed jobs whose error is transient and attempts remain."""
        with self._lock:
            for job in self._jobs:
                if job.state in TERMINAL_STATES and job.state is not JobState.SUCCESS:
                    if job.state is JobState.CANCELLED or job.state is JobState.SKIPPED:
                        continue
                    if job.attempts >= self._max_attempts:
                        continue
                    if not is_retryable_error(job.error_code):
                        continue
                    job.state = JobState.DISCOVERED
                    job.error_code = None
                    job.message = "queued for retry"
        return self.run()

    def _summarize(self) -> BatchResult:
        success = sum(1 for j in self._jobs if j.state is JobState.SUCCESS)
        cancelled = sum(1 for j in self._jobs if j.state is JobState.CANCELLED)
        skipped = sum(1 for j in self._jobs if j.state is JobState.SKIPPED)
        failed = sum(
            1
            for j in self._jobs
            if j.is_terminal
            and j.state not in (JobState.SUCCESS, JobState.CANCELLED, JobState.SKIPPED)
        )
        return BatchResult(
            total=len(self._jobs),
            success=success,
            failed=failed,
            cancelled=cancelled,
            skipped=skipped,
            jobs=list(self._jobs),
        )
