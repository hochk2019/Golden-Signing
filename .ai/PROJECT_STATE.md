# PROJECT STATE

Status legend: DONE | IN_PROGRESS | BLOCKED | TODO | DEFERRED

| ID | Objective | Status | Depends | Files | Tests | Evidence | Next |
|---|---|---|---|---|---|---|---|
| P0-01 | Git repo + ignore private fixtures | DONE | — | `.gitignore` | — | init + commit | — |
| P0-02 | Move/hash golden PDFs | DONE | — | `tests/fixtures/private/` | pypdfium2 4 pages | SHA256 in START_HERE | — |
| P0-03 | `.ai/` control-plane | DONE | P0-01 | `.ai/*` | — | files present | — |
| P0-04 | REVISION_NOTE | DONE | — | `docs/revisions/1.2.0-notes.md` | — | N-001..N-005 | — |
| P0-05 | ADR + matrices | DONE | P0-03 | `docs/ARCHITECTURE_*.md`, DEPENDENCY, TOKEN | — | written | — |
| P0-06 | pyproject + uv.lock + venv | DONE | P0-05 | `pyproject.toml`, `uv.lock` | import smoke | uv sync OK | — |
| P0-07 | Domain contracts | DONE | P0-06 | `signing/contracts.py`, exceptions, batch/state | smoke tests | 7 passed | — |
| P0-08 | Branding + fixture READMEs | DONE | — | `assets/branding/README.md` | — | written | — |
| P0-09 | Smoke tests | DONE | P0-06 | `tests/unit/test_smoke.py` | 7 passed | pytest exit 0 | — |
| P0-10 | Initial commit | IN_PROGRESS | P0-01..09 | — | — | this session | commit |
| P1-01 | PDF preflight laboratory | TODO | P0-10 | `src/golden_signing/pdf/` | golden fixtures | — | Phase 1 |
| P1-02 | Sign with test certificate | TODO | P1-01 | `signing/pdf_signer.py` | verify pass | — | Phase 1 |
| P2-01 | PKCS#11 token adapter | TODO | P1-02 | `token/pkcs11.py` | token present | user token | Phase 2 |

## Verification evidence (Phase 0)

- `uv sync` / `uv sync --extra dev` — PASS
- `uv run pytest` — **7 passed**
- pyHanko **0.37.0** installed in `.venv`
- Golden PDFs: 4 pages each

## Status label

`PHASE 0 COMPLETE / PUS REAL-WORLD VALIDATION PENDING`
