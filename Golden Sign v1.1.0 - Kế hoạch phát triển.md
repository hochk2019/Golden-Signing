# GOLDEN SIGNING — KẾ HOẠCH PHÁT TRIỂN v1.1.0

**Tên sản phẩm:** Golden Signing  
**Phiên bản hiện tại:** v1.0.0  
**Phiên bản mục tiêu:** v1.1.0  
**Định hướng:** Windows desktop application chuyên ký số PDF/chứng từ, hỗ trợ ký hàng loạt ổn định, tương thích hệ thống Hải quan PUS, đồng thời bổ sung chuyển Word/Excel → PDF và nén PDF thông minh trước khi ký.  
**Nhà phát triển:** HOC HK  
**Email:** hochk2019@gmail.com  
**Điện thoại:** 0868.333.606  
**Thông tin dịch vụ:** Cung cấp dịch vụ tư vấn hải quan miễn phí - vận chuyển hàng hóa toàn quốc.

---

## 0. Mục tiêu của tài liệu

Đây là tài liệu giao việc cho AI Coding Agent để review và phát triển Golden Signing từ v1.0.0 lên v1.1.0.

AI Agent phải đọc toàn bộ tài liệu trước khi code. Không được coi đây là danh sách tính năng đơn giản. v1.1.0 phải được triển khai theo pipeline an toàn:

```text
Review codebase
→ Review UX/UI
→ Review architecture
→ Review PDF/signing pipeline
→ Review Office conversion
→ Review compression engine
→ Chốt ADR
→ Viết tests
→ Implement từng module
→ Integration test
→ Regression test
→ AI review độc lập
→ Security/license review
→ Packaging
→ Release candidate
→ Validation trên Golden samples
→ v1.1.0
```

Không được sửa Signing Core đang ổn định chỉ để phục vụ UI mới nếu chưa có regression tests bảo vệ.

---

# 1. Tóm tắt yêu cầu v1.1.0

## 1.1. Tính năng bắt buộc

### A. Hỗ trợ Word/Excel

Cho phép thêm trực tiếp:

- `.doc`
- `.docx`
- `.xls`
- `.xlsx`

Có thể thiết kế kiến trúc mở để về sau hỗ trợ `.xlsm`, `.docm`, `.odt`, `.ods`, nhưng **v1.1.0 không tự động xử lý macro-enabled files nếu chưa có test và chính sách bảo mật riêng**.

Ứng dụng phải:

1. Tự nhận diện loại file.
2. Hiển thị biểu tượng/nhãn Word hoặc Excel.
3. Không thay đổi file gốc.
4. Chuyển sang PDF trong thư mục temporary/workspace.
5. Kiểm tra PDF tạo ra.
6. Chuyển qua pipeline nén nếu người dùng chọn “Nén và ký số”.
7. Ký số PDF sau cùng.
8. Verify chữ ký.
9. Chỉ commit output khi tất cả các bước thành công.

Pipeline:

```text
DOC/DOCX/XLS/XLSX
       ↓
Office/LibreOffice Converter
       ↓
PDF intermediate
       ↓
Preflight
       ↓
Compression (optional)
       ↓
PDF final unsigned
       ↓
Signing Core
       ↓
Cryptographic Verification
       ↓
Output Commit
```

### B. Nén PDF

Thêm nút:

**Nén và ký số**

đặt ngay dưới/nằm cạnh nút **KÝ SỐ** theo layout thực tế của v1.0.0.

Thêm nút:

**Cài đặt nén**

Tách riêng khỏi `Cài đặt` nếu giao diện hiện tại đã có trang Settings tổng quát, hoặc mở một panel/modal compression settings trong Settings. Không làm giao diện chính chật chội.

### C. Nén thông minh

Không coi “nén PDF” chỉ là giảm chất lượng ảnh.

Compression Engine phải phân tích:

- file size
- số trang
- page dimensions
- image count
- image dimensions
- image color space
- image compression/filter
- font information
- forms
- annotations
- attachments
- metadata
- embedded thumbnails
- structural objects
- vector/text ratio
- encrypted/password protected state
- existing signatures

Sau đó chọn chiến lược nén thích hợp.

### D. Ghi nhớ cài đặt nén

Compression profile phải được lưu riêng, tương tự Signature Profile.

Ví dụ:

```text
PUS Safe Compression
Balanced
Small File
Maximum Compression
Custom
```

Cài đặt gần nhất phải được ghi nhớ.

### E. “Nén và ký số” phải nén TRƯỚC rồi mới ký

Tuyệt đối không:

```text
PDF → Sign → Compress
```

vì mọi thay đổi lên phần PDF đã được bảo vệ có thể làm chữ ký không còn hợp lệ.

Đúng:

```text
PDF → Compress → Finalize PDF → Sign → Verify
```

Đối với Word/Excel:

```text
Word/Excel → PDF → Compress → Sign → Verify
```

---

# 2. Đánh giá tính khả thi

## 2.1. Word/Excel → PDF

**Khả thi cao.**

Microsoft Office cung cấp API `ExportAsFixedFormat` cho Excel và Word để xuất PDF/XPS; Excel cho phép lựa chọn quality và print areas. Word cho phép chọn tối ưu cho screen/print và các tham số liên quan tới PDF. Nguồn chính thức:

- https://learn.microsoft.com/en-us/office/vba/api/excel.workbook.exportasfixedformat
- https://learn.microsoft.com/en-us/office/vba/api/word.range.exportasfixedformat

Tuy nhiên, Microsoft cảnh báo Office Automation trong môi trường unattended/non-interactive có thể không ổn định và không được họ hỗ trợ cho các server/service scenario. Golden Signing là desktop interactive application, nhưng Agent vẫn phải thiết kế quá trình COM automation có kiểm soát, không biến Word/Excel thành Windows service và không chạy hàng chục instance song song. 

