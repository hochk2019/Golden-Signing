# START HERE — Golden Sign

Project: Golden Sign (display name; package `golden_signing`)
Spec: 1.2.0 (file `Golden Signing v1.2.0.md`; do not edit spec file — track in revisions)
Application version: **1.0.0**
Current milestone: **Phase 8–10 complete · Phase 9 packaging v1.0.0**
Last verified commit: (see git log)
Current blocker: none
Next task: Publish GitHub Release v1.0.0 assets; user tests install/update path
Required skills: compose-next, verification-before-completion
Last test result: `pytest` exit 0

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
