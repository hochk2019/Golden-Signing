# START HERE — Golden Signing

Project: Golden Signing
Spec: 1.2.0 (file `Golden Signing v1.2.0.md`; revision banner still says 1.1.0 — see `docs/revisions/1.2.0-notes.md`)
Application version target: 0.1.0-alpha
Current milestone: **Phase 2–5 minimal Qt UI COMPLETE**
Last verified commit: (filled after commit)
Current blocker: none (manual GUI check recommended)
Next task: User GUI smoke; then token/PUS or Phase 6 features
Required skills: compose-next, ui-ux-pro-max (before UI changes), test-driven-development, systematic-debugging, verification-before-completion
Last test result: `pytest` exit 0 (offscreen UI included)

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

## Phase 1 quick facts

- Preflight: SAFE on source, WARN + `Signature1` on ECUS signed
- ECUS packaging: `/Filter /Adobe.PPKMS`, `/SubFilter /adbe.pkcs7.sha1`, ByteRange `[0, 313171, 321173, 33265]`
- Lab sign path: ephemeral RSA test cert via pyHanko; **not** PUS-validated
