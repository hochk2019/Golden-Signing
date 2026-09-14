# GOLDEN SIGNING — G-SIGN APP ICON DESIGN SPECIFICATION

**Project:** Golden Signing  
**Feature:** New Windows Application Icon  
**Design Concept:** G-Sign  
**Version:** 1.0  
**Status:** Design Request  
**Brand Owner:** HOC HK / Golden Logistics

---

## 1. MỤC TIÊU THIẾT KẾ

Thiết kế một **biểu tượng ứng dụng Windows hoàn toàn mới cho Golden Signing**, khác với logo Golden Logistics đang sử dụng trong giao diện ứng dụng.

Biểu tượng mới phải trở thành một **Application Symbol** độc lập, có khả năng nhận diện Golden Signing ngay cả khi:

- không có tên ứng dụng;
- được hiển thị ở kích thước rất nhỏ;
- nằm trên Desktop;
- nằm trên Taskbar;
- nằm trong Start Menu;
- nằm trong Windows Search;
- nằm trong installer;
- nằm trong cửa sổ About;
- nằm trong thông báo hệ thống.

### Thông điệp cần truyền tải

Biểu tượng phải thể hiện đồng thời:

**GOLDEN + DIGITAL SIGNATURE + TRUST / VERIFIED**

nhưng phải được thể hiện bằng **một biểu tượng thống nhất**, không phải ghép ba icon rời rạc.

---

# 2. CONCEPT CHÍNH: “G-SIGN”

### Ý tưởng cốt lõi

Biến chữ **G** của “Golden” thành một biểu tượng nhận diện.

Chữ G không nên được vẽ như một font chữ thông thường.

Thay vào đó:

> **G là cấu trúc hình học chính của icon.**

Sau đó tích hợp một **signature stroke** vào chữ G.

Cuối cùng, phần cuối của nét ký tạo thành một dạng **check / verification gesture**.

Ý tưởng tổng quát:

```text
G
+
SIGNATURE STROKE
+
VERIFICATION GESTURE
```

Không được thiết kế thành:

```text
[G] + [✓]
```

mà phải trở thành một biểu tượng thống nhất, trong đó chữ G và nét ký là cùng một ngôn ngữ hình học.

---

# 3. Ý NGHĨA HÌNH HỌC

Logo phải có thể giải thích bằng ba tầng:

### Tầng 1 — G

Chữ G tượng trưng cho:

**Golden**

và tạo liên kết trực tiếp với thương hiệu Golden Logistics.

### Tầng 2 — Signature Stroke

Một đường cong giống nét bút ký số chạy xuyên hoặc tương tác với cấu trúc G.

Nó tượng trưng cho:

**Signing**

### Tầng 3 — Verification

Phần cuối nét ký tạo thành một dấu xác nhận tinh tế.

Không nhất thiết phải là dấu check `✓` hoàn chỉnh.

Có thể sử dụng:

- stroke kết thúc hướng lên;
- một góc check;
- một đoạn cắt hình học;
- negative space dạng check.

Mục tiêu là:

**Người nhìn cảm nhận được “verified” mà không thấy đây là một dấu tick UI thông thường.**

---

# 4. HÌNH DÁNG TỔNG THỂ

Ưu tiên:

- silhouette rõ;
- hình học đơn giản;
- cân bằng;
- góc bo vừa phải;
- đường nét đủ dày;
- ít chi tiết;
- không sử dụng typography trực tiếp làm icon.

Icon nên có cảm giác:

**Premium + Technical + Trustworthy**

Không quá mềm mại như ứng dụng lifestyle.

Không quá cứng như phần mềm kế toán.

Không quá “security” như antivirus.

Không giống PDF reader.

Không giống document scanner.

---

# 5. CẤU TRÚC LOGO

AI Designer phải thử ít nhất 5 biến thể hình học.

## Variant A — Circular G-Sign

Một chữ G gần dạng vòng tròn.

Nét ký chạy bên trong và phá vòng ở đoạn cuối.

Đây là biến thể ưu tiên nghiên cứu đầu tiên.

## Variant B — Open G

Chữ G mở rõ ràng hơn.

Signature stroke tạo phần mở cuối của chữ G.

Mục tiêu:

**G + signature là cùng một đường nét.**

## Variant C — Golden Ribbon G

Chữ G được tạo thành từ một dải vàng.

Một đầu dải tạo thành nét ký.

Mang cảm giác:

**premium / fintech / enterprise**

## Variant D — Negative Space G

