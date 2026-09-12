# Golden Sign

PDF digital signature utility for Windows. Ký số PDF nhanh, ổn định, ưu tiên tương thích quy trình Hải quan (PUS) — **không** phải công cụ chèn ảnh chữ ký.

Tên hiển thị: **Golden Sign** (trước đây: Golden Signing). Spec gốc: `Golden Signing v1.2.0.md`.
- Version target: `0.1.0-alpha`
- Developer: HOC HK — hochk2019@gmail.com — 0868.333.606

## Status

**Phase 0 — Research lock** (see `.ai/START_HERE.md`).

PUS real-world validation: **PENDING**. Never claim 100% PUS compatibility without a live upload/verify test.

## Stack

Python 3.13 · pyHanko · pypdfium2 · PySide6 (UI phase) · SQLite · uv · PyInstaller

## Develop

```
uv sync
uv run pytest
uv run python -c "import golden_signing; print(golden_signing.__version__)"
```

## Layout

```
.ai/                 # agent control-plane (read START_HERE first)
assets/branding/     # logo source + variants
docs/                # ADR, matrices, design, compose spec
src/golden_signing/  # application package
tests/fixtures/      # public + private (private gitignored)
```

## Safety rules

- No PIN / private key in logs, config, or dumps.
- Never overwrite source PDFs; atomic output only.
- Post-sign verification required before SUCCESS.
- Private golden PDFs stay out of public remotes.

## License

Proprietary — HOC HK. Third-party licenses documented at release (`THIRD_PARTY_LICENSES.md`).
