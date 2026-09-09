# PROJECT STATE

Status legend: DONE | IN_PROGRESS | BLOCKED | TODO | DEFERRED

| ID | Objective | Status | Depends | Files | Tests | Evidence | Next |
|---|---|---|---|---|---|---|---|
| P0-01..10 | Research lock + scaffold | DONE | — | Phase 0 | 7 smoke | 691f09f / 3e49261 | — |
| P1-01..04 | PDF laboratory + review | DONE | P0 | pdf/, signing/ | 70+ | 3d7e7d0 / 7b6acb3 | — |
| P2-01 | PKCS#11 discovery | DONE | P1 | `token/discovery.py` | unit | env + no-load tests | — |
| P2-02 | Token session manager | DONE | P2-01 | `token/session.py` | unit | serialize / lost / recover | — |
| P2-03 | Pkcs11Backend + Fake | DONE | P2-02 | `token/pkcs11.py`, `fake.py` | unit+integration | missing DLL TokenError; fake sign | — |
| P2-04 | Phase 2 review | DONE | P2-01..03 | `.ai/reviews/phase2-token.md` | — | PASS w/ notes | — |
| P2-05 | Real USB token matrix | TODO | P2-03 | `docs/TOKEN_COMPATIBILITY.md` | user device | — | user session |
| P3-01 | PUS Safe production profile | TODO | P1, P2 | `signing/profiles.py` | golden | — | Phase 3 |

## Verification evidence (Phase 2)

- `pytest -q` — **PASS** exit 0 (full suite)
- Token tests — 23 passed (discovery/fake/session/pkcs11/integration)
- `mypy` token modules — PASS
- `ruff` token modules — PASS
- Concurrent sign: 8 threads serialized on one manager
- Unplug → `TokenLostError` + `TOKEN_LOST`; replug + `recover()` → `LOGGED_IN`

## Status label

`PHASE 2 TOKEN ABSTRACTION COMPLETE (FAKE+PKCS11 SHELL) / REAL TOKEN + PUS VALIDATION PENDING`
