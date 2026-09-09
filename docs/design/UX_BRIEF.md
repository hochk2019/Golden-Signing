# UX BRIEF — Golden Signing 0.1.0-alpha

Audience: customs brokers / office staff signing PDF batches on Windows. Vietnamese default UI.

## Primary job

Drop or add PDFs → see readiness → pick certificate/profile → **Ký số** → see per-file result. One screen for the happy path.

## IA (sidebar)

```
Trang chủ / Ký tài liệu   (primary)
Hàng đợi
Lịch sử
────────────
Hồ sơ ký
Mẫu hiển thị
────────────
Cài đặt
Giới thiệu
```

Logo mark only at top of rail (see BRANDING_SPEC). Workspace prioritizes file list + actions, not branding.

## Main screen (Ký)

1. Drop zone / [Thêm PDF] [Thêm thư mục]
2. File table: name, pages, status (Sẵn sàng / Cảnh báo / Lỗi), message
3. Certificate combo + profile auto-load by fingerprint
4. Signature mode: Vô hình | Hiển thị | Hỏi mỗi lần
5. Primary CTA **KÝ SỐ** (one primary action)
6. Progress: `n/total` + per-row state; pause/resume/cancel queued; retry failed

## Feedback rules (Pro Max)

- Always show progress for multi-step batch (`done/total`).
- Success = icon + text + color; error = cause + recovery (retry / open folder).
- Never silent failure; never SUCCESS without verify (engine already enforces).
- Empty state: “Kéo thả PDF vào đây”.
- Status announced as full phrase for a11y where Qt supports accessible names.

## Error copy (user-facing)

```
Không thể ký file
Tên file: invoice-032.pdf
Lý do: Chứng thư số không còn hợp lệ.
[ Xem chi tiết ] [ Bỏ qua ]
```

Technical detail behind “Xem chi tiết” (code, backend, fingerprint). Stable error codes from exceptions taxonomy.

## Explicit non-goals (0.1.0-alpha)

Watch folder, CLI, appearance designer polish, cloud login, OCR, AI in crypto path.

## Accessibility

Keyboard: tab order, focus ring, 44px min targets where possible. No color-only status. Vietnamese labels + accessible names on icon buttons.

## Review checkpoints before Qt coding freeze

- [x] Design system search (Pro Max) — Enterprise Gateway + Swiss minimal
- [x] Tokens documented
- [x] Branding spec + mark pipeline
- [ ] Human glance at mark PNG/ICO when user wakes
- [ ] Wireframe mock approved (optional screenshot later)
