# Phase 2 — Token Abstraction Review

Date: 2026-09-09
Reviewer: orchestrator in-session (independent subagent APIError)
Spec: `docs/compose/spec/phase-2-token-abstraction.md`
Status: **PASS with notes**

## Verification evidence

| Command | Result |
|---|---|
| `python -m pytest -q` | **PASS** exit 0 (full suite + 23 token tests) |
| `mypy src/golden_signing/token/` | **PASS** |
| `ruff check` token modules | **PASS** |

## A) Spec compliance

| AC | Verdict | Evidence |
|---|---|---|
| pytest 0 | MET | exit 0 |
| Discovery no load; env respected | MET | `discovery.py`; `test_token_discovery.py` |
| Concurrent sign serialized | MET | RLock + `test_concurrent_sign_serialized` |
| Unplug → TokenLostError, no crash | MET | `test_unplug_then_sign_is_token_lost`, integration |
| recover after replug | MET | `test_recover_after_replug` |
| No PIN/key in logs/files | MET | PIN `del` after login; fake key in memory only |
| No real-token/PUS claim | MET | status docs only |

## B) Correctness

| Severity | Finding | Disposition |
|---|---|---|
| Important | `assert LOGGED_IN` in sign path | **FIXED** — raise `TokenError` instead of assert |
| Minor | `health_check` False marks TOKEN_LOST even if transient | Accepted for Phase 2; recover() is the path back |
| Minor | Pkcs11Backend not exercised on real hardware | OPEN — user token matrix still TBD |
| Minor | Fake PIN default `123456` is lab-only | OK — test double |

## C) Consistency

- Reuses `CertificateInfo`, `SigningSession`, `TokenError` / `TokenLostError` taxonomy.
- `TokenBackend` extends operational surface without breaking `SignerBackend`.
- Module layout matches spec §6 `token/` tree (base, pkcs11, discovery, session).

## Security notes

1. Private key operations only via token/Fake in-memory key — no export API.
2. PIN from `Callable[[], str]`, not stored on manager; `del pin` in `finally`.
3. Discovery never `LoadLibrary`s — existence check only.
4. Device-removed string heuristic maps vendor errors → `TokenLostError`.

## Open for next phase

- Real USB token fill-in of `docs/TOKEN_COMPATIBILITY.md` matrix.
- Wire `TestCertPdfSigner` / future engine to `SignerBackend` Protocol properly.
- Windows CSP/KSP fallback if vendor has no PKCS#11.
