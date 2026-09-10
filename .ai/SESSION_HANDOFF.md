# SESSION HANDOFF

## Overnight autonomous (user asleep)

Implemented without push:

1. **05399b2** — Drag signature position (click PDF preview), per-cert save; error **Chi tiết** dialog; **Xác minh PDF**; batch **Tạm dừng / Ký lại lỗi**
2. **9e85be5** — SQLite **lịch sử ký** + sidebar; **Export diagnostics JSON**; **Watch folder** (Cài đặt)
3. **9e07aec** — lint/mypy cleanup

Also earlier same overnight: table column balance, Profiles dialog, logo XObject fix, cert profile store.

## Tests

- `pytest -q` exit 0 (full suite)
- mypy/ruff on new modules clean

## Not done (by design / blocked)

- Phase 8 signed update system
- Phase 9 PyInstaller packaging + code-sign
- PUS real-world upload (needs Hải quan env)
- True Vietnamese diacritics on PDF (folded for compatibility)

## When user wakes

1. Restart app (`uv run golden-signing`)
2. Try: **Vị trí…** (click preview), row **Chi tiết**, **Xác minh PDF…**, **Lịch sử ký**, Cài đặt → **Watch folder** + **Export diagnostics**
3. Ask for Phase 8/9 or PUS test next

## HEAD

`9e07aec` on `main` — **not pushed**