Nguồn: https://learn.microsoft.com/en-us/office/client-developer/integration/considerations-unattended-automation-office-microsoft-365-for-unattended-rpa

## 2.2. LibreOffice fallback

LibreOffice hỗ trợ chuyển đổi bằng `--convert-to` và `--outdir`, phù hợp làm fallback khi Microsoft Office không có hoặc không thể sử dụng.

Nguồn chính thức:

https://help.libreoffice.org/latest/uk/text/shared/guide/start_parameters.html

Không được coi LibreOffice output luôn giống Microsoft Office 100%. Với file Word/Excel phức tạp phải có compatibility test.

## 2.3. Nén PDF

**Khả thi cao**, nhưng phải chia làm nhiều lớp.

QPDF phù hợp cho tối ưu lossless/structural và có các cơ chế `--compress-streams`, `--recompress-flate`, `--compression-level`, `--object-streams=generate`, `--optimize-images`. QPDF không phải công cụ resample ảnh tổng quát, nên Golden Signing cần thêm image-aware compression layer nếu muốn đạt các ngưỡng dung lượng rất thấp.

Nguồn:

https://qpdf.readthedocs.io/en/latest/cli.html
https://qpdf.readthedocs.io/en/stable/license.html

QPDF được phát hành theo Apache License 2.0.

## 2.4. Ghostscript

Ghostscript rất mạnh cho PDF conversion/compression, nhưng bản AGPL và bản thương mại có yêu cầu cấp phép khác nhau. Nếu Golden Signing là phần mềm proprietary/closed-source và phân phối Ghostscript kèm sản phẩm, **không được tự ý bundle bản AGPL**. Phải mua commercial license hoặc loại bỏ Ghostscript khỏi build phân phối.

Nguồn chính thức:

https://ghostscript.com/faq/
https://www.ghostscript.com/releases/gsdnld.html

Do đó v1.1.0 nên thiết kế `CompressionProvider` để không khóa vào Ghostscript.

---

# 3. Quyết định kiến trúc v1.1.0

```text
Golden Signing Desktop
│
├── UI Layer (PySide6)
│
├── Application Layer
│   ├── File Queue
│   ├── Workflow Orchestrator
│   ├── Profile Manager
│   ├── Compression Manager
│   └── Conversion Manager
│
├── Document Layer
│   ├── PDF Analyzer
│   ├── PDF Preflight
│   ├── Office Converter
│   ├── Compression Engine
│   └── PDF Validator
│
├── Signing Layer
│   ├── Signing Core
│   ├── Token Manager
│   ├── Certificate Manager
│   ├── Signature Profile
│   └── Signature Validator
│
├── Infrastructure
│   ├── SQLite
│   ├── Logging
│   ├── Temporary Workspace
│   ├── Update Service
│   └── Diagnostics
│
└── External Providers
    ├── Windows Office
    ├── LibreOffice
    ├── QPDF
    ├── PKCS#11
    └── Windows Crypto APIs
```

Không để UI gọi trực tiếp qpdf/Office/token APIs. Tất cả phải đi qua service/interface.

---

# 4. File type pipeline

## 4.1. File type registry

Tạo:

```python
DocumentType.PDF
DocumentType.WORD
DocumentType.EXCEL
DocumentType.UNKNOWN
```

Extension chỉ là tín hiệu ban đầu. Không tin extension tuyệt đối. Nên kiểm tra magic/header/container nếu có thể.

## 4.2. Status mới cho queue

Mỗi file có state machine:

```text
ADDED
→ DETECTING
→ READY
→ CONVERTING
→ CONVERTED
→ PREFLIGHT
→ COMPRESSING
→ COMPRESSED
→ WAITING_TOKEN
→ SIGNING
→ VERIFYING
→ SUCCESS
```

Nhánh lỗi:

```text
CONVERSION_FAILED
COMPRESSION_FAILED
PREFLIGHT_FAILED
TOKEN_FAILED
SIGN_FAILED
VERIFY_FAILED
OUTPUT_FAILED
```

Không dùng một trạng thái “ERROR” chung chung.

---

# 5. Word/Excel Conversion Engine

## 5.1. Provider architecture

```python
class OfficeConversionProvider(Protocol):
    def can_convert(self, file_path: Path) -> bool: ...
    def convert_to_pdf(self, source: Path, output: Path, options: ConversionOptions) -> ConversionResult: ...
```

Implement:

```text
MicrosoftOfficeProvider
LibreOfficeProvider
```

## 5.2. Microsoft Office provider

Nếu Word/Excel được cài:

- phát hiện cài đặt
- phát hiện version
- kiểm tra COM availability
- tạo process/session kiểm soát
- tuyệt đối không chạy macro
- tắt alerts không cần thiết
- không lưu đè source
- đóng document
- đóng application
- kill process còn sót chỉ sau khi đã thử cleanup an toàn
- không chạy song song nhiều Word/Excel instance trên cùng user session trừ khi test chứng minh an toàn

### Excel

Cần hỗ trợ cấu hình:

- dùng print area hay toàn workbook
- quality standard/minimum
- include document properties
- page range
- worksheet/book scope nếu cần

Mặc định: giữ print area nếu file đã cấu hình print area hợp lệ.

### Word

Cần hỗ trợ:

- optimize for screen / print
- bookmarks
- document structure tags
- ISO 19005/PDF-A chỉ khi người dùng yêu cầu
- include properties

Mặc định: ưu tiên fidelity hiển thị hơn size; compression engine xử lý size ở bước sau.

## 5.3. LibreOffice provider

