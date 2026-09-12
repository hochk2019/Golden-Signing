---
feature: phase-8-github-update
status: delivered
updated: 2026-09-11
branch: main
commits: a398782..HEAD
---

# Phase 8 — GitHub Update

## Report

**What was built** — Package `golden_signing.updater`: parse/compare versions, fetch GitHub `/releases/latest`, pick `GoldenSigning-*-win64.zip`, load `checksums.txt`, download+SHA256-verify, extract to `%LOCALAPPDATA%\GoldenSigning\updates\staged-<ver>`, backup live dir to `updates/previous`, restore on failure. UI: *Giới thiệu → Kiểm tra cập nhật* with check / open release / stage buttons. *Cài đặt* has `update/repo` (`owner/name`). Dev/source only stages files (does not replace running tree).

**Verification** — `pytest tests/unit/test_updater.py tests/unit/test_update_dialog.py` PASS (13); full suite `pytest -q` exit 0.

**Journey log**
- Scope cut by user: no minisign, no beta/stable, no auto-restart.
- `dataclasses.replace` on frozen+slots UpdateInfo for checksums attach.
- Injected `get(url, timeout)` avoids network in tests; checksums URL must match asset name endswith.

## [S1] Problem

App không có kênh cập nhật. User không có server riêng; muốn check version mới từ **GitHub Releases**, tải asset, **verify SHA256**, cài, và **rollback** nếu hỏng. Không cần beta/stable channels, không cần chữ ký crypto (HTTPS + SHA256 là đủ v1).

## [S2] Design

### Source of truth

- GitHub REST: `GET https://api.github.com/repos/{owner}/{repo}/releases/latest`
- Bỏ qua draft; `prerelease=true` vẫn coi là latest nếu là release cuối (v1: không filter kênh).
- Repo slug lấy từ QSettings `update/repo` (VD `hockh/golden-signing`). Trống → UI báo “chưa cấu hình repo”.

### Version

- App version: `golden_signing.__version__` (PEP 440-ish, so sánh bằng `packaging.version` nếu có, fallback parse `x.y.z`).
- Release `tag_name`: `v1.2.3` hoặc `1.2.3` — strip `v` rồi so.
- Mới hơn ⇔ remote > local.

### Asset contract

Trong release, tìm asset theo thứ tự:
1. `checksums.txt` (hoặc `SHA256SUMS`) — dòng `\<sha256\>  \<filename\>`
2. Zip Windows: `GoldenSigning-*-win64.zip` hoặc `GoldenSigning-*.zip` (không `.exe` đơn lẻ v1)

Thiếu checksums hoặc hash không khớp → **không cài**.

### Apply / rollback

App đang chạy (onedir hoặc source):
1. Tải zip về `%LOCALAPPDATA%\GoldenSigning\updates\download-\<ver\>.zip`
2. Verify SHA256
3. Backup thư mục app hiện tại (nếu là onedir `GoldenSigning/`) sang `previous\` (giữ 1 bản)
4. Giải nén vào chỗ mới, ghi `pending_restart` marker
5. User bấm *Khởi động lại* → helper nhỏ (`python -m golden_signing.updater.apply`) thay thư mục rồi start lại
6. Nếu start mới fail (marker `apply_failed`) → restore `previous\`

Khi chạy từ source (dev, không phải onedir): chỉ **check + báo** version mới + link release; không tự thay source tree. *Stage* vẫn tải/verify vào `updates/` để thử.

### UI

- Trong **Giới thiệu**: nút **Kiểm tra cập nhật**
- Hộp thoại: đang check / đã mới nhất / có bản `vX.Y.Z` → Tải & chuẩn bị / Mở trang Release / lỗi mạng
- Auto-check nhẹ khi mở app **không** dialog ồn ào — chỉ badge/link ở Giới thiệu (optional v1: chỉ manual)

### Out of scope (S3)

- Kênh beta/stable
- Chữ ký minisign/ed25519
- Differential/patch update
- Tự động restart không hỏi

## Tasks

- [x] T1: version compare + GitHub latest parse (unit, mock JSON) — acceptance: parse tag/asset/checksums; newer/older/same (covers: S2)
- [x] T2: SHA256 verify checksums.txt (unit) — acceptance: match/mismatch/missing (covers: S2)
- [x] T3: download + extract + backup + rollback state machine (unit, tmp dirs) — acceptance: apply ok; bad hash abort; rollback restores previous (covers: S2)
- [x] T4: UI Kiểm tra cập nhật trong Giới thiệu (offscreen smoke) — acceptance: dialog states; no crash when repo empty/offline (covers: S2)
- [x] T5: bootstrap logging still green + full pytest — acceptance: exit 0 (covers: S2)
