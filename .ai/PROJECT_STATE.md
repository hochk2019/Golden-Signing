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
| P3-01 | PUS Safe settings + invariants | DONE | P1 | `signing/pus_safe.py` | unit | forced verify | — |
| P3-02 | Golden regression | DONE | P3-01 | `tests/regression/` | regression | source hash stable | — |
| P3-03 | Phase 3 review | DONE | P3-01..02 | `.ai/reviews/phase3-pus-safe.md` | — | PASS | — |
| P4-01 | Batch retry/worker/queue/recovery | DONE | P1–P3 | `batch/*` | unit+integration | 10-file isolation | — |
| P4-02 | Phase 4 review | DONE | P4-01 | `.ai/reviews/phase4-batch.md` | — | PASS | — |
| P5-00 | UI/UX Pro Max brief + tokens | TODO | branding | `docs/design/` | — | — | before Qt code |
| P5-01 | PySide6 main window | TODO | P5-00 | `ui/` | manual | — | Phase 5 |

## Verification evidence (Phase 2–4)

- `pytest -q` — **PASS** exit 0 (full suite)
- Token + PUS Safe + Batch — all green
- Batch integration: 9/10 success, 1 corrupt isolated

## Status label

`PHASE 2–4 CORE (TOKEN SHELL + PUS SAFE + BATCH) COMPLETE / UI + REAL TOKEN + PUS UPLOAD PENDING`