Dùng `soffice --headless --convert-to pdf --outdir ...` với isolated user profile cho mỗi conversion job/session khi cần.

Không chạy chung user profile LibreOffice với phiên người dùng nếu có nguy cơ lock profile.

## 5.4. Conversion validation

Sau conversion phải kiểm tra:

- file tồn tại
- size > 0
- mở được như PDF
- số trang > 0
- render page 1 thành công
- không bị page trắng bất ngờ
- không lỗi parser

Đối với Excel:

- test print area
- merged cells
- formulas
- hidden sheets
- charts
- images
- landscape/portrait
- page scaling

Đối với Word:

- images
- tables
- headers/footers
- page breaks
- Vietnamese Unicode
- custom fonts
- hyperlinks
- footnotes/endnotes

---

# 6. Compression Engine

## 6.1. Nguyên tắc

Compression Engine phải cố đạt **dung lượng thấp nhất có thể mà vẫn giữ chất lượng theo profile và giữ tính sử dụng của tài liệu**.

Không hứa “file nào cũng xuống dưới 400 KB”. Có những PDF chứa quá nhiều ảnh hoặc vector phức tạp mà không thể đạt 400 KB mà không làm giảm chất lượng mạnh.

UI phải nói rõ:

```text
Mục tiêu: ≤ 400 KB
Kết quả tối ưu: 427 KB
Không nên nén thêm vì sẽ làm giảm chất lượng dưới ngưỡng đã chọn.
```

## 6.2. Target size

Cho phép:

```text
Tự động
100 KB
150 KB
200 KB
250 KB
300 KB
350 KB
400 KB
500 KB
1 MB
Tùy chỉnh
```

Nhưng profile phải có:

**Target final signed size**

thay vì chỉ “target unsigned size”.

Lý do: chữ ký sẽ thêm bytes vào output.

Có tham số:

```text
Signature overhead reserve:
- Auto learned
- 16 KB
- 32 KB
- 64 KB
- 128 KB
- Custom
```

Auto learned dựa trên lịch sử các lần ký thành công của cùng Signature Profile nếu đủ dữ liệu.

## 6.3. Compression tiers

### Level 0 — Lossless

- object streams
- recompress flate
- compression level 9
- remove unused structures nếu an toàn
- remove metadata nếu user chọn
- strip thumbnails nếu an toàn
- optimize structural streams
- optimize images nếu hoàn toàn không làm giảm chất lượng hoặc qpdf chứng minh output nhỏ hơn

### Level 1 — Balanced

- Level 0
- optimize images
- resize oversized raster images
- JPEG quality 75–85
- target DPI khoảng 150–220 tùy content

### Level 2 — Strong

- image resampling
- JPEG quality 55–75
- DPI khoảng 120–180
- grayscale nếu user bật
- remove optional metadata/thumbnails/attachments

### Level 3 — PUS Compact

- ưu tiên text/vector
- giữ khả năng đọc/search text nếu PDF có text layer
- raster images khoảng 120–150 DPI tùy kích thước trang và loại tài liệu
- JPEG quality khoảng 55–70 tùy test
- metadata stripping theo profile
- tuyệt đối không flatten/rasterize toàn trang mặc định

### Level 4 — Maximum / Extreme

Chỉ hiện khi user bật “Cho phép giảm mạnh chất lượng”.

Có thể:

- grayscale
- 96–120 DPI
- JPEG quality thấp hơn
- rasterize một số vector-heavy content

Nhưng **PUS Safe không được tự động dùng Level 4**.

---

# 7. Intelligent Compression Algorithm

Không chạy một preset duy nhất. Dùng iterative optimization.

```text
Analyze
  ↓
Lossless pass
  ↓
Measure
  ↓
If target met → done
  ↓
Image optimization
  ↓
Measure
  ↓
If target met → done
  ↓
Downsample/resample
  ↓
Measure
  ↓
If target met → done
  ↓
Grayscale if allowed
  ↓
Measure
  ↓
If target still not met:
  show “quality floor reached”
```

Mỗi lần tạo candidate output:

1. viết file temporary
2. parse lại PDF
3. render representative pages
4. kiểm tra text extraction cơ bản
5. kiểm tra page count
6. so sánh kích thước
7. giữ candidate tốt nhất

Không overwrite file gốc trong quá trình thử.

---

# 8. Image-aware compression

PikePDF có API kiểm tra và thay thế image objects trong PDF, nên có thể dùng làm image processing layer kết hợp Pillow; cần test kỹ với các color spaces và shared image objects.

Nguồn:
https://pikepdf.readthedocs.io/en/stable/topics/images.html

Cần xử lý:

- RGB
- grayscale
- CMYK nếu có
- alpha/transparency
- JPEG
- JPEG2000 nếu giữ nguyên an toàn
- Flate/PNG-like image streams
- inline images
- image XObjects

Không convert mù mọi thứ sang JPEG.

Ví dụ:

- chữ scan đen trắng → ưu tiên grayscale/1-bit strategy nếu đọc được
- tài liệu màu → giữ màu nếu cần
- logo/con dấu → giữ đủ chất lượng
- ảnh photograph → JPEG phù hợp
- text/vector → không rasterize chỉ vì cần giảm size

---

# 9. Chế độ nén đặc biệt “PUS Safe < 400 KB”

Người dùng có yêu cầu thực tế rằng PUS thường khó xử lý file ký số lớn hơn khoảng 400 KB.

Đây được coi là **business requirement của môi trường sử dụng**, không phải tuyên bố chính thức rằng PUS áp một ngưỡng 400 KB cho mọi hồ sơ.

UI nên có profile:

**PUS Safe – mục tiêu 400 KB**

Flow:

