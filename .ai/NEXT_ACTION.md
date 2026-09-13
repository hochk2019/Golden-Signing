# NEXT ACTION — v1.1.0

**Current phase:** I3 polish + RC prep (core convert/compress/UI wired)
**Current task:** T53 UI polish · T54 docs/release
**Last successful step:** full pytest exit 0 after convert+compress+worker+UI
**Failed step:** Office COM unit test crashes host → spike-only (opt-in)
**Files changed:** document/, compress/, batch/, ui/compression_dialog, main_window, file_table
**Tests run:** `pytest -q` exit 0
**Next exact action:** user GUI check (Nén và ký số); then version bump 1.1.0 + build release

## Anti-forgetting (v1.1.0)

| ID | Task | Status |
|---|---|---|
| T48 | S0 audit + control-plane | DONE |
| T49 | S1 compression spike + ADR | DONE |
| T50 | S2 Office spike + ADR | DONE |
| T51 | I1 convert + job states | DONE |
| T52 | I2 compression engine | DONE |
| T53 | I3 UI compress + convert | DONE (user GUI check pending) |
| T54 | I4 orchestrator + I5 docs/release | IN_PROGRESS |

## Do not

- Do not claim PUS compatibility without real upload.
- Do not compress a PDF after it is signed.
- Do not rewrite Signing Core without regression tests.
- Do not bundle Ghostscript AGPL.
- Do not write PIN/private key to logs.
- Do not overwrite source files.
