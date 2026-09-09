# NEXT ACTION

1. **Manual GUI check** (recommended): `uv run golden-signing` or  
   `uv run python -m golden_signing.app.bootstrap` — drop PDFs, press KÝ SỐ, inspect `signed/`.
2. USB token when available → fill `docs/TOKEN_COMPATIBILITY.md`.
3. PUS upload before any compatibility claim.
4. Later: cert picker, history, dark theme, appearance designer (Phase 6).

## Do not

- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs.