```text
User chọn PUS Safe
        ↓
Target final signed size = 400 KB
        ↓
Estimate signature overhead
        ↓
Compression target for unsigned PDF
        ↓
Compress
        ↓
Sign
        ↓
Verify
        ↓
Measure final size
```

Nếu output vẫn >400 KB:

```text
Không tự động sửa/chèn lại chữ ký.
Hiển thị:
Final size: 428 KB
Target: 400 KB
Status: Target not reached
Recommendation: chọn compression mạnh hơn.
```

Optional advanced setting:

**Cho phép tự động thử lại nén + ký nếu vượt target**

Nhưng phải cảnh báo rằng mỗi lần retry có thể yêu cầu thao tác/token authorization lại.

---

# 10. Không phá chữ ký hiện có

Compression engine phải kiểm tra:

```text
Existing signature present?
```

Nếu có chữ ký:

**Không nén trực tiếp file signed.**

Hiển thị:

> File đã có chữ ký số. Việc nén/chỉnh sửa file có thể làm chữ ký hiện tại không còn hợp lệ.

Cho lựa chọn:

- Cancel
- Tạo bản sao chưa ký nếu có nguồn gốc phù hợp
- Continue only with explicit advanced confirmation

Không được âm thầm làm mất chữ ký.

---

# 11. Cài đặt nén — UX

Thiết kế dialog:

```text
┌─────────────────────────────────────────────┐
│ CÀI ĐẶT NÉN PDF                         X   │
├─────────────────────────────────────────────┤
│ Profile: [PUS Safe ▼]                       │
│                                             │
│ Mục tiêu dung lượng                         │
│ ○ Tự động                                   │
│ ● ≤ 400 KB                                  │
│ ○ Tùy chỉnh [____] KB                       │
│                                             │
│ Chất lượng                                  │
│ [Thấp ─────●───── Cao]                     │
│                                             │
│ DPI ảnh: [150 ▼]                            │
│ JPEG quality: [70 ▼]                        │
│                                             │
│ ☑ Giữ text/vector nguyên bản                │
│ ☑ Giữ màu                                   │
│ ☐ Chuyển ảnh sang grayscale                 │
│ ☑ Xóa metadata không cần thiết              │
│ ☐ Xóa attachment                             │
│ ☐ Xóa annotation                             │
│ ☐ Xóa outline                                │
│ ☐ Cho phép giảm chất lượng mạnh              │
│                                             │
│ ☑ Ghi nhớ cài đặt này                       │
│                                             │
│ [Khôi phục mặc định]    [Lưu]               │
└─────────────────────────────────────────────┘
```

Không được để người dùng phổ thông phải hiểu Ghostscript/QPDF flags.

Advanced options có thể mở accordion riêng.

---

# 12. UI Main v1.1.0

UI hiện tại v1.0.0 có:

- Ký tài liệu
- Kéo PDF vào đây
- Thêm PDF
- Thêm thư mục
- Quét lại token
- Profile PUS Safe
- Danh sách file
- Thư mục output
- Cài đặt ký
- Ký lại lỗi
- Xóa danh sách ký
- KÝ SỐ

v1.1.0 giữ nguyên bố cục tổng thể để người dùng v1.0 không bị “lạc”, chỉ mở rộng khả năng.

## 12.1. Drop zone

Text phải đổi từ:

`Kéo thả PDF vào đây`

thành:

`Kéo thả PDF, Word hoặc Excel vào đây`

Subtitle nhỏ:

`PDF • DOC • DOCX • XLS • XLSX`

## 12.2. File list

Thêm cột:

```text
Loại | Tên file | Dung lượng | Trạng thái | Hành động
```

Ví dụ:

```text
[PDF]  abc.pdf      812 KB    Sẵn sàng
[W]    hopdong.docx  1.2 MB   Chờ chuyển PDF
[X]    bangke.xlsx   2.4 MB   Chờ chuyển PDF
```

## 12.3. Primary actions

Giữ:

**KÝ SỐ**

Thêm:

**NÉN VÀ KÝ SỐ**

Thêm secondary action:

**CÀI ĐẶT NÉN**

Nút `Nén và ký số` nên disable nếu queue không có file hợp lệ.

## 12.4. Smart action

Có thể thêm:

**Tác vụ nhanh ▼**

- Ký số
- Nén và ký số
- Chỉ nén PDF
- Chuyển Office → PDF
- Chuyển + nén + ký

Không đưa quá nhiều nút vào toolbar.

---

# 13. Smart profile

Mở rộng hệ thống profile từ v1.0:

```text
Signature Profile
Compression Profile
Conversion Profile
```

Một workflow profile có thể kết hợp cả ba:

```text
PUS Safe - Company A
├── Certificate fingerprint
├── Signature appearance
├── Visible/Invisible
├── PAdES/compatibility mode
├── Compression profile
├── Conversion profile
└── Output naming
```

Khi token của Company A được chọn:

```text
certificate fingerprint
        ↓
load profile Company A
        ↓
load logo
load appearance
load compression preset
load output settings
```

Nếu profile không tồn tại:

`Tạo profile cho chứng thư này?`

---

# 14. Compression profile persistence

SQLite model đề xuất:

```text
compression_profiles
---------------------
id
name
mode
target_size_bytes
quality
image_dpi
jpeg_quality
gray_scale
preserve_text_vector
strip_metadata
strip_thumbnails
strip_attachments
strip_annotations
strip_outline
allow_extreme
is_default
created_at
updated_at
```

Không lưu path tuyệt đối của source file trong compression profile.

---

# 15. Database changes

Mở rộng bảng `documents/jobs` hiện tại tùy codebase thực tế.

Thông tin nên có:

