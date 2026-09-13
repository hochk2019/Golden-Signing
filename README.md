# Golden Sign

PDF digital signature utility for Windows. Ký số PDF nhanh, ổn định, ưu tiên tương thích quy trình Hải quan (PUS) — **không** phải công cụ chèn ảnh chữ ký.

- **Tên hiển thị:** Golden Sign  
- **Phiên bản:** 1.0.0  
- **Developer:** HOC HK — hochk2019@gmail.com — 0868.333.606  
- **Repo:** https://github.com/hochk2019/Golden-Signing  
- Spec gốc: `Golden Signing v1.2.0.md`  
- Hướng dẫn: `docs/HUONG_DAN_SU_DUNG.md`

## Cài đặt

1. Tải `GoldenSign-1.0.0-win64.zip` từ [Releases](https://github.com/hochk2019/Golden-Signing/releases).
2. Giải nén → chạy `install.ps1` (chuột phải → Run with PowerShell), hoặc copy thư mục vào `%LOCALAPPDATA%\Programs\GoldenSign`.
3. Mở **Golden Sign** từ Start Menu.

Gỡ cài đặt: Settings → Apps → Golden Sign → Uninstall, hoặc chạy `uninstall.ps1`.

## Cập nhật

App tự dò GitHub Releases khi mở (có thể tắt trong Cài đặt). Khi có bản mới: hiện ghi chú release → *Cập nhật ngay* → tải zip + kiểm SHA256 → thay thư mục cài → mở lại app.

## Develop

```
uv sync --extra ui --extra dev
uv run pytest
uv run golden-signing
```

## Build release

```
packaging\build_release.ps1
```

## Layout

```
assets/branding/     # logo
docs/                # ADR, design, user guide
packaging/           # PyInstaller + install scripts
src/golden_signing/  # application package
tests/               # pytest
```

## Safety

- No PIN / private key in logs.
- Never overwrite source PDFs; atomic output + post-sign verify.
- Private golden PDFs stay out of public remotes.

## License

Proprietary — HOC HK.
