# NEXT ACTION

**Single recommended next step:**

Phase 4 batch engine delivered. USB token deferred.

1. **Phase 5 prep (required before Qt code):** run UI/UX Pro Max, write `docs/design/BRANDING_SPEC.md`, `DESIGN_TOKENS.md`, `UX_BRIEF.md` (spec §46.1 / §44.5b). Derive `golden-mark` / PNG / ICO from `golden.svg`.
2. Only then PySide6 main window + drag/drop + file list + profile/cert selectors.
3. Real USB token when available → fill TOKEN_COMPATIBILITY matrix.
4. PUS upload test before any compatibility claim.

## Do not

- Do not start Qt widgets before design gate artifacts exist.
- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs.