```text
document_id
source_path
source_type
source_size
intermediate_pdf_path
after_compression_size
final_signed_size
compression_profile_id
signature_profile_id
conversion_provider
compression_provider
signing_provider
workflow_type
current_state
error_code
error_message_user
created_at
completed_at
```

Lưu checksum SHA-256 của source và output nếu phù hợp.

Không lưu PIN/private key.

---

# 16. Output naming

Ví dụ:

```text
contract.docx
→ contract.pdf
→ contract_compressed.pdf
→ contract_signed.pdf
```

Nhưng mặc định người dùng không nên bị buộc phải thấy cả intermediate files.

Nên có output modes:

```text
1. Chỉ xuất kết quả cuối
2. Giữ PDF trung gian
3. Giữ tất cả intermediate khi Debug
```

PUS Safe production profile: `Chỉ xuất kết quả cuối`.

---

# 17. Atomic output

Mọi output phải đi qua:

```text
.temp
  ↓
write
  ↓
fsync/close
  ↓
validate
  ↓
rename/move atomic
```

Không ký trực tiếp vào file đích nếu chưa chuẩn bị xong.

Nếu process crash:

- source vẫn còn nguyên
- output partial nằm trong temp
- lần mở app sau phải dọn temp an toàn

---

# 18. Retry/resume

v1.1.0 phải tiếp tục cơ chế anti-forgetting và job persistence đã thiết kế ở v1.2 specification.

Mỗi file phải có checkpoint:

```text
DETECTED
CONVERTED
COMPRESSED
SIGNED
VERIFIED
COMMITTED
```

Nếu app bị tắt:

```text
Startup Recovery
↓
scan unfinished jobs
↓
validate artifacts
↓
resume from safest checkpoint
```

Không resume blindly một signed output chưa verify.

---

# 19. Test matrix cho Office conversion

## Word

- DOC/DOCX tiếng Việt
- nhiều trang
- bảng lớn
- hình ảnh lớn
- header/footer
- logo
- chữ ký ảnh
- font Tahoma/Arial/Times New Roman/Segoe UI
- Unicode Vietnamese
- hyperlinks
- page break
- section break
- landscape/portrait
- embedded image
- document properties

## Excel

- XLS/XLSX
- nhiều sheet
- hidden sheet
- print area
- print titles
- merged cells
- formulas
- charts
- images
- page break
- page scaling
- landscape
- portrait
- wide tables
- Vietnamese text

Acceptance criterion:

PDF phải mở được, không lỗi parser, số trang hợp lý và render không bị mất nội dung quan trọng.

---

# 20. Test matrix compression

Tạo dataset benchmark:

```text
01_text_only.pdf
02_scan_bnw.pdf
03_scan_color.pdf
04_photo_heavy.pdf
05_mixed_text_image.pdf
06_vector_heavy.pdf
07_form_pdf.pdf
08_annotation_pdf.pdf
09_attachment_pdf.pdf
10_large_100_pages.pdf
11_already_compressed.pdf
12_hai_quan_sample.pdf
13_ecus_signed_sample.pdf
```

### Critical regression sample

Bắt buộc dùng bản gốc Hải quan đã cung cấp:

`6.Chung tu khai bs_106960399450_H11-tong(1).pdf`

Mục tiêu:

```text
Original
→ Compress
→ Sign
→ Verify
```

Không được làm mất nội dung con dấu đỏ/chữ ký xanh đang có sẵn trong tài liệu.

---

# 21. Test PUS compatibility

Không tuyên bố compatibility chỉ bằng unit test.

Test levels:

### Level A — Structural

- valid PDF
- valid AcroForm
- valid signature field
- valid ByteRange
- valid CMS

### Level B — Cryptographic

- signature validates
- certificate chain parses
- signing time parses
- profile is accepted by PDF validation tools

### Level C — Viewer

- Acrobat/Adobe Reader
- Edge PDF viewer
- other common validator

### Level D — PUS

Upload thật vào:

https://pus.customs.gov.vn/faces/Home

Ghi nhận:

- accepted
- rejected
- error message
- file size
- certificate
- signature profile
- PDF characteristics

Tạo report cho từng build.

---

# 22. Signature-safe compression rule

**Không bao giờ chạy compression provider trên final signed PDF trong workflow bình thường.**

Tổ chức pipeline thành:

```text
SourceArtifact
     ↓
WorkingPdf
     ↓
CompressedPdf
     ↓
SigningInput
     ↓
SignedPdf
     ↓
Validation
     ↓
Output
```

`SignedPdf` là immutable artifact.

---

# 23. Không đưa Ghostscript vào build mặc định nếu chưa xử lý license

Agent phải tạo capability matrix:

| Engine | Chức năng | License | Bundle default? |
|---|---|---|---|
| qpdf | structural/lossless/image optimize | Apache 2.0 | Có thể |
| pikepdf | inspect/modify PDF images | MPL 2.0 | Có thể, review license |
| Pillow | image resample/encode | permissive | Có thể |
| LibreOffice | Office→PDF fallback | MPL | Có thể, review package size/license |
| Ghostscript | advanced PDF compression | AGPL/commercial | Không mặc định nếu chưa xử lý license |
| Microsoft Office | high-fidelity Office→PDF | commercial software | Không bundle |

Agent phải tạo `THIRD_PARTY_LICENSES.md`.

---

# 24. PySide6 licensing gate

PySide6 Community Edition sử dụng LGPLv3/GPLv3; Qt cũng cung cấp commercial license. Nếu Golden Signing phát hành dưới dạng proprietary/closed-source, Agent phải thực hiện license review và xác định cách phân phối PySide6/Qt phù hợp trước release.

Nguồn chính thức:

https://doc.qt.io/qtforpython-6/commercial/index.html
https://doc.qt.io/qt-6/licensing.html