Không dùng đường viền G trực tiếp.

G được tạo bởi negative space.

Nét ký chạy ngang qua negative space.

Ưu điểm:

- hiện đại;
- dễ nhận diện ở kích thước nhỏ;
- có tiềm năng trở thành biểu tượng thương hiệu dài hạn.

## Variant E — G + Digital Spark

G vẫn là thành phần chính.

Nét ký kết thúc bằng một điểm sáng / node nhỏ hoặc một góc hình học.

Có thể gợi ý:

**digital certificate / electronic signing**

Nhưng phải cực kỳ tiết chế và không dùng hiệu ứng “ánh sáng” thực sự trong icon chính.

---

# 6. TỶ LỆ VÀ GRID

Thiết kế phải sử dụng grid hình học.

Khuyến nghị:

**Base canvas: 1024 × 1024**

Thiết kế theo:

**8 px / 16 px grid system**

Có safe area khoảng:

**10–12% mỗi cạnh**

Không để artwork chạm mép icon.

### Tỷ lệ đề xuất

```text
Canvas
100%

Safe area
≈ 88–90%

Main symbol
≈ 72–78%

Signature stroke
≈ 55–65%
```

Đây là starting point. AI designer được phép điều chỉnh nếu optical balance tốt hơn, nhưng phải ghi lại lý do.

---

# 7. STROKE

Signature stroke phải có khả năng tồn tại ở kích thước nhỏ.

Không sử dụng stroke quá mảnh.

AI phải kiểm tra:

**16 px / 20 px / 24 px / 32 px / 48 px / 64 px / 128 px / 256 px / 512 px**

### Quy tắc

Ở:

**16–24 px**

chỉ giữ lại:

- silhouette G;
- nét ký chính;
- verification gesture.

Ở:

**48–128 px**

có thể xuất hiện:

- negative space;
- các chi tiết hình học phụ.

Ở:

**256–512 px**

có thể hiển thị đầy đủ cấu trúc.

---

# 8. KHÔNG ĐƯỢC DÙNG TEXT TRONG ICON

Không đưa các chữ:

`GOLDEN`  
`SIGN`  
`GS`  
`PDF`  
`CKS`  
`✓`

vào icon dưới dạng typography.

Đặc biệt:

**không dùng chữ “GS” làm logo chính.**

Logo cần được nhận biết bằng hình dạng.

---

# 9. MÀU SẮC

Logo phải thuộc cùng brand family với Golden Logistics nhưng không cần sao chép chính xác logo hiện tại.

### Primary Golden

`#D99A22`

### Deep Gold

`#A96F08`

### Highlight

`#F4C15D`

### Dark

`#111827`

### White

`#FFFFFF`

Có thể nghiên cứu thêm 1 accent phụ nhưng không vượt quá 1 màu accent ngoài nhóm vàng.

---

# 10. ƯU TIÊN GRADIENT HAY FLAT?

### Icon chính

Ưu tiên:

**flat / semi-flat**

Không dùng gradient quá mạnh.

Có thể tạo một gradient vàng rất nhẹ ở phiên bản 256/512 px nếu nó giúp biểu tượng premium hơn.

Nhưng:

> Khi convert xuống 16–32 px, icon phải vẫn hoạt động hoàn toàn mà không phụ thuộc gradient.

---

# 11. DARK MODE

Phải thiết kế tối ưu cho:

### Light background

Biểu tượng phải có contrast tốt và không bị chìm trên nền trắng.

### Dark background

Biểu tượng phải có contrast tốt và không bị chói hoặc mất chi tiết trên nền tối.

AI phải kiểm tra optical balance riêng cho cả hai bối cảnh.

Không đơn giản chỉ đảo màu.

Có thể cần tạo:

**Light Context Variant**

và

**Dark Context Variant**

nhưng silhouette phải giống nhau.

---

# 12. TRANSPARENT BACKGROUND

Icon master phải hỗ trợ:

**transparent background**

Không đặt nền trắng cố định.

AI có thể tạo thêm các composition preview cho installer/marketing, nhưng master icon phải là vector có nền trong suốt.

---

# 13. WINDOWS ICON

Phải tạo đầy đủ:

```text
golden-signing.ico
```

ICO phải chứa các resolution:

```text
16×16
20×20
24×24
32×32
40×40
48×48
64×64
96×96
128×128
256×256
```

Không chỉ resize một PNG 256 xuống.

Mỗi kích thước phải được kiểm tra rasterization.

---

# 14. MASTER ASSET

File gốc phải là:

```text
golden-signing.svg
```

Ngoài ra tạo:

```text
golden-signing-512.png
golden-signing-256.png
golden-signing.ico
```

SVG là:

**Single Source of Truth**

Không được chỉnh sửa từng PNG một cách độc lập.

---

# 15. RELATIONSHIP VỚI LOGO GOLDEN LOGISTICS

Cực kỳ quan trọng:

### Existing Brand Logo

`GOLDEN LOGISTICS`

tiếp tục được sử dụng trong:

- giao diện;
- About;
- splash;
- thương hiệu;
- tài liệu marketing.

### New App Symbol

`G-SIGN`

được sử dụng trong:

- Windows executable;
- Desktop shortcut;
- Taskbar;
- Start Menu;
- Installer;
- Notification;
- application window icon.

Hai hệ thống phải:

**cùng brand family**

nhưng:

**không phải cùng một artwork.**

---

# 16. KHÔNG ĐƯỢC COPY LOGO HIỆN TẠI

Không được:

- lấy logo Golden Logistics rồi thu nhỏ;
- cắt một phần logo;
- thêm dấu tick lên logo hiện tại;
- đưa logo hiện tại vào một hình vuông;
- đặt logo hiện tại trong tờ PDF;
- đổi màu logo hiện tại thành vàng.

Mục tiêu là:

> **Tạo một symbol mới hoàn toàn dựa trên ý niệm “G + Sign”.**

---

# 17. WINDOWS SHORTCUT OVERLAY

Windows có thể chèn shortcut overlay vào icon.

AI phải kiểm tra:

```text
Original EXE icon
        ↓
Desktop shortcut
        ↓
Windows shortcut overlay
```

Overlay không được che mất:

- G;
- signature stroke;
- verification gesture.

Vì vậy phải chừa một vùng an toàn ở góc dưới.

---

# 18. TASKBAR

Phải test khi icon chỉ còn khoảng:

**16–24 px**

Mục tiêu:

Người dùng nhìn thoáng qua vẫn biết:

> “Đây là Golden Signing.”

Không được để phần signature stroke biến mất hoàn toàn.

---

# 19. START MENU / SEARCH

Test:

**32 px / 48 px / 64 px**

Không có text bên trong icon.

Tên:

**Golden Signing**

sẽ do Windows hiển thị bên cạnh.

---

# 20. APPLICATION WINDOW ICON

Icon cũng phải được sử dụng ở title bar:

`[G-SIGN] Golden Signing`

Không dùng logo Golden Logistics ở title bar.

---

# 21. SPLASH SCREEN

Splash screen có thể sử dụng:

`G-SIGN + Golden Signing + Golden Logistics`

nhưng đây là **marketing composition**, không phải app icon.

---

# 22. ABOUT SCREEN

About screen có thể hiển thị:

```text
        [G-SIGN]

      Golden Signing

      Version 1.x.x

Developed by HOC HK
Golden Logistics
```

Logo Golden Logistics có thể đặt nhỏ hơn bên dưới.

---

# 23. NOTIFICATION

Windows notification có thể dùng:

```text
[G-SIGN]
Golden Signing

Ký số thành công
```

Không sử dụng full Golden Logistics logo trong notification.

---

# 24. DESIGN LANGUAGE

G-Sign phải tạo cảm giác:

- **40%** Golden / Premium
- **30%** Digital / Technology
- **20%** Trust / Verification
- **10%** PDF / Document

Không đảo ngược thành một icon PDF thông thường.

---

# 25. NHỮNG THỨ PHẢI TRÁNH

Không thiết kế:

- tờ giấy PDF với dấu tick;
- USB Token;
- chữ ký tay màu xanh;
- con dấu đỏ;
- ổ khóa;
- khiên bảo mật quá rõ;
- đám mây;
- thư mục;
- chữ GS lớn;
- chữ G dạng font thông thường;
- icon scan;
- icon printer;
- icon Acrobat-like;
- icon Microsoft-like.

Đặc biệt:

**Không làm icon giống Adobe Acrobat.**

---

# 26. UNIQUE SILHOUETTE TEST

AI phải đặt icon cạnh các nhóm icon phổ biến như:

- Adobe Acrobat
- Foxit
- PDF24
- Microsoft Edge PDF
- LibreOffice
- SignNow
- DocuSign
- các ứng dụng ký số khác

và kiểm tra:

> Khi làm mờ / thu nhỏ / nhìn nhanh, icon Golden Signing có bị nhầm với icon nào không?

