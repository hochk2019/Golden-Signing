# DECISIONS

## D-001 — Stack lock (spec §1, §42)

- Python 3.13.x
- Signing engine: **pyHanko 0.37.0** (MIT, PyPI verified 2026-09-09, released 2026-08-31)
- UI: PySide6 (LGPLv3/GPLv3 Community — obligations reviewed before commercial release)
- PDF render: pypdfium2 (Apache-2.0/BSD-3-Clause + PDFium third-party licenses)
- Storage: SQLite local
- Packaging: PyInstaller **onedir** first
- Package manager: **uv** + lockfile

## D-002 — Spec source of truth

- `Golden Signing v1.2.0.md` is the product specification.
- Do **not** edit the original spec for cosmetic issues.
- Track inconsistencies in `docs/revisions/1.2.0-notes.md`.

## D-003 — Phase boundary for this session

User approved **Phase 0 Research lock only** for this delivery.
Phase 1+ requires golden fixtures (present) and a separate approval after ADR review.

## D-004 — Private fixtures

Golden ECUS PDFs live in `tests/fixtures/private/` and are **gitignored**.
SHA-256 recorded in `.ai/START_HERE.md`. Never push to public remotes.

## D-005 — Worktree policy

Main worktree at `E:\GPT\Golden Signing` used for Phase 0 bootstrap (no concurrent agents).
Feature work after Phase 0 should use Superpowers `using-git-worktrees` / compose-next Workspace.

## D-007 — Phase 1 scope (this session)

- User approved **Phase 1 PDF Laboratory only**.
- Workspace: continue on **main** (explicit override of D-005 worktree preference).
- Skills: compose-next + TDD + systematic-debugging + verification-before-completion + subagent-driven-development.
- `memory-systems` skill **rejected** for this project phase (agent-memory architecture ≠ PDF lab).
- Spec gate: write `docs/compose/spec/phase-1-pdf-lab.md` and wait for user approval before code (granted).

## D-008 — Phase 1 signing profile default

- Lab signing uses pyHanko modern path (SHA-256 digest); does **not** force ECUS `adbe.pkcs7.sha1`.
- PUS-Compatibility SubFilter remains a later profile experiment after real PUS validation (N-005).

## D-009 — Multi-agent fallback

- Subagent APIError on T2/T3/T5 completion; code landed in working tree and was verified/finished in-session.
- Independent review subagent (general-4) succeeded and drove two Important fixes (verify hard-fail; temp+replace).

## D-006 — Multi-agent

Parallel subagents for research/implementation with disjoint file sets; commits stay with orchestrator (this session).