Không coi “pip install pyside6” là bằng chứng rằng licensing đã được giải quyết cho sản phẩm thương mại.

---

# 25. Performance goals

### Single PDF

- mở file và preflight không tạo cảm giác treo UI
- compression chạy background worker
- UI luôn responsive

### Batch

- không block UI
- mỗi file có progress
- không ký đồng thời trên cùng token
- preprocessing/compression có thể parallel có giới hạn

### Memory

Không load toàn bộ hàng trăm PDF vào RAM cùng lúc.

Dùng streaming/temp files khi có thể.

---

# 26. UI progress cho batch

Hiển thị:

```text
Đang xử lý 17 / 50

ABC.docx
✓ Chuyển PDF
✓ Nén: 1.2 MB → 287 KB
● Đang ký
○ Xác minh
```

Sau cùng:

```text
48 thành công
1 lỗi chuyển Word → PDF
1 không đạt mục tiêu 400 KB
```

Không dùng một progress bar duy nhất mà không có trạng thái từng file.

---

# 27. Error UX

Không hiển thị:

`Error -2147352567`

thẳng cho người dùng.

Phải có:

```text
Không thể chuyển file Excel sang PDF.

Nguyên nhân:
Excel không phản hồi.

Đề xuất:
- Đóng file Excel đang mở.
- Thử lại.
- Chuyển sang LibreOffice.

Mã kỹ thuật: OFFICE_COM_TIMEOUT
```

Có nút:

`Sao chép thông tin lỗi`

`Mở log`

---

# 28. Smart recommendations

Thêm hệ thống recommendation nhẹ:

### Ví dụ 1

Nếu PDF 4 MB, 95% dung lượng là ảnh:

> File chủ yếu là ảnh. Chọn “Balanced” có thể giảm dung lượng đáng kể.

### Ví dụ 2

Nếu PDF đã 180 KB:

> File đã nhỏ. Không nên nén thêm nếu ưu tiên chất lượng.

### Ví dụ 3

Nếu file đã có signature:

> Không nên nén trực tiếp vì có thể làm chữ ký hiện tại mất hiệu lực.

### Ví dụ 4

Nếu file Word chưa có PDF:

> Đã phát hiện Word. Khi ký, Golden Signing sẽ chuyển sang PDF trước.

---

# 29. Preview compression

Có thể bổ sung ở v1.1.0 nếu thời gian cho phép, nhưng ưu tiên sau core.

Dialog:

```text
Kích thước gốc: 2.31 MB
Dự kiến: 312 KB

Chất lượng ảnh: 75%
DPI: 150
Text/vector: giữ nguyên

[ Xem trước ]   [ Áp dụng ]
```

Preview không cần render toàn bộ file nếu quá lớn; chỉ render trang đại diện:

- trang 1
- trang nhiều ảnh nhất
- trang cuối

---

# 30. Signature + compression integration

Profile Signature và Compression phải có thể tách hoặc liên kết.

Ví dụ:

```text
Company A
│
├── Signature Profile: PUS Safe
│   ├── Invisible
│   ├── Token: certificate fingerprint
│   └── Appearance: template A
│
└── Compression Profile: PUS Safe 400 KB
    ├── Target final size: 400 KB
    ├── Preserve text/vector
    └── Balanced/Strong adaptive
```

Khi chọn Company A:

`Signature + Compression` có thể tự load.

Nhưng UI phải cho phép người dùng override tạm thời mà không sửa profile gốc.

---

# 31. File Explorer integration

Nếu v1.0 đã có hoặc kiến trúc cho phép, bổ sung:

- Right click PDF → Golden Signing → Ký số
- Right click PDF → Golden Signing → Nén và ký số
- Right click Word/Excel → Golden Signing → Chuyển + ký

Chỉ triển khai sau core UI ổn định.

---

# 32. Drag-and-drop

Mở rộng drop acceptance:

```text
PDF
DOC
DOCX
XLS
XLSX
```

Khi kéo file không hỗ trợ:

```text
File không được hỗ trợ: .zip
```

Không crash.

---

# 33. Security requirements

Office documents là input không tin cậy.

Agent phải giả định file có thể chứa:

- macro
- external links
- malformed structures
- embedded objects
- very large images
- path traversal filenames
- zip bombs trong Office containers

Không chạy macro.

Không tự mở hyperlink.

Không upload file lên cloud để conversion/compression mặc định.

Golden Signing phải hoạt động offline trừ update/remote signing nếu người dùng chủ động dùng.

---

# 34. Privacy

Mặc định:

- file không rời máy
- không telemetry nội dung document
- không gửi PDF lên server
- không gửi certificate/private key
- log chỉ lưu metadata cần thiết

Nếu có update checking:

chỉ gửi app version/channel/OS nếu chính sách đã công bố.

---

# 35. AI coding workflow

AI Agent phải làm theo các phase.

## Phase 0 — Repository audit

Không code.

Đọc:

- source tree
- dependency lockfile
- existing tests
- current signing pipeline
- DB schema
- profile system
- UI
- packaging
- update mechanism

Xuất:

```text
AI_REVIEW_V1_1.md
CURRENT_ARCHITECTURE.md
RISK_REGISTER.md
```

## Phase 1 — Skill research

Trước UI:

- đọc `ui-ux-pro-max-skill`
- thực hiện UX audit
- tạo `UX_BRIEF.md`
- tạo `DESIGN_TOKENS.md`

Trước backend:

- thực hiện backend architecture review
- tạo ADR

Trước database:

- schema review
- migration plan
- data integrity plan

Không code UI trước khi UX brief được review.

## Phase 2 — Compression spike

Làm prototype độc lập.

Dataset benchmark.

So sánh:

