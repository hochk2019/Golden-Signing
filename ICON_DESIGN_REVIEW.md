# ICON DESIGN REVIEW — G-Sign (chờ duyệt)

**Spec:** `Golden Signing - G-Sign App Icon Design Specification.md`  
**Product UI name:** Golden Sign · Brand family: Golden Logistics  
**Status:** Concept exploration — **chưa** thay ICO/EXE

---

## Điều chỉnh so với spec (phù hợp codebase)

| Spec | Dự án hiện tại | Đề xuất |
|---|---|---|
| Tên “Golden Signing” | UI: **Golden Sign** | ICO title / shortcut: Golden Sign |
| App icon mới | `golden-app-icon.ico` = logo logistics | Thay bằng **G-Sign** |
| Logo trong app (sidebar) | `golden-mark-ui.png` | **Giữ nguyên** (đúng yêu cầu §15) |
| Thư mục deliverable | `branding/golden-signing/` | Map vào `assets/branding/gsign/` + `G_SIGN_CONCEPTS/` |
| Review gate 6 reviewer | Solo user | Bạn = final decision |

## Research (Phase 1 — tóm tắt)

- Windows ICO cần **16/24/32** nét dày; gradient gần như không thấy ở taskbar.
- Acrobat/Foxit: **chữ A / con cáo / PDF đỏ** → tránh silhouette chữ + tick UI.
- DocuSign/SignNow: **nét bút** phổ biến → G phải là khung chính, stroke chỉ là “cửa sổ” mở.
- Golden Logistics: kim cương vàng → G-Sign dùng **cùng họ màu** (#D99A22) nhưng **hình học khác**.

## 5 concepts (file trong `G_SIGN_CONCEPTS/`)

| File | Tên | Hình học |
|---|---|---|
| `concept-a.svg` | **Circular G-Sign** | G vòng gần tròn; stroke phá vòng cuối dưới-phải |
| `concept-b.svg` | **Open G** | G mở; **chính stroke tạo thanh ngang + đuôi G** |
| `concept-c.svg` | **Golden Ribbon** | Dải vàng gấp khúc thành G; đầu dải = nét ký |
| `concept-d.svg` | **Negative Space G** | Khối vàng đặc; G & stroke là **khoảng âm** |
| `concept-e.svg` | **G + Digital Node** | G nét vàng; cuối stroke có **node hình thoi** (không dùng tick UI) |

## Bảng điểm (ước lượng — bạn chấm lại)

| Tiêu chí | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| Recognizability (nhìn ra G) | 8 | 9 | 7 | 8 | 8 |
| Uniqueness vs PDF apps | 7 | 8 | 8 | 9 | 7 |
| Golden brand family | 8 | 7 | 9 | 8 | 8 |
| Digital-signature nghĩa | 8 | 9 | 7 | 7 | 8 |
| 16–24px readability | 7 | 8 | 7 | 9 | 7 |
| Professionalism | 8 | 8 | 9 | 8 | 7 |
| **Tổng /60** | **46** | **49** | **47** | **49** | **45** |

**Đề xuất chọn:** **B (Open G)** hoặc **D (Negative Space)** — B “ký” rõ nhất; D nhỏ đẹp nhất.  
Có thể hybrid: **D ở 16–32px**, **B ở 256+** (cùng geometry master).

## Sau khi bạn duyệt concept

1. Vector master `golden-signing.svg` (1024 grid, safe 12%)  
2. Core 16–32 + Premium 128–512  
3. ICO 10 tầng + PNG  
4. Cắm vào: `app_icon_path`, PyInstaller `.ico`, Inno Setup, title bar  
5. **Không** đụng `golden-mark.png` / sidebar  
6. `ADR-GSIGN-001.md`  
7. Commit + build release  

## Bạn reply

- **“Chọn B”** / **“Chọn D”** / **“Chọn A|C|E”**  
- **“Sửa concept”** — mô tả  
- Sau đó mình mới làm ICO + tích hợp.
