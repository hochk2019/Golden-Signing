# NEXT ACTION

**Single recommended next step after this session:**

Phases 2–3 delivered on `main` (token shell + PUS Safe profile/golden regression).

1. **If USB token available** — fill `docs/TOKEN_COMPATIBILITY.md` (discovery, certs, PIN, sign digest).
2. **Phase 4 — Batch engine** (spec §30): job queue, per-file state machine, retry/pause, atomic commit, one bad file must not kill batch.
3. Keep PUS status as validation pending until real upload test.

## Do not

- Do not claim PUS compatibility without real PUS upload test.
- Do not parallelize crypto on one token.
- Do not write PIN/private key to logs.
- Do not overwrite source PDFs; use atomic output only.