- qpdf
- pikepdf + Pillow
- optional engines

Đo:

- file size
- quality
- speed
- PDF validity
- text preservation

Xuất:

`COMPRESSION_ENGINE_DECISION.md`

## Phase 3 — Office conversion spike

Test:

- MS Office
- LibreOffice

Xuất:

`OFFICE_CONVERSION_DECISION.md`

## Phase 4 — Core implementation

Implement:

1. Document type detector
2. Conversion service
3. Compression analyzer
4. Compression engine
5. Compression profiles
6. Workflow orchestrator
7. UI bindings

## Phase 5 — Integration

```text
DOCX → PDF → Compress → Sign → Verify
XLSX → PDF → Compress → Sign → Verify
PDF → Compress → Sign → Verify
PDF → Sign → Verify
```

## Phase 6 — AI review

Một agent/context reviewer khác phải review:

- security
- state machine
- file corruption risk
- token safety
- Office COM cleanup
- compression quality
- signature validity
- UI logic
- race conditions
- temp file leakage
- licensing

Reviewer không được coi test “pass” là đủ.

## Phase 7 — Release Candidate

- build clean machine
- install clean machine
- Windows Defender check
- launch test
- update test
- uninstall test
- rollback test

## Phase 8 — PUS validation

Dùng Golden sample + real upload test.

## Phase 9 — Release v1.1.0

Tag:

```text
golden-signing-v1.1.0
```

---

# 36. Anti-forgetting / resume

Agent phải cập nhật sau mỗi task:

```text
.ai/
├── PROJECT_STATE.md
├── NEXT_ACTION.md
├── WORK_LOG.md
├── DECISIONS.md
├── RISKS.md
├── TEST_STATUS.md
└── SESSION_HANDOFF.md
```

`NEXT_ACTION.md` luôn chỉ rõ:

```text
Current phase
Current task
Last successful step
Failed step
Files changed
Tests run
Next exact command/action
```

Nếu context bị mất:

```text
Read PROJECT_STATE
Read NEXT_ACTION
Read WORK_LOG
Check git status
Run focused tests
Resume
```

Không bắt đầu lại toàn dự án.

---

# 37. Definition of Done cho v1.1.0

## Office

- DOC/DOCX/XLS/XLSX nhận diện được.
- Chuyển PDF thành công với provider phù hợp.
- Fallback provider hoạt động khi có thể.
- Source không bị thay đổi.

## Compression

- Lossless mode hoạt động.
- Balanced mode hoạt động.
- PUS Safe mode hoạt động.
- Custom profile lưu được.
- Cài đặt được ghi nhớ.
- Target size hoạt động.
- Không làm hỏng PDF.
- Không phá text/vector mặc định.

## Signing

- Compression xảy ra trước signature.
- Signature validation vẫn pass.
- Golden sample regression pass.
- Token flow không bị thay đổi xấu.

## Batch

- Một file lỗi không ảnh hưởng file khác.
- Retry hoạt động.
- Resume hoạt động.

## UX

- UI không freeze.
- File type hiển thị rõ.
- Progress rõ.
- Error rõ.
- Settings dễ hiểu.

## Release

- Third-party license report.
- Security audit.
- Dependency audit.
- Clean install test.
- Update test.
- PUS validation evidence.

---

# 38. Các tính năng nên cân nhắc cho v1.2+

Không đưa vào v1.1 nếu làm trễ core.

1. Preview PDF.
2. Preview trước/sau nén.
3. OCR tùy chọn cho scan.
4. Smart duplicate detection.
5. Watch Folder.
6. CLI mode.
7. Windows Explorer context menu mở rộng.
8. Remote signing/CSC.
9. Timestamp server.
10. LTV/PAdES-LT/LTA.
11. Batch template.
12. Rule-based automatic profile selection.
13. Auto-detect document type and recommend action.
14. Compression benchmark report.
15. Workspace restore.
16. Portable mode.
17. Multi-language.

---

# 39. Tính năng đặc biệt nên bổ sung ngay nếu chi phí thấp: “Nén thử”

Người dùng chọn file rồi nhấn:

**Xem khả năng nén**

Golden Signing phân tích mà không ký:

```text
Original: 1.84 MB
Lossless: 1.71 MB
Balanced: 612 KB
Strong: 392 KB
PUS Safe: 348 KB
```

Kèm preview nhỏ:

```text
Khuyến nghị:
PUS Safe
348 KB
Chất lượng tốt
Giữ text/vector
```

Đây là tính năng tạo khác biệt lớn nhưng không ảnh hưởng Signing Core.

---

# 40. Tính năng đặc biệt nên bổ sung: “Ký tối ưu”

Thay vì bắt người dùng hiểu “nén rồi ký”, có thể thêm một workflow thông minh:

**KÝ TỐI ƯU**

Engine tự quyết định:

```text
PDF?
  ↓
Phân tích dung lượng
  ↓
< target? → Sign
> target? → Compress
  ↓
Verify
```

Với Office:

```text
Office
 ↓
Convert PDF
 ↓
Analyze
 ↓
Compress if needed
 ↓
Sign
 ↓
Verify
```

Nút này có thể đặt trong `Tác vụ nhanh`, không nhất thiết phải chen thêm một nút lớn ở màn hình chính.

---

# 41. Tính năng đặc biệt nên bổ sung: “Không nén nếu không cần”

Compression engine không nên nén theo kiểu “user click là chắc chắn phải thay đổi file”.

Ví dụ:

`PDF = 210 KB`

Target = 400 KB

→ Không cần compression.

Hiển thị:

> File đã dưới mức mục tiêu, Golden Signing sẽ giữ nguyên chất lượng và bỏ qua bước nén.

---

# 42. Source references

