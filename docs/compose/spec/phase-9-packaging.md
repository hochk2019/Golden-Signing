---
feature: phase-9-packaging
status: delivered
updated: 2026-09-11
branch: main
commits: 2f453f6..d4af29e
---

# Phase 9 — Packaging v1.0.0

## Report

**What was built** — Version **1.0.0**. Slim PyInstaller onedir (`~116 MB`; drop unused Qt DLLs; **must keep asyncio** for pyHanko). Two release artifacts: **Inno Setup** `GoldenSign-Setup-1.0.0.exe` (~39 MB, double-click install, always Desktop shortcut, per-user `%LOCALAPPDATA%\Programs\GoldenSign`) and portable zip (~53 MB). `resource_root()` works frozen/source. User guide + SVG.

**Update vs install** — Updater replaces install dir (parent of `GoldenSign.exe`) after SHA256; zip asset is what updater downloads. Data stays in `%LOCALAPPDATA%\GoldenSign` after uninstall.

**Verification** — pytest exit 0; ISCC compile SUCCESS; smoke `GoldenSign.exe` offscreen 6s RUNNING after asyncio fix; user confirmed sign + verify OK after install.

**Journey log** — Excluding `asyncio` broke pyHanko at launch; never exclude stdlib modules pyHanko pulls without running the frozen EXE.

## Tasks

- [x] T1 version 1.0.0 consistency
- [x] T2 PyInstaller onedir + frozen asset paths
- [x] T3 install/uninstall scripts + release zip/checksums
- [x] T4 user guide + illustrations
- [x] T5 tests + prepare GitHub push
