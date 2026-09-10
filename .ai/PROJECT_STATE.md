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
| P5-00 | UI/UX Pro Max brief + tokens + branding assets | DONE | — | `docs/design/`, `assets/branding/` | — | design gate PASS | human glance mark |
| P5-01 | PySide6 main window (minimal) | DONE | mark OK | `ui/main_window.py` | offscreen 5 tests | pytest 0 | manual GUI check |
| P5-02 | Phase 5 Qt review | DONE | P5-01 | `.ai/reviews/phase5-qt-ui.md` | — | PASS | — |
| P5-03 | ECA token UI + PIN fix | DONE | P2 | `token_pdf_signer.py`, UI | wrong PIN test | commit 6307786 / 11027d9 | — |
| P6-01 | Visible signature + output UX (original spec) | DONE | P5 | `appearance.py`, UI | 6 tests | commit 275ba0c | user GUI check |
| P6-02 | Stamp polish (default visible, rich info, fold VN, color+bg toggle, tight box) | DONE | P6-01 | appearance + UI | tests green | 67ee2f3…c91ff55 | user GUI |
| P6-03 | Token UX (auto-scan, PIN API, compact cert dialog) | DONE | P2 | token_pdf_signer + UI | ECA listed | 6307786 / 11027d9 | — |
| P6-04 | Empty-password encrypted PDF sign/verify | DONE | P1 | `pdf/crypto.py` | user file test | 5df8c38 | — |
| P7-00 | Appearance designer / logo in stamp / QR / placement | TODO | P6 | — | — | — | deferred |
| P7-01 | History / full cert profile page | TODO | P5 | `ui/` | — | — | deferred |

## Verification evidence

- `pytest -q` — **PASS** exit 0
- Visible lab sign: field `GoldenSigningVisible` + crypto valid
- ECA token: cert list + PIN via `token.open(user_pin=)`
- Empty-password encrypted PDF: preflight not BLOCK; sign+verify OK

## Status label

`PHASE 2–6 COMPLETE + STAMP/TOKEN POLISH / MANUAL GUI + PUS UPLOAD PENDING`
