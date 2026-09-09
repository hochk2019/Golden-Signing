# START HERE — Golden Signing

Project: Golden Signing
Spec: 1.2.0 (file `Golden Signing v1.2.0.md`; revision banner still says 1.1.0 — see `docs/revisions/1.2.0-notes.md`)
Application version target: 0.1.0-alpha
Current milestone: **Phase 0 — Research lock**
Last verified commit: 691f09ff7402f5dd60e5b760a06ebc1fb5173d00
Current blocker: none
Next task: finish Phase 0 artifacts (ADR, matrices, domain contracts, venv)
Required skills: compose-next, ui-ux-pro-max (before any UI code), test-driven-development, systematic-debugging, verification-before-completion
Last test result: n/a (no test suite yet)

## Session resume protocol

1. Read this file
2. `git status` + `git log -3`
3. Read `.ai/PROJECT_STATE.md` and `.ai/NEXT_ACTION.md`
4. Inspect uncommitted changes
5. Run focused tests if any
6. Continue next unchecked task — do **not** restart the project

## Golden fixtures (PRIVATE — do not commit publicly)

| Logical ID | Path | SHA-256 |
|---|---|---|
| GOLDEN_INPUT_ECUS_SAMPLE | `tests/fixtures/private/ecus_source.pdf` | `76DF3ED717A0077E4DEF2612005467BA8A21E095FFBE9DC076D14A150EC9B272` |
| GOLDEN_OUTPUT_ECUS_SAMPLE | `tests/fixtures/private/ecus_signed.pdf` | `11921502135884CBDCD35F366DD2CCC7176C1D22843BD1EFB4668F412CD8E475` |

Both are PDF 1.7, 4 pages (verified with pypdfium2).