Nếu có, phải redesign.

---

# 27. BLUR TEST

AI phải thực hiện:

### Test 1 — Blur

Gaussian blur nhẹ.

Nếu silhouette vẫn nhìn ra chữ G → Pass.

### Test 2 — 16 px

Scale xuống 16 px.

Nếu vẫn nhận ra G-Sign → Pass.

### Test 3 — Grayscale

Nếu vẫn nhận diện được → Pass.

### Test 4 — Silhouette only

Chuyển toàn bộ icon thành màu đen.

Nếu vẫn đẹp → Pass.

---

# 28. MIRROR TEST

Lật ngang logo.

Nếu hình bị mất cân bằng nghiêm trọng → cần cải thiện geometry.

Không bắt buộc logo phải đối xứng.

Nhưng optical balance phải tốt.

---

# 29. OPTICAL BALANCE

Không đánh giá chỉ bằng toán học.

Designer cần kiểm tra:

- trọng tâm thị giác;
- khoảng âm;
- trọng lượng nét;
- hướng chuyển động của signature stroke.

Signature stroke nên tạo cảm giác:

**đang “ký” / “xác nhận”**

chứ không chỉ là một đường cong.

---

# 30. MOTION CONCEPT

Không cần animation trong icon Windows.

Tuy nhiên AI nên thiết kế để sau này có thể dùng animation nhỏ trong UI:

```text
G
↓
signature stroke
↓
verification
```

Ví dụ animation khi:

**Ký thành công**

G-Sign sáng nhẹ hoặc signature stroke chạy một lần.

Đây là yêu cầu optional cho tương lai, không đưa animation vào ICO.

---

# 31. AI DESIGN PROCESS

AI MUST NOT immediately generate final asset.

Phải thực hiện:

### Phase 1 — Research

Nghiên cứu:

- Windows icon design
- modern desktop app branding
- digital signing products
- enterprise software iconography
- existing Golden Logistics branding
- icon behavior at small sizes
- Windows shortcut and taskbar constraints

### Phase 2 — Concept Exploration

Tạo tối thiểu:

**5 concept**

### Phase 3 — Comparison

Đánh giá:

| Tiêu chí | Điểm |
|---|---:|
| Recognizability | /10 |
| Uniqueness | /10 |
| Golden relationship | /10 |
| Digital signature meaning | /10 |
| Windows compatibility | /10 |
| Small-size readability | /10 |
| Professionalism | /10 |
| Memorability | /10 |

### Phase 4 — Select

Chọn 1 concept.

### Phase 5 — Geometry

Xây dựng vector geometry.

### Phase 6 — Small Size Optimization

Tối ưu riêng cho:

16 / 20 / 24 / 32 px.

### Phase 7 — Color

Test:

- light;
- dark;
- grayscale;
- transparent.

### Phase 8 — Final Assets

Xuất SVG / PNG / ICO.

---

# 32. REQUIRED DELIVERABLES

AI phải tạo:

```text
ICON_DESIGN_REVIEW.md

G_SIGN_CONCEPTS/
├── concept-a.svg
├── concept-b.svg
├── concept-c.svg
├── concept-d.svg
├── concept-e.svg
└── comparison.md

branding/
└── golden-signing/
    ├── golden-signing.svg
    ├── golden-signing-512.png
    ├── golden-signing-256.png
    └── golden-signing.ico
```

Nếu môi trường coding project đã có cấu trúc asset riêng, AI được phép điều chỉnh vị trí thư mục nhưng phải giữ tên file master hoặc ghi rõ mapping.

---

# 33. DESIGN DECISION RECORD

Sau khi chọn concept cuối cùng phải tạo:

```text
ADR-GSIGN-001.md
```

Nội dung:

- Why G-Sign
- Why this geometry
- Why this color
- Why this signature stroke
- Why alternatives were rejected
- Small-size decisions
- Windows decisions
- Brand relationship

---

# 34. AI REVIEW GATE

Trước khi merge vào project, phải review bởi:

### UX Reviewer

Kiểm tra recognizability.

### Branding Reviewer

Kiểm tra Golden brand.

### Windows UI Reviewer

Kiểm tra Windows integration.

### Accessibility Reviewer

Kiểm tra grayscale / contrast.

### Engineering Reviewer

Kiểm tra ICO/SVG/asset pipeline.

### Final Decision

Chỉ merge khi tất cả Gate đạt.

---

# 35. ACCEPTANCE CRITERIA

Logo chỉ được coi là hoàn thành khi:

