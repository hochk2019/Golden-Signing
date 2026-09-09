---
feature: phase-4-batch-engine
status: delivered
updated: 2026-09-09
branch: main
commits: 19d7de7..12d6d5a # Phase 4 delivery
---

# Phase 4 — Batch Engine

## Report

**What was built** — `batch/retry.py` (transient-only policy), `batch/worker.py` (preflight → lab sign, error→state map), `batch/queue.py` (`BatchEngine` enqueue/run/pause/resume/cancel_queued/retry_failed + progress callback), `batch/recovery.py` (interrupted in-flight jobs fail safe). Integration: 10 PDFs with one corrupt → 9 SUCCESS / 1 PREFLIGHT_FAILED; source fixture hash unchanged.

**Verification** — full `pytest -q` exit 0; 12 batch tests; mypy/ruff batch clean.

**Journey log**
1. USB token deferred by user — lab `TestCertPdfSigner` is the batch backend.
2. `run()` clears pause at start so resume = call `run()` again.
3. Unknown error codes are not auto-retried (conservative).
4. JobState moved to `StrEnum` for Python 3.13 lint cleanliness.

## [S1] Problem

Golden Signing must sign many PDFs without one bad file killing the batch (spec §5.2, §8, §30 Phase 4). Phase 1–3 only sign a single file. Need a job queue with the existing state machine, sequential per-token signing, pause/resume/cancel, retry only for transient errors, atomic outputs, and recovery rules after crash.

USB token hardware is **out of scope this session** (user asleep; device not available). Lab engine (`TestCertPdfSigner`) is the signing backend for tests.

## [S2] Design

### Workspace

Continue on `main`. Commit only, **no push**. User unavailable — proceed without Grill.

### Modules

```
src/golden_signing/batch/
  state.py      # existing JobState / SigningJob (extend only if needed)
  retry.py      # is_retryable_error, default max attempts
  queue.py      # BatchEngine: enqueue, run, pause, resume, cancel, retry_failed
  worker.py     # process_one_job: preflight → sign → verify path using engine
  recovery.py   # classify_incomplete_jobs after crash (no temp reuse)
```

### Job lifecycle (lab)

```
DISCOVERED → PREFLIGHT → READY → SIGNING → VERIFYING → COMMITTED → SUCCESS
                         ↘ PREFLIGHT_FAILED | SIGN_FAILED | VERIFY_FAILED | IO_ERROR | OUTPUT_CONFLICT | CANCELLED | SKIPPED
```

Map engine `SignResult.error_code` → `JobState`.

### Rules

1. **Isolation** — job failure sets that job terminal; loop continues.
2. **Pause** — checked between jobs; in-flight job finishes; remaining stay READY/DISCOVERED.
3. **Cancel queued** — non-started jobs → CANCELLED; in-flight finishes.
4. **Retry** — only if `is_retryable_error(code)` and `attempts < max_attempts`. Non-retryable from `NON_RETRYABLE_CODES` + `VERIFY_FAILED`, `PROFILE_INVARIANT`, `WRONG_PIN`.
5. **Output** — never overwrite source; engine already atomic temp+replace.
6. **Idempotency** — each job UUID; recovery treats SIGNING leftover as failed (do not trust unverified temp).
7. **Progress** — callback `(done, total, job)` optional.

### Signing backend

Protocol-compatible usage: call `engine.preflight` + `engine.sign` + engine already verifies. Lab uses `TestCertPdfSigner`. No PKCS#11 in this phase.

### Out of Scope

- PySide6 UI progress widgets
- Multi-token lanes
- Watch folder
- Real USB token
- Parallel preflight pools (sequential lab runner is enough; parallelism later)

## Tasks

- [x] T1: `retry.py` + unit tests (covers: S2)
- [x] T2: `worker.py` single-job processing + error mapping + tests (covers: S2; depends: T1)
- [x] T3: `queue.py` BatchEngine pause/resume/cancel/retry + isolation tests (covers: S1; S2; depends: T2)
- [x] T4: `recovery.py` + tests (covers: S2)
- [x] T5: Batch integration: 10 mixed PDFs, one corrupt, batch completes others (covers: S1; depends: T3)
- [x] T6: Review notes + control-plane + commit (covers: S2; depends: T1–T5)

## Acceptance criteria

1. `pytest` exit 0 including new batch tests.
2. One failing file does not stop others.
3. Transient retry works; VERIFY_FAILED / WRONG_PIN never auto-retried blindly.
4. Pause leaves remaining jobs unfinished but resumable.
5. Cancel marks unstarted jobs CANCELLED.
6. Source PDFs unchanged after batch.
7. No PUS/token claims.