### PDF24 compression
https://tools.pdf24.org/en/compress-pdf

PDF24 mô tả nhiều tùy chọn như DPI, image quality, remove thumbnails, deduplicate streams, rasterize heavy graphics, subset embedded fonts, modern image compression, grayscale, maximum Flate compression, flatten form, strip output intents/attachments/annotations/outline/metadata/structural information. Đây là **feature inspiration**, không phải bằng chứng rằng Golden Signing phải sao chép tất cả.

### qpdf
https://qpdf.readthedocs.io/en/latest/cli.html
https://qpdf.readthedocs.io/en/stable/license.html

### pikepdf images
https://pikepdf.readthedocs.io/en/stable/topics/images.html

### Microsoft Excel PDF export
https://learn.microsoft.com/en-us/office/vba/api/excel.workbook.exportasfixedformat

### Microsoft Word PDF export
https://learn.microsoft.com/en-us/office/vba/api/word.range.exportasfixedformat

### Office automation warning
https://learn.microsoft.com/en-us/office/client-developer/integration/considerations-unattended-automation-office-microsoft-365-for-unattended-rpa

### LibreOffice conversion
https://help.libreoffice.org/latest/uk/text/shared/guide/start_parameters.html

### pyHanko
https://github.com/MatthiasValvekens/pyHanko

### Qt for Python licensing
https://doc.qt.io/qtforpython-6/commercial/index.html
https://doc.qt.io/qt-6/licensing.html

### Ghostscript licensing
https://ghostscript.com/faq/
https://www.ghostscript.com/releases/gsdnld.html

---

# 43. Final implementation decision

**v1.1.0 là khả thi và nên làm.**

Hai tính năng người dùng yêu cầu không xung đột với Signing Core nếu kiến trúc đúng.

Điểm cần điều chỉnh so với ý tưởng ban đầu:

1. Không ép mọi PDF phải nén.
2. Không cam kết mọi PDF đều xuống dưới 400 KB.
3. Target 400 KB nên hiểu là target của **file cuối cùng sau ký**, không phải chỉ file trước ký.
4. Không nén sau khi ký.
5. Office conversion phải tách provider và có fallback.
6. Không bundle Ghostscript nếu licensing chưa được xử lý.
7. Compression phải có quality floor.
8. PUS Safe không được tự động rasterize toàn trang.
9. Không đánh đổi text/vector chỉ để đạt một con số KB nếu người dùng chưa cho phép.
10. AI Agent phải làm spike/benchmark trước khi khóa compression engine.

---

# 44. Prompt khởi động cho AI Coding Agent

AI Agent phải bắt đầu bằng câu lệnh nội bộ sau:

```text
You are working on Golden Signing v1.1.0.

Do NOT start coding immediately.

1. Read this specification completely.
2. Audit the existing v1.0.0 repository.
3. Inspect the current signing pipeline and regression tests.
4. Inspect the current UI shown in the v1.0.0 reference screenshot.
5. Read the UI/UX Pro Max skill before proposing UI changes.
6. Perform a backend and database architecture review.
7. Research Office-to-PDF conversion options and PDF compression engines.
8. Pay special attention to licensing constraints.
9. Create AI_REVIEW_V1_1.md.
10. Create CURRENT_ARCHITECTURE.md.
11. Create RISK_REGISTER.md.
12. Create COMPRESSION_ENGINE_DECISION.md.
13. Create OFFICE_CONVERSION_DECISION.md.
14. Create ADRs for all material architecture choices.
15. Do not implement the main feature until these review documents are complete.
16. Use the existing Golden Signing codebase; do not rewrite the application from scratch.
17. Preserve the existing signing functionality and add regression tests before modifying it.
18. Treat the supplied Hải quan original/signed PDF pair as a critical regression sample.
19. Never modify a signed PDF after signing.
20. Implement compression before signing.
21. Persist job state so interrupted sessions can resume safely.
22. Review your own implementation using an independent review pass before declaring v1.1.0 complete.
23. Run unit, integration, security, licensing, packaging and PUS compatibility tests.
24. Never claim PUS compatibility without actual evidence from the target environment.
25. At every interruption, update PROJECT_STATE.md, NEXT_ACTION.md and SESSION_HANDOFF.md.

First response: report findings and proposed architecture. Do not code yet.
```

---

# 45. Versioning

```text
v1.0.0 = current stable baseline
v1.1.0 = Office→PDF + compression + integrated pre-sign workflow
v1.1.x = bug/security fixes
v1.2.0 = future feature release
```

Semantic versioning should be used.

---

# 46. Release notes v1.1.0 dự kiến

```text
Golden Signing v1.1.0

NEW
- Sign Word/Excel files by converting them to PDF first
- Batch Office conversion
- PDF compression engine
- Compression profiles
- Target-size compression
- PUS Safe compression workflow
- Compress & Sign button
- Compression settings memory
- Smart compression recommendations
- Compression benchmark/analysis groundwork

IMPROVED
- Batch workflow state tracking
- Error reporting
- File type detection
- Output management
- Resume/recovery

SECURITY
- Office input isolation/validation
- Signed-PDF mutation protection
- Dependency/license audit

COMPATIBILITY
- Preserve existing PUS Safe signing workflow
- Golden sample regression test
```

---

# 47. Acceptance statement

Chỉ đánh dấu v1.1.0 “Ready” khi:

```text
Code ✓
Tests ✓
Office conversion ✓
Compression ✓
Signing regression ✓
Certificate/token regression ✓
Golden sample ✓
PUS validation evidence ✓
Security review ✓
License review ✓
Packaging ✓
Update ✓
Documentation ✓
AI independent review ✓
```

Nếu thiếu một mục critical, release phải giữ ở RC/beta.
