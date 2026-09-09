---
feature: phase-0-research-lock
status: delivered
updated: 2026-09-09
branch: main
commits: 691f09ff7402f5dd60e5b760a06ebc1fb5173d00
---

# Phase 0 — Research Lock

## Report

**What was built** — Golden Signing bootstrap on `main` in `E:\GPT\Golden Signing`: git repo with private-fixture ignore rules, `.ai/` anti-forgetting control-plane, revision notes for spec 1.2.0 inconsistencies, ADR locking Python 3.13 + pyHanko 0.37.0 + PySide6 + pypdfium2 + uv/PyInstaller, dependency and token matrices, domain contracts (signing Protocols, error taxonomy, batch state machine, atomic write), uv environment with pyHanko 0.37.0, and seven unit smoke tests. Golden ECUS PDFs installed privately and hashed (4 pages each).

**Verification** — `uv sync` PASS; `uv sync --extra dev` PASS; `uv run pytest` **7 passed**; `git check-ignore` confirms private PDFs excluded; import smoke prints `0.1.0a0` and pyHanko `0.37.0`.

**Journey log**
1. Actor research subagents failed with APIError; completed PyPI/docs research in-session instead.
2. PowerShell `Set-Content` wrote unquoted package inits → SyntaxError; fixed with quoted docstrings.
3. Spec banner 1.2.0 vs footer 1.1.0 and duplicate §44.5 recorded in REVISION_NOTE rather than editing source.
4. Private fixtures must stay gitignored — hash table is the integrity source of truth.
5. Next phase must start with PDF preflight against golden files, not UI.

## [S1] Problem

Golden Signing is a greenfield Windows PDF digital-signature app. The spec mandates Phase 0 (research lock) before any UI or signing implementation.

## [S2] Design

Foundation delivered: control-plane, ADR/matrix docs, scaffold, domain contracts, fixtures, first commit path. No production UI or token I/O.

## [S3] Out of Scope

- PySide6 windows, real PKCS#11, PUS upload, updater, installer
- Editing `Golden Signing v1.2.0.md`
- Committing private golden PDFs

## Tasks

- [x] T1: Git init + .gitignore + directory scaffold
- [x] T2: Install golden fixtures + SHA-256 + page-count check
- [x] T3: Write `.ai/` control-plane files
- [x] T4: Write REVISION_NOTE
- [x] T5: Write ADR + DEPENDENCY_MATRIX + TOKEN_COMPATIBILITY
- [x] T6: Scaffold pyproject.toml + src packages + smoke test
- [x] T7: Domain contracts modules
- [x] T8: Branding README + fixture private README
- [x] T9: Initial commit (this commit)

