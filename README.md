# Golden Sign

PDF digital signature utility for Windows. Ký số PDF nhanh, ổn định, ưu tiên tương thích quy trình Hải quan (PUS) — **không** phải công cụ chèn ảnh chữ ký.

- **Tên hiển thị:** Golden Sign  
- **Phiên bản:** 1.1.2  
- **Developer:** HOC HK — hochk2019@gmail.com
- **Repo:** https://github.com/hochk2019/Golden-Signing   
- Hướng dẫn: `docs/HUONG_DAN_SU_DUNG.md`

## Tính năng nổi bật (1.1.0)

- Ký số PDF hàng loạt (USB token PKCS#11)
- Chuyển **Word/Excel → PDF** rồi ký (MS Office COM)
- **Nén PDF** trước khi ký (Lossless / Balanced / PUS Safe 400KB)
- Nút **KÝ SỐ** · **CHỈ NÉN** · **NÉN VÀ KÝ SỐ**
- Hồ sơ theo chứng thư, lịch sử, cập nhật tự động từ GitHub

## Cài đặt

**Khuyến nghị (1 file):**

1. Tải **`GoldenSign-Setup-1.1.2.exe`** từ [Releases](https://github.com/hochk2019/Golden-Signing/releases).
2. Double-click → làm theo wizard (không cần admin).
3. Cài vào `%LOCALAPPDATA%\Programs\GoldenSign`; tạo **Desktop** + Start Menu.
4. Mở **Golden Sign** từ Desktop.

**Portable (không cài):** tải `GoldenSign-1.1.2-win64.zip` → giải nén → chạy `GoldenSign.exe` (hoặc `Cai-dat.bat` để cài).

**Gỡ cài đặt:** *Settings → Apps → Golden Sign → Uninstall*.

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

Sinh `dist\release\`: Setup.exe + portable zip + `checksums.txt` (cần Inno Setup 6).

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