[ ] Tạo được symbol G-Sign độc lập.  
[ ] Không sao chép logo Golden Logistics.  
[ ] Nhìn ra chữ G.  
[ ] Có cảm giác digital signing.  
[ ] Có cảm giác verification/trust.  
[ ] Không giống icon PDF reader.  
[ ] Không giống antivirus.  
[ ] Không giống Adobe/Foxit/PDF24.  
[ ] Nhận diện tốt ở 16×16.  
[ ] Nhận diện tốt ở 24×24.  
[ ] Nhận diện tốt ở 32×32.  
[ ] Nhận diện tốt ở 48×48.  
[ ] Nhận diện tốt ở 256×256.  
[ ] Hoạt động trên nền trắng.  
[ ] Hoạt động trên nền tối.  
[ ] Hoạt động khi transparent.  
[ ] Hoạt động ở grayscale.  
[ ] Không cần text để nhận diện.  
[ ] Không bị mất nét khi Windows rasterize.  
[ ] Desktop shortcut vẫn nhận diện tốt.  
[ ] Taskbar vẫn nhận diện tốt.  
[ ] EXE có icon chính xác.  
[ ] Không làm thay đổi logo Golden Logistics hiện tại.

---

# 36. FINAL DESIGN PRINCIPLE

Golden Signing không nên có một icon kiểu:

> “PDF + dấu tick”.

Golden Signing phải có một biểu tượng riêng:

> **“G đang ký.”**

Đây là câu chuyện thị giác cốt lõi của G-Sign.

Người dùng nhìn thấy biểu tượng phải có cảm giác:

**Golden → Sign → Verified**

mà không cần đọc chữ.

---

# 37. KHUYẾN NGHỊ BỔ SUNG — CORE VÀ PREMIUM

AI nên tạo **2 phiên bản G-Sign** trong quá trình thiết kế:

### G-Sign Core

Cực kỳ đơn giản, tối ưu:

- 16 px
- 20 px
- 24 px
- 32 px

Đây là phiên bản bắt buộc phải hoạt động tốt trên Taskbar/Desktop.

### G-Sign Premium

Nhiều chi tiết hơn, tối ưu:

- 128 px
- 256 px
- 512 px

Phiên bản này có thể được dùng trong:

- Installer
- About
- Splash
- Marketing preview
- Store/website nếu cần

Nhưng cả hai phải xuất phát từ **cùng một geometry master**, không trở thành hai logo khác nhau.

---

# 38. YÊU CẦU ĐỐI VỚI AI CODING/DESIGN AGENT

**KHÔNG CODE NGAY.**

Trước tiên phải:

```text
READ DESIGN SKILLS
        ↓
RESEARCH
        ↓
ICON DESIGN REVIEW
        ↓
5 CONCEPTS
        ↓
COMPARE
        ↓
SELECT
        ↓
DESIGN SYSTEM
        ↓
SMALL SIZE TEST
        ↓
FINAL VECTOR
        ↓
WINDOWS ICO
        ↓
ENGINEERING INTEGRATION
```

AI phải sử dụng **ui-ux-pro-max-skill** và các skill thiết kế/brand/icon tốt nhất đang có trước khi triển khai.

Nếu skill không tồn tại trong môi trường, AI phải báo rõ và tìm skill tương đương, không tự ý bỏ qua bước design review.

---

# 39. ĐIỀU KIỆN BẮT BUỘC VỀ TÀI SẢN ĐẦU VÀO

File logo Golden Logistics hiện tại là **brand reference**, không phải artwork để biến đổi trực tiếp thành app icon.

AI phải:

- giữ nguyên logo gốc;
- không overwrite;
- không recolor;
- không crop;
- không chỉnh sửa nếu chưa được yêu cầu;
- chỉ tham khảo hình học/thẩm mỹ để xây dựng brand relationship.

Nếu project đã có file:

`golden.svg`

hoặc logo Golden Logistics tương đương, phải giữ nguyên file gốc và tạo asset mới cho Golden Signing.

---

# 40. KẾT QUẢ MONG MUỐN

Kết quả cuối cùng cần làm cho người dùng có cảm giác:

> “Đây là một ứng dụng ký số chuyên nghiệp của Golden.”

chứ không phải:

> “Đây là một file PDF có dấu tick.”

Biểu tượng tốt nhất là biểu tượng mà sau khi nhìn 1–2 giây, người dùng có thể nhớ được hình dạng của nó.

**Golden Signing = G-Sign.**
