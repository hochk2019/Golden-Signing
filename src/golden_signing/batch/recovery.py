"""Crash recovery helpers (spec §8.2)."""

from __future__ import annotations

from collections.abc import Iterable

from golden_signing.batch.state import JobState, SigningJob

__all__ = ["classify_incomplete_jobs"]


def classify_incomplete_jobs(jobs: Iterable[SigningJob]) -> list[SigningJob]:
    """After a crash: jobs stuck in non-terminal in-flight states become failed.

    Never trust an unverified temp output. Jobs still DISCOVERED/READY stay resumable.
    """
    fixed: list[SigningJob] = []
    for job in jobs:
        if job.state in (JobState.SIGNING, JobState.FINALIZING, JobState.VERIFYING, JobState.COMMITTED):
            job.state = JobState.SIGN_FAILED
            job.error_code = "SIGN_FAILED"
            job.message = "interrupted before verified commit; output discarded"
            fixed.append(job)
        elif job.state is JobState.PREFLIGHT:
            job.state = JobState.DISCOVERED
            job.error_code = None
            job.message = "reset after interrupt"
            fixed.append(job)
    return fixed
