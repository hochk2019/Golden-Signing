---
feature: phase-9-packaging
status: delivered
updated: 2026-09-11
branch: main
commits: 2f453f6..HEAD
---

# Phase 9 — Packaging v1.0.0

## Report

**What was built** — Version **1.0.0** (`__version__`, pyproject, README, smoke test). PyInstaller onedir `GoldenSign.exe` with bundled branding assets; `resource_root()` works frozen or from source. Per-user installer: `install.ps1` / `Cai-dat.bat` → `%LOCALAPPDATA%\Programs\GoldenSign` + Start Menu + HKCU Uninstall key; `uninstall.ps1`. Release zip `GoldenSign-1.0.0-win64.zip` + `checksums.txt`. User guide `docs/HUONG_DAN_SU_DUNG.md` + SVG illustrations.

**Update vs install** — Updater replaces the **install directory** (parent of `GoldenSign.exe`) after SHA256 verify; per-user path needs no admin. Uninstaller remains in the same folder (shipped in zip, refreshed by update). Data stays in `%LOCALAPPDATA%\GoldenSign` after uninstall.

**Verification** — full pytest exit 0; PyInstaller build SUCCESS; zip 76MB + checksums written.

## Tasks

- [x] T1 version 1.0.0 consistency
- [x] T2 PyInstaller onedir + frozen asset paths
- [x] T3 install/uninstall scripts + release zip/checksums
- [x] T4 user guide + illustrations
- [x] T5 tests + prepare GitHub push
