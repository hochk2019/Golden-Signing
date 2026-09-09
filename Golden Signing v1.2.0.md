# GOLDEN SIGNING

**Tên sản phẩm:** Golden Signing  
**Định hướng:** Windows desktop application chuyên ký số PDF/chứng từ, ưu tiên tương thích hệ thống Hải quan PUS, ký hàng loạt ổn định, nhẹ, hiện đại và dễ mở rộng.  
**Đặc tả:** 1.2.0  
**Phiên bản phần mềm khởi đầu:** 0.1.0-alpha  
**Ngày đặc tả:** 2026-09-09  
**Nhà phát triển:** HOC HK  
**Email:** hochk2019@gmail.com  
**Điện thoại:** 0868.333.606  
**Thông tin dịch vụ:** Cung cấp dịch vụ tư vấn hải quan miễn phí - vận chuyển hàng hóa toàn quốc.

---

## 0. Chỉ dẫn bắt buộc cho AI Coding Agent

Tài liệu này là **đặc tả triển khai** cho Golden Signing. AI Coding Agent không được chỉ “làm cho chạy” theo cách đơn giản, mà phải thực hiện theo đúng thứ tự:

1. Review lại toàn bộ đặc tả này trước khi code.
2. Kiểm tra các giả định bằng tài liệu kỹ thuật và thử nghiệm thực tế.
3. Phân tích codebase theo kiến trúc module trước khi sửa.
4. Không sửa Signing Core chỉ để làm UI đẹp hơn nếu chưa có test bảo vệ.
5. Không cho phép một lỗi của một file làm hỏng cả batch.
6. Không bao giờ ghi PIN/chìa khóa riêng vào log, file cấu hình, crash dump hay telemetry.
7. Không tự động thay đổi PDF gốc. Luôn tạo file output an toàn theo chiến lược atomic commit.
8. Mọi thay đổi vào PDF sau khi ký phải được xem là thao tác phá tính toàn vẹn chữ ký và phải bị chặn/cảnh báo.
9. Mọi release phải chạy đầy đủ test, security review, dependency audit, packaging test và golden-sample regression.
10. AI phải review lại chính code đã viết trong một phiên/context review độc lập, không chỉ đọc diff do chính nó vừa sinh ra.
11. Không tuyên bố “tương thích PUS 100%” nếu chưa có test upload/verify thực tế trên môi trường PUS tương ứng.
12. Ưu tiên correctness > compatibility > reliability > security > performance > UI polish. Không được đánh đổi tính toàn vẹn chữ ký để tăng tốc.

### 0.1. Nguyên tắc không được vi phạm

- Private key luôn ở USB Token/thiết bị ký hoặc remote signing service. Không export private key.
- Không lưu PIN/token secret.
- PIN chỉ tồn tại trong memory trong thời gian ngắn nhất có thể và phải được xoá/giải phóng ngay sau khi dùng.
- Không parallelize cryptographic signing trên cùng một token nếu token/middleware không chứng minh được thread-safe.
- Parallelize phần đọc, preflight, rendering, hashing và chuẩn bị queue; serialize thao tác ký trên một token.
- Không dùng ảnh chữ ký/chữ ký tay thay cho chữ ký số thật.
- Visual signature appearance và cryptographic signature phải được coi là hai lớp độc lập.
- Chế độ hiển thị chữ ký (**visible / invisible**) phải luôn là lựa chọn của người dùng và thuộc về signing profile; **PUS Safe có thể đặt invisible làm mặc định**, nhưng tuyệt đối không được ép tất cả tài liệu phải invisible. Nếu preflight phát hiện nội dung hiển thị đã có dấu/chữ ký hình ảnh, UI nên cảnh báo và đề xuất invisible, nhưng người dùng vẫn có thể chọn visible khi policy cho phép.
- Không thay đổi nội dung, kích thước trang, DPI, hình ảnh, font hoặc page rasterization của PDF chỉ để ký.

---

# 1. Kết luận kiến trúc đã được review

## 1.1. Quyết định chính

Golden Signing nên dùng **Python** thay vì .NET cho phiên bản đầu tiên.

Kiến trúc khuyến nghị:

```text
Python 3.13.x
   + PySide6
   + pyHanko
   + pypdfium2
   + cryptography
   + PKCS#11 adapter
   + pywin32 / Windows Certificate APIs
   + SQLite
   + httpx
   + structlog/logging
   + pytest
   + hypothesis
   + mypy/ruff
   + pip-audit
   + PyInstaller
```

### Vì sao chọn Python

Python phù hợp vì:

- Máy phát triển đã có nhiều thư viện Python.
- Signing/PDF ecosystem hiện đã có pyHanko, hỗ trợ PDF signatures, PAdES, PKCS#11, validation và interrupted signing.
- PyHanko 0.37.0 được phát hành 2026-08-31, yêu cầu Python >=3.10 và MIT licensed.
- PySide6 là binding chính thức của Qt 6 cho Python.
- pypdfium2 cung cấp rendering PDF bằng PDFium và tránh phụ thuộc strong-copyleft như AGPL của một số PDF renderer khác.
- PyInstaller có thể đóng gói ứng dụng và dependency thành ứng dụng độc lập cho Windows.

### Điều kiện quan trọng

Python **không có nghĩa là mọi token sẽ hoạt động tự động**.

Lớp Token Adapter phải hỗ trợ nhiều backend:

1. PKCS#11 native DLL — backend ưu tiên.
2. Windows Certificate Store / CSP / KSP — backend tương thích Windows.
3. Remote Signing / CSC — phase mở rộng.

Nếu một USB Token chỉ cung cấp CSP/KSP mà không có PKCS#11 usable, không được kết luận “Python không hỗ trợ token”; phải triển khai Windows Crypto API adapter hoặc một helper native nhỏ.

---

# 2. Cơ sở phân tích từ hai file PDF mẫu

Đã có hai file mẫu cùng một chứng từ:

- `6.Chung tu khai bs_106960399450_H11-tong(1).pdf` = bản gốc chưa ký.
- `6.Chung tu khai bs_106960399450_H11-tong.pdf` = bản đã ký bằng ECUS Tool.

## 2.1. Bản gốc

Đặc điểm đã kiểm tra:

- PDF 1.7.
- 4 trang.
- Có metadata `Creator = PDF24 Creator`.
- `Producer = GPL Ghostscript 10.07.0`.
- Không có `/AcroForm`.
- Không có `/Annots` trên 4 trang.

Quan trọng: **trang 1 của bản gốc đã chứa sẵn hình con dấu đỏ + chữ ký xanh**. Trang 2 cũng đã có con dấu/chữ ký hiển thị. Vì vậy appearance nhìn thấy trong bản ECUS không phải bằng chứng rằng ECUS đã vẽ thêm chữ ký hiển thị; nó có thể chỉ đang giữ nguyên nội dung gốc và thêm lớp chữ ký số vô hình.

## 2.2. Bản ECUS đã ký

Đã kiểm tra:

- Vẫn là PDF 1.7.
- 4 trang.
- `Producer = GPL Ghostscript 10.07.0; modified using iTextSharp 5.1.1 (c) 1T3XT BVBA`.
- Root có `/AcroForm`.
- `/AcroForm/SigFlags = 3`.
- Có field `Signature1`.
- Field type `/Sig`.
- Field là `/Widget` annotation.
- Field nằm ở page 1.
- `/Rect = [0, 0, 300, 20]`.
- Có appearance XObject `/AP`.
- Có signature dictionary:

```pdf
/Type /Sig
/Filter /Adobe.PPKMS
/SubFilter /adbe.pkcs7.sha1
/M D:20100101000000+07'00'
/Name 
/ByteRange [0 313171 321173 33265]
/Contents <DER encoded CMS/PKCS#7 ...>
```

Điểm phải lưu ý: `/M` trong mẫu là `D:20100101000000+07'00'`, không nên sao chép giá trị này. Golden Signing phải tạo signing time hợp lý hoặc để timestamp/validation profile quyết định. Không hard-code thời gian.

## 2.3. CMS/Certificate

`/Contents` có DER-encoded CMS/PKCS#7.

Certificate được trích xuất từ CMS:

- Subject: `CN=CÔNG TY TNHH ICH CUBE VIỆT NAM`
- UID: `MST:2400817632`
- Issuer: `CN=CA2,O=NACENCOMM SCT,C=VN`
- Public key: RSA
- Certificate signature hash: SHA-256
- Certificate validity: 2024-11-27 đến 2026-12-02 UTC.
- SHA-256 fingerprint:
  `62003b776fa39a574904c0fc3a6cd691bde004320e4bd365a0c4f00777474cda`

## 2.4. Đặc điểm đặc biệt: ECUS dùng `/adbe.pkcs7.sha1`

Theo ISO 32000-1/Adobe PDF specifications, `/adbe.pkcs7.sha1` là một cách đóng gói PKCS#7 trong PDF, trong đó SHA-1 digest của byte range được encapsulate trong PKCS#7.

**Không được suy luận rằng Golden Signing phải dùng SHA-1 cho mọi tài liệu chỉ vì mẫu ECUS dùng nó.**

Thay vào đó phải có 2 lớp profile:

- `PUS-Compatibility` — tái tạo chính xác kiểu đóng gói đã chứng minh là PUS chấp nhận.
- `Modern-PAdES` — dùng profile PAdES/CAdES hiện đại hơn khi môi trường đích cho phép.

PUS-Compatibility chỉ được gọi là “đã xác nhận” sau test thực tế. Modern-PAdES không được tự ý thay thế PUS-Compatibility trong phiên bản đầu.

## 2.5. Ý nghĩa của ByteRange

Mẫu dùng:

```text
[0 313171 321173 33265]
```

Khoảng chữ ký bỏ qua vùng `/Contents` chứa CMS và bảo vệ các byte còn lại.

Golden Signing phải:

- Tạo placeholder `/Contents` đủ lớn.
- Tính ByteRange chính xác.
- Tạo digest trên đúng byte ranges.
- Gọi token để ký digest/signed attributes phù hợp.
- Chèn CMS vào `/Contents`.
- Verify lại ByteRange và cryptographic integrity trước khi commit output.

---

# 3. Mục tiêu sản phẩm

Golden Signing không phải “ECUSTool clone”.

Mục tiêu:

> Một công cụ ký số PDF cho Windows, mở lên là hiểu ngay, kéo thả là dùng được, ký một file hoặc hàng trăm file ổn định, không phá PDF gốc, hiển thị rõ lỗi từng file, có PUS Safe profile và có thể tự cập nhật an toàn.

---

# 4. UI/UX mục tiêu

## 4.1. Ngôn ngữ

- Tiếng Việt mặc định.
- Có thể thêm English sau.
- Font UI ưu tiên Segoe UI / font hệ thống tương thích Windows.

## 4.2. Màn hình chính

```text
┌────────────────────────────────────────────────────────────┐
│ Golden Signing                                 v0.1.0      │
│ Ký số PDF nhanh • An toàn • Tương thích Hải quan          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│          KÉO THẢ PDF VÀO ĐÂY                               │
│                                                            │
│          [ + Thêm PDF ]   [ + Thêm thư mục ]               │
│                                                            │
├────────────────────────────────────────────────────────────┤
│  12 file       10 sẵn sàng       2 cần kiểm tra            │
│                                                            │
│  □ file01.pdf      Sẵn sàng          2 trang                │
│  □ file02.pdf      Sẵn sàng          4 trang                │
│  □ file03.pdf      PDF lỗi           Không thể mở           │
│                                                            │
│  Profile: [ PUS Safe ▼ ]                                   │
│  Chứng thư: [ CÔNG TY TNHH ABC ▼ ]                          │
│                                                            │
│              [ KÝ SỐ ]                                     │
└────────────────────────────────────────────────────────────┘
```

## 4.3. Không dùng dashboard phức tạp

Trang chính phải tập trung vào 1 việc: ký.

Các tính năng nâng cao đưa vào sidebar hoặc Settings:

- Tệp
- Ký số
- Kiểm tra chữ ký
- Lịch sử
- Mẫu chữ ký
- Tự động
- Cài đặt
- Trợ giúp
- Thông tin

## 4.4. Preview PDF

Dùng `pypdfium2` để render preview.

Preview hỗ trợ:

- zoom
- fit page
- page thumbnails
- page number
- rotate view
- tìm kiếm text nếu khả thi
- chọn vùng visible signature

Không sửa nội dung PDF trong editor ở phase đầu.

---

# 5. Tính năng sản phẩm

## 5.1. Core

- Ký một PDF.
- Ký nhiều PDF.
- Ký cả thư mục.
- Drag & drop.
- File picker.
- Windows Explorer context menu.
- Ký invisible.
- Visible signature appearance tùy chọn.
- Chọn trang và vị trí visible signature.
- Template appearance.
- Tự chèn thông tin chứng thư vào appearance nếu người dùng bật.

## 5.2. Batch Signing

Đây là tính năng trọng điểm.

Mỗi file có state machine:

```text
DISCOVERED
→ PREFLIGHT
→ READY
→ WAITING_TOKEN
→ SIGNING
→ FINALIZING
→ VERIFYING
→ COMMITTED
→ SUCCESS
```

Các trạng thái lỗi:

```text
PREFLIGHT_FAILED
TOKEN_ERROR
PIN_CANCELLED
SIGN_FAILED
FINALIZE_FAILED
VERIFY_FAILED
OUTPUT_CONFLICT
IO_ERROR
```

Batch phải hỗ trợ:

- Pause.
- Resume.
- Cancel queued.
- Retry failed.
- Retry selected.
- Open output folder.
- Export error report.
- Không làm dừng batch vì 1 file lỗi.

## 5.3. Atomic output

Quy trình:

```text
input.pdf
  ↓
working/temp UUID
  ↓
write signed temporary
  ↓
verify
  ↓
fsync/flush
  ↓
atomic rename/replace
  ↓
output.pdf
```

Không được tạo output “đã ký” nếu verification thất bại.

## 5.4. PUS Safe

Profile riêng:

```yaml
name: PUS Safe
visible_signature: false
preserve_existing_content: true
preserve_page_geometry: true
incremental_update: true
post_sign_verification: strict
subfilter: profile-controlled
algorithm: profile-controlled
```

Không hard-code các trường của ECUS vào code. Dùng cấu hình profile.

## 5.5. Signature appearance

Template engine:

- ảnh logo
- tên công ty
- người ký
- chức danh
- thời gian
- số chứng thư rút gọn
- issuer
- QR verification tùy chọn
- text tùy biến

Hai kiểu:

1. Minimal.
2. Corporate.

PUS Safe mặc định invisible.

## 5.6. Certificate Manager

Hiển thị:

- Subject.
- Organization.
- Serial.
- Issuer.
- Valid from/to.
- Key algorithm.
- Key size.
- SHA-256 fingerprint.
- Token name.
- Backend đang dùng.
- Trust status.

Cảnh báo:

- hết hạn < 30 ngày
- hết hạn < 7 ngày
- certificate revoked nếu xác minh được
- token không phản hồi
- driver missing
- nhiều certificate trùng subject

## 5.7. Signature Viewer/Verifier

Có thể mở PDF và hiển thị:

```text
✓ Chữ ký hợp lệ về mặt mật mã
✓ Tài liệu không bị thay đổi sau khi ký
✓ Certificate đọc được
✓ Certificate còn hiệu lực tại thời điểm kiểm tra
⚠ Không có timestamp tin cậy
⚠ Không xác định được trust chain
```

Phân tách rõ:

- Cryptographic validity
- Certificate validity
- Trust validity
- Revocation status
- Timestamp validity
- Document modification status

## 5.8. Audit History

SQLite local.

Ghi:

- thời gian
- file hash trước ký
- file hash sau ký
- file path
- certificate fingerprint
- profile
- result
- duration
- error code

Không ghi:

- PIN
- private key
- full CMS blob trừ khi debug mode được user bật chủ động

Có tùy chọn:

- xoá lịch sử
- export CSV/JSON
- mở location file

## 5.9. Watch Folder

Phase 2:

```text
C:\GoldenSigning\Input
           ↓
Golden Signing watcher
           ↓
preflight
           ↓
auto sign
           ↓
C:\GoldenSigning\Signed
```

Phải có debounce để tránh ký file đang được phần mềm khác ghi.

## 5.10. CLI/API

Phase 2/3:

```text
golden-signing.exe sign file.pdf

golden-signing.exe batch C:\Input --profile pus-safe

golden-signing.exe verify output.pdf
```

CLI dùng chung Signing Core, không copy code logic.

---

# 6. Kiến trúc module

```text
src/golden_signing/
│
├── app/
│   ├── bootstrap.py
│   ├── dependencies.py
│   └── lifecycle.py
│
├── ui/
│   ├── main_window.py
│   ├── pages/
│   ├── dialogs/
│   ├── widgets/
│   ├── models/
│   └── resources/
│
├── signing/
│   ├── orchestrator.py
│   ├── profiles.py
│   ├── pdf_signer.py
│   ├── cms_builder.py
│   ├── signature_appearance.py
│   ├── validators.py
│   └── exceptions.py
│
├── pdf/
│   ├── inspection.py
│   ├── rendering.py
│   ├── incremental.py
│   ├── fields.py
│   └── integrity.py
│
├── token/
│   ├── base.py
│   ├── pkcs11.py
│   ├── windows_crypto.py
│   ├── discovery.py
│   └── session.py
│
├── certificate/
│   ├── models.py
│   ├── discovery.py
│   ├── validation.py
│   └── trust.py
│
├── batch/
│   ├── queue.py
│   ├── state.py
│   ├── worker.py
│   └── recovery.py
│
├── storage/
│   ├── database.py
│   ├── settings.py
│   └── secrets.py
│
├── updater/
│   ├── checker.py
│   ├── manifest.py
│   ├── verifier.py
│   └── installer.py
│
├── diagnostics/
│   ├── health.py
│   ├── reports.py
│   └── logging.py
│
└── security/
    ├── hashing.py
    ├── redaction.py
    └── integrity.py
```

---

# 7. Signing Core

## 7.1. Đừng viết PDF signer từ đầu nếu không cần

Ưu tiên pyHanko làm engine PAdES/PDF signature base.

Lý do:

- hiểu signature fields
- ByteRange
- CMS
- PAdES
- PKCS#11
- validation
- timestamp
- interrupted signing

Sau đó Golden Signing xây adapter/profile/orchestration ở trên.

## 7.2. Interface

```python
class SignerBackend(Protocol):
    def list_certificates(self) -> list[CertificateInfo]: ...
    def sign(self, digest: bytes, algorithm: str) -> bytes: ...
    def open_session(self) -> SigningSession: ...
```

```python
class PdfSigningEngine(Protocol):
    def preflight(self, input_path: Path, profile: SigningProfile) -> PreflightResult: ...
    def sign(self, input_path: Path, output_path: Path, signer: SignerBackend,
             profile: SigningProfile) -> SignResult: ...
    def verify(self, output_path: Path, profile: SigningProfile) -> VerificationResult: ...
```

## 7.3. Token session manager

Một session có:

- token identity
- certificate identity
- login state
- health state
- mutex
- timeout
- disconnect recovery

Pseudo-flow:

```text
discover token
→ select certificate
→ open token session
→ request PIN only when necessary
→ sign N documents sequentially
→ close session
```

Nếu token rút ra:

```text
SIGNING → TOKEN_LOST → WAITING_FOR_TOKEN
```

Không crash app.

---

# 8. Batch Engine nâng cao

## 8.1. Worker model

Không dùng một thread độc quyền cho tất cả việc.

Khuyến nghị:

```text
UI thread
   │
   ├── preflight worker pool
   ├── PDF render worker pool
   ├── hash worker pool
   │
   └── signing queue (serialized per token)
            │
            └── verification worker pool
```

Nếu có 2 token độc lập, có thể có 2 signing lanes.

## 8.2. Idempotency

Mỗi job có UUID.

Nếu app crash:

- job đang ký → không dùng lại output temp chưa verify
- job đã commit → detect output hash/history
- job chưa bắt đầu → resume

Không được ký trùng file nếu profile có `skip_if_output_valid=true`.

## 8.3. Retry policy

Retry tự động chỉ với lỗi transient:

- file lock
- token reconnect
- temporary I/O
- timestamp network timeout

Không retry mù với:

- certificate expired
- unsupported PDF
- signature verification failed
- wrong PIN
- invalid cryptographic state

---

# 9. PDF Preflight

Trước khi ký phải kiểm tra:

- PDF header.
- page count.
- encrypted/password protected.
- malformed PDF.
- existing signatures.
- existing AcroForm.
- existing incremental updates.
- PDF version.
- unsupported structures.
- form fields.
- annotations.
- file size.
- write permission.
- output collision.

Kết quả có 3 mức:

```text
SAFE
WARN
BLOCK
```

Ví dụ:

`SAFE`: PDF bình thường, chưa ký.

`WARN`: PDF đã có signature, ký thêm sẽ tạo revision mới.

`BLOCK`: PDF encrypted và không có quyền sửa/sign.

---

# 10. Existing signature policy

Golden Signing phải phát hiện:

- signature fields
- signed revisions
- document timestamps
- incremental updates

Không bao giờ “flatten” hoặc rebuild PDF đã ký để ký tiếp.

Nếu user chọn ký tiếp:

```text
append new incremental revision
```

Nếu không đảm bảo an toàn:

```text
BLOCK
"Tài liệu đã có chữ ký và không thể ký tiếp an toàn theo profile hiện tại."
```

---

# 11. PUS Compatibility Lab

Đây là phần quan trọng nhất của dự án.

## 11.1. Golden fixtures

Giữ cục bộ:

```text
tests/fixtures/private/
  ecus_source.pdf
  ecus_signed.pdf
```

Không commit hai file nếu repository public.

Hash fixtures để bảo đảm test đúng file.

## 11.2. Test matrix

Mỗi build phải test:

| ID | Scenario | Expected |
|---|---|---|
| PUS-001 | PDF 1 trang | ký + verify |
| PUS-002 | PDF 4 trang giống mẫu | ký + verify |
| PUS-003 | PDF scan | ký |
| PUS-004 | PDF lớn | ký |
| PUS-005 | 100 PDF | tất cả xử lý độc lập |
| PUS-006 | file lỗi giữa batch | file khác vẫn chạy |
| PUS-007 | rút token | batch không crash |
| PUS-008 | cắm lại token | resume |
| PUS-009 | certificate hết hạn | block |
| PUS-010 | existing signature | policy rõ ràng |
| PUS-011 | PDF encrypted | policy rõ ràng |
| PUS-012 | PUS real upload | accepted/verified |

## 11.3. So sánh với ECUS

Không cần byte-for-byte giống ECUS.

So sánh:

- page count
- rendered content preservation
- `/AcroForm`
- `/Sig`
- `/ByteRange`
- `/Contents`
- CMS parse
- signing certificate
- signature algorithm
- timestamp
- incremental update
- validation result

---

# 12. PUS Safe profile – nguyên tắc

Profile PUS Safe phải ưu tiên:

1. Không thay đổi nội dung trang.
2. Không rasterize PDF.
3. Không đổi kích thước trang.
4. Không nén lại toàn bộ document.
5. Không flatten.
6. Dùng incremental update.
7. Signature field có cấu trúc chuẩn PDF.
8. CMS/PKCS#7/PAdES theo profile đã thử nghiệm.
9. Post-sign verification.
10. Thực tế upload PUS.

### Mặc định

```text
Signature mode: INHERIT_FROM_PROFILE
Visible signature: PROFILE_CONTROLLED
Appearance modification: PROFILE_CONTROLLED
Incremental update: ON
Post-sign verify: ON
Overwrite original: OFF
Atomic output: ON
```

**Nguyên tắc mới:** không coi invisible là giới hạn của Golden Signing. Mọi profile phải chọn được `VISIBLE`, `INVISIBLE` hoặc `ASK_EVERY_TIME`. `PUS Safe` có thể mặc định `INVISIBLE`, nhưng profile khác có thể mặc định `VISIBLE`. Khi người dùng chọn visible, hệ thống phải preview trước khi ký nếu appearance có thể che nội dung tài liệu.

---

# 13. Hiện đại hóa nhưng không over-engineer

## Nên thêm

- drag/drop
- batch queue
- search/filter
- retry
- pause/resume
- certificate health
- profile presets
- signature verifier
- watch folder
- context menu
- CLI
- signed update
- diagnostics
- portable export/import settings
- recent files
- keyboard shortcuts
- dark/light theme

## Không nên thêm ở phiên bản đầu

- cloud account bắt buộc
- đăng nhập server bắt buộc
- telemetry mặc định
- database server
- microservices
- Electron
- browser-based UI bắt buộc
- chỉnh sửa PDF đầy đủ như Acrobat
- OCR toàn bộ tài liệu
- AI đọc tài liệu tự động
- ký tự động theo nội dung nếu chưa có audit model rõ ràng

---

# 14. AI features có thể thêm sau

Không để AI tham gia vào quá trình tạo chữ ký cryptographic.

AI chỉ hỗ trợ:

- giải thích lỗi
- đề xuất profile
- đọc diagnostics
- phát hiện file có khả năng cần xử lý đặc biệt
- tạo tên output
- tìm chứng từ cần ký

AI **không được**:

- giữ private key
- nhận PIN
- sinh signature raw
- sửa bytes sau khi ký
- tự quyết định bỏ qua verification

---

# 15. Cơ chế update từ xa

## 15.1. Mục tiêu

Trong Settings:

```text
[✓] Tự động kiểm tra cập nhật

Phiên bản hiện tại: 0.1.0
Phiên bản mới: 0.2.0

Cải tiến:
• Batch ổn định hơn
• Hỗ trợ CA mới
• Sửa lỗi PDF...

[ Xem chi tiết ] [ Cập nhật ]
```

## 15.2. Security model

Không chỉ tải EXE rồi chạy.

Manifest:

```json
{
  "product": "Golden Signing",
  "version": "0.2.0",
  "min_supported_version": "0.1.0",
  "url": "https://.../GoldenSigning-0.2.0.exe",
  "sha256": "...",
  "signature": "..."
}
```

Client phải:

1. HTTPS.
2. Verify publisher signature trên update binary.
3. Verify SHA-256.
4. Verify signed manifest bằng public key tích hợp trong app.
5. Không downgrade nếu không được phép.
6. Chỉ cập nhật sau khi user xác nhận hoặc policy cho phép.
7. Có rollback/fallback.

## 15.3. Code signing

Các EXE/DLL/installer của Golden Signing phải được code-sign bằng chứng thư của nhà phát triển khi sản phẩm phát hành chính thức.

Không dùng self-signed certificate cho release production.

---

# 16. Versioning

Dùng Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Ví dụ:

```text
0.1.0-alpha
0.1.0-beta
1.0.0
1.0.1
1.1.0
2.0.0
```

## Version metadata trong app

- ProductName = Golden Signing
- FileDescription = Golden Signing - PDF Digital Signature
- CompanyName = HOC HK
- ProductVersion = x.y.z
- Copyright = HOC HK

Trong About:

```text
Golden Signing
Version 0.1.0

Developer: HOC HK
Email: hochk2019@gmail.com
Phone: 0868.333.606

Cung cấp dịch vụ tư vấn hải quan miễn phí
- vận chuyển hàng hóa toàn quốc.
```

---

# 17. Miễn trừ trách nhiệm sử dụng

Đưa nội dung này vào About / Disclaimer / installer khi phù hợp:

> **Miễn trừ trách nhiệm**
>
> Golden Signing là phần mềm hỗ trợ người dùng thực hiện thao tác ký số và kiểm tra kỹ thuật đối với tài liệu điện tử. Phần mềm không thay thế quy định của cơ quan nhà nước, tổ chức cung cấp chứng thư số, nhà cung cấp dịch vụ chứng thực chữ ký số hoặc hệ thống tiếp nhận hồ sơ điện tử.
>
> Kết quả tiếp nhận/ghi nhận chữ ký tại một hệ thống bên thứ ba, bao gồm hệ thống Hải quan, có thể phụ thuộc vào cấu hình hệ thống, chứng thư số, nhà cung cấp CA, driver/token, phiên bản phần mềm, quy định nghiệp vụ và các yêu cầu kỹ thuật thay đổi theo thời gian.
>
> Người sử dụng có trách nhiệm kiểm tra tài liệu sau khi ký, kiểm tra trạng thái chữ ký và bảo đảm hồ sơ gửi đi phù hợp với yêu cầu của cơ quan/đơn vị tiếp nhận.
>
> Nhà phát triển không chịu trách nhiệm đối với thiệt hại phát sinh từ việc sử dụng chứng thư số, token, dữ liệu đầu vào, cấu hình hệ thống, lỗi mạng, lỗi thiết bị, thay đổi của hệ thống bên thứ ba hoặc việc người dùng bỏ qua cảnh báo/kiểm tra của phần mềm.
>
> **Không bao giờ chia sẻ PIN, private key hoặc cho người khác sử dụng token trái phép.**

AI Agent không được tự sửa disclaimer thành tuyên bố pháp lý tuyệt đối. Nếu sản phẩm phát hành thương mại, nên rà soát pháp lý riêng.

---

# 18. Privacy

Mặc định:

- Không upload PDF lên server.
- Không gửi nội dung PDF.
- Không gửi certificate private data.
- Không gửi PIN.
- Không telemetry document content.

Update checker chỉ gửi thông tin tối thiểu cần thiết.

Diagnostics export phải có redaction.

---

# 19. Logging

Có 3 mức:

```text
Normal
Diagnostic
Developer
```

Normal:

- job start/end
- errors
- version
- token status tổng quát

Diagnostic:

- stack traces
- profile
- PDF metadata
- dependency versions

Developer:

- không được log secret
- có thể log low-level PDF object metadata có kiểm soát

Implement redaction layer.

---

# 20. Performance target

Mục tiêu trên máy văn phòng hiện đại:

- App startup < 2 giây sau lần chạy đầu.
- Add 100 PDF không treo UI.
- Preview không block signing.
- 100-file batch không tăng RAM không kiểm soát.
- File 100–300 MB phải có streaming strategy phù hợp.
- UI giữ 60 FPS cho thao tác cơ bản nếu có thể.

Không benchmark theo tốc độ “ký cryptographic” nếu USB Token là bottleneck.

Đo riêng:

- preflight time
- render time
- hashing time
- token sign time
- finalize time
- verify time
- total job time

---

# 21. Error handling UX

Không hiển thị traceback cho người dùng bình thường.

Ví dụ:

```text
Không thể ký file

Tên file: invoice-032.pdf
Lý do: Chứng thư số không còn hợp lệ.

[ Xem chi tiết ] [ Bỏ qua ]
```

Technical detail:

```text
Code: CERT_EXPIRED
Backend: PKCS11
Certificate: SHA256 fingerprint ...
```

Error codes phải ổn định qua phiên bản để dễ support.

---

# 22. Settings

### Chung

- Theme
- Language
- startup
- recent files

### Ký số

- default profile
- default certificate
- visible/invisible
- signature appearance
- output folder
- overwrite policy

### Batch

- concurrency preflight
- auto retry
- stop on token loss
- verify after signing

### Update

- auto-check
- stable/beta channel
- manual update

### Privacy

- diagnostics
- history retention

---

# 23. File naming

Template:

```text
{original_name}_signed.pdf
```

Hoặc:

```text
{original_name}.pdf
```

Không mặc định overwrite.

Hỗ trợ:

```text
[✓] Không ghi đè file gốc
[✓] Nếu trùng tên → thêm (1), (2), ...
```

---

# 24. Installer

Giai đoạn đầu:

- portable build để test.
- installer sau khi core ổn định.

Production:

- signed installer
- signed EXE/DLL
- uninstall sạch
- Start Menu shortcut
- context menu optional
- per-user install ưu tiên nếu phù hợp

PyInstaller:

- ưu tiên `onedir` ở giai đoạn đầu vì dễ chẩn đoán và ít overhead runtime.
- có thể có `onefile` cho portable distribution sau khi ổn định.

---

# 25. Dependency policy

Không dùng mọi package vì “đã có trong máy”.

Repository phải có environment riêng:

```text
.venv/
pyproject.toml
uv.lock hoặc requirements lock
```

Pin version cho release.

Mỗi dependency phải ghi:

- purpose
- license
- version
- security status

Bắt buộc chạy `pip-audit` trên lockfile/environment trước release.

Không tự động nâng toàn bộ dependency trong production nếu chưa chạy regression.

---

# 26. License review bắt buộc

Đặc biệt chú ý:

### PyHanko

MIT.

### PySide6

Community Edition có LGPLv3/GPLv3; Qt cũng có commercial license.

Nếu Golden Signing được phân phối closed-source/commercial, phải thực hiện đúng nghĩa vụ license của Qt/PySide6 hoặc mua license thương mại phù hợp.

### pypdfium2

pypdfium2 theo Apache-2.0/BSD-3-Clause, nhưng các binary/dependency bên trong PDFium có thêm license phải ship theo yêu cầu.

### Không dùng PyMuPDF mặc định

Không đưa PyMuPDF vào MVP chỉ để render PDF nếu chưa có license review, vì licensing model của PyMuPDF có thể không phù hợp với cách phân phối closed-source/commercial mong muốn.

---

# 27. Test architecture

```text
tests/
├── unit/
├── integration/
├── regression/
├── security/
├── performance/
├── fixtures/
│   ├── public/
│   └── private/
└── golden/
```

## Unit

- ByteRange
- hashing
- certificate parsing
- profile selection
- output naming
- queue state

## Integration

- PKCS#11
- PDF signing
- verification
- token reconnect
- updater

## Regression

- ECUS golden input/output
- exact field structure expectations
- PUS compatibility profiles

## Security

- tampered update
- wrong hash
- invalid signature manifest
- path traversal in update package
- malicious PDF path
- malicious filename
- ZIP slip nếu update là ZIP
- log secret leak
- PIN persistence

---

# 28. AI Review Gate

Mỗi milestone phải có một bước review độc lập.

## Review A — Architecture review

AI reviewer phải trả lời:

1. Module nào có trách nhiệm ký?
2. Private key có bao giờ đi ra khỏi token không?
3. UI có gọi trực tiếp PKCS#11 không?
4. Batch có serialize signing đúng không?
5. PDF có bị rewrite không?
6. Verification có bắt buộc trước commit không?

## Review B — Security review

Kiểm tra:

- secret handling
- path handling
- command injection
- update security
- supply chain
- dependency vulnerabilities
- unsafe deserialization
- malicious PDF
- DLL loading
- arbitrary code execution

## Review C — PDF interoperability review

Kiểm tra:

- ByteRange
- Contents
- CMS
- certificate chain
- signature field
- incremental update
- PDF viewers
- ECUS baseline
- PUS baseline

## Review D — UX review

Kiểm tra:

- user hiểu file nào thành công
- lỗi có dễ xử lý
- batch không làm mất dữ liệu
- token state có rõ
- progress chính xác
- không có nút nguy hiểm mặc định

## Review E — Production review

- installer
- code signing
- update rollback
- version metadata
- license notices
- crash recovery
- Windows 10/11

---

# 29. Không cho AI Agent tự đánh giá là “đã hoàn tất”

Một milestone chỉ được PASS khi có bằng chứng:

```text
[ ] tests pass
[ ] lint pass
[ ] type check pass
[ ] pip-audit pass hoặc risk được ghi rõ
[ ] golden PDF regression pass
[ ] batch stress pass
[ ] token integration pass
[ ] update security pass (nếu milestone có update)
[ ] manual UI test pass
[ ] real PUS test pass (milestone compatibility)
```

Nếu thiếu test thực tế PUS thì trạng thái phải là:

```text
TECHNICALLY READY / PUS REAL-WORLD VALIDATION PENDING
```

---

# 30. Lộ trình thực hiện

## Phase 0 — Research lock

### Việc cần làm

- đọc đặc tả này
- inspect 2 golden sample
- xác nhận pyHanko version phù hợp
- xác nhận PySide6 licensing route
- xác nhận pypdfium2 packaging
- lập dependency matrix
- lập token compatibility matrix

### Output

```text
ARCHITECTURE_DECISION_RECORD.md
DEPENDENCY_MATRIX.md
TOKEN_COMPATIBILITY.md
```

Không code UI lớn.

---

## Phase 1 — PDF laboratory

Mục tiêu: chứng minh có thể tạo output cryptographic signature hợp lệ.

### Việc cần làm

1. Import golden input.
2. Parse PDF.
3. Detect existing signatures.
4. Tạo signature field.
5. Ký bằng test certificate trước.
6. Ký bằng PKCS#11 token.
7. Parse CMS.
8. Verify signature.
9. So sánh output với ECUS structural baseline.
10. Không làm thay đổi page content.

### PASS condition

Output mở tốt bằng PDF viewer và validation engine.

---

## Phase 2 — Token abstraction

### Việc cần làm

- PKCS#11 library discovery.
- enumerate slots.
- enumerate certificates.
- identify private key.
- login session.
- sign digest.
- reconnect handling.
- timeout handling.
- concurrency guard.

### PASS

Rút/cắm token không crash app.

---

## Phase 3 — PUS Safe

### Việc cần làm

- implement profile.
- invisible default.
- incremental update.
- post-sign validation.
- preserve original content.
- golden fixture tests.

### PASS

Mẫu tương ứng với file user gửi phải ký được và được user xác nhận PUS nhận diện.

---

## Phase 4 — Batch engine

### Việc cần làm

- job model
- queue
- UI progress
- retry
- pause/resume
- cancel
- atomic commit
- recovery
- 10/50/100/500 file stress test

### PASS

Một file lỗi không gây cascade failure.

---

## Phase 5 — UI/UX

### Việc cần làm

- Main window.
- drag/drop.
- PDF preview.
- certificate selector.
- profile selector.
- result panel.
- dark/light theme.
- history.
- about.

---

## Phase 6 — Signature appearance

### Việc cần làm

- template engine
- visible signature
- drag position
- scale
- QR
- image/logo

PUS Safe không tự bật.

---

## Phase 7 — Diagnostics & support

- health check
- error codes
- diagnostic export
- log redaction
- support bundle

---

## Phase 8 — Update system

- manifest
- signature verification
- hash verification
- updater helper
- rollback
- beta/stable channels

---

## Phase 9 — Packaging & release

- PyInstaller onedir.
- signed binaries.
- installer.
- legal/license notices.
- version info.
- release notes.
- SHA256 release hashes.

---

# 31. Release checklist

```text
[ ] Version bumped
[ ] Changelog written
[ ] Git tag created
[ ] Tests pass
[ ] Dependency audit pass
[ ] License report updated
[ ] Golden samples pass
[ ] Token regression pass
[ ] Batch stress pass
[ ] PUS manual test pass
[ ] Installer built
[ ] EXE/DLL signed
[ ] Manifest signed
[ ] SHA256 published
[ ] Rollback tested
[ ] About information checked
[ ] Disclaimer checked
```

---

# 32. Phiên bản đầu tiên đề xuất

## Golden Signing 0.1.0-alpha

Phạm vi:

- Windows 10/11 64-bit.
- PDF only.
- invisible signing.
- PKCS#11 first.
- certificate discovery.
- PUS Safe profile.
- one file.
- batch.
- post-sign verify.
- logs.
- diagnostic report.
- basic modern UI.

Chưa cần:

- cloud/remote signing UI
- advanced appearance editor
- watch folder
- full CLI automation
- LTV/LTA production guarantee

---

# 33. Golden Signing 0.2.0-beta

- visible signature editor
- Explorer context menu
- history
- watch folder
- robust reconnect
- improved certificate trust validation
- multiple token lanes
- CLI
- signed updates

---

# 34. Golden Signing 1.0.0

Chỉ release 1.0.0 khi:

- Signing Core ổn định.
- PUS Safe profile đã được kiểm chứng thực tế.
- Batch regression ổn định.
- token adapter được kiểm tra trên các CA/token mục tiêu.
- update system an toàn.
- installer code-signed.
- documentation hoàn chỉnh.

---

# 35. Các vấn đề AI Agent phải nghiên cứu thêm trước code

AI Agent phải tự nghiên cứu và đưa kết luận vào `RESEARCH_DECISIONS.md`:

1. pyHanko 0.37.0 API phù hợp với production flow nào.
2. API PKCS#11 nào ổn định trên Windows.
3. Windows CSP/KSP fallback implementation.
4. PySide6 licensing cho distribution mong muốn.
5. pypdfium2 license bundle obligations.
6. PDF.js có cần thiết không; nếu dùng thì license/package strategy.
7. PyInstaller onedir vs onefile.
8. Windows Authenticode/Trusted Signing.
9. Update manifest signing strategy.
10. Safe handling of DLL discovery/loading.
11. Certificate chain validation cho CA Việt Nam.
12. OCSP/CRL retrieval behavior.
13. Timestamp service architecture.
14. PAdES B-B/B-T/B-LT/B-LTA compatibility.
15. PUS acceptance behavior.
16. Threat model của local desktop signer.

AI không được lấy blog ngẫu nhiên làm nguồn duy nhất cho các quyết định cryptographic/licensing/security.

---

# 36. Threat model cơ bản

## Assets

- private key trên token
- PIN
- certificates
- PDF documents
- signed PDFs
- update signing key/public key
- local history

## Threats

- malicious PDF
- malicious DLL
- compromised update server
- tampered installer
- token removal
- PIN shoulder surfing
- malicious local application
- path traversal
- output replacement
- corrupted batch state

## Controls

- no private key export
- signed binaries
- signed update manifest
- hash verification
- safe DLL search
- allowlisted update endpoints
- path canonicalization
- atomic output
- signature verification
- redacted logs
- least privilege

---

# 37. Điều không được làm

- Không dùng `eval`, `exec` trên dữ liệu PDF/config.
- Không tải script từ server rồi execute.
- Không auto-install dependency từ internet khi runtime.
- Không tự tải DLL token từ nguồn không tin cậy.
- Không lưu PIN trong JSON.
- Không dùng base64 PIN như “mã hóa”.
- Không copy certificate private key ra temp.
- Không overwrite file gốc mặc định.
- Không silently ignore failed verification.
- Không catch-all exception rồi báo “Success”.

---

# 38. Definition of Done cho một file ký

Một file chỉ được đánh dấu `SUCCESS` khi toàn bộ điều kiện sau đúng:

```text
PDF input readable
AND
preflight PASS/WARN acceptable
AND
certificate valid for signing
AND
token signing succeeded
AND
CMS constructed successfully
AND
PDF serialized successfully
AND
ByteRange valid
AND
signature cryptographically valid
AND
certificate extracted successfully
AND
output reopened successfully
AND
output hash recorded
AND
atomic commit succeeded
```

Nếu bất kỳ bước nào FAIL → không SUCCESS.

---

# 39. Definition of Done cho batch

Batch chỉ SUCCESS khi mọi file đã ở terminal state:

```text
SUCCESS
FAILED
SKIPPED
CANCELLED
```

Không để job ở trạng thái mơ hồ sau khi app restart.

UI phải hiển thị:

```text
Đã hoàn tất: 97
Thất bại: 2
Bỏ qua: 1
```

---

# 40. Yêu cầu về tài liệu cho AI Agent

Repository phải có:

```text
README.md
ARCHITECTURE.md
SECURITY.md
RELEASE.md
CHANGELOG.md
DEPENDENCIES.md
LICENSES.md
PUS_COMPATIBILITY.md
TROUBLESHOOTING.md
AI_REVIEW.md
```

Mỗi release cập nhật:

```text
CHANGELOG.md
PUS_COMPATIBILITY.md
DEPENDENCIES.md
```

---

# 41. Nguồn nghiên cứu chính

1. ETSI, **EN 319 142-1 PAdES digital signatures; Part 1: Building blocks and PAdES baseline signatures**. ETSI đang có phiên bản 1.3.0 ở trạng thái approval trong 2026.  
   https://www.etsi.org/technical-groups/esi/

2. ETSI, EN 319 142-1 V1.2.1 — mô tả các mức PAdES B-B, B-T, B-LT, B-LTA và yêu cầu interoperability.  
   https://www.etsi.org/deliver/etsi_EN/319100_319199/31914201/01.02.01_60/en_31914201v010201p.pdf

3. Adobe PDF 32000-1 — PKCS#7 PDF signatures, `/Contents`, `/ByteRange`, `/SubFilter`, `adbe.pkcs7.detached`, `adbe.pkcs7.sha1`.  
   https://opensource.adobe.com/dc-acrobat-sdk-docs/standards/pdfstandards/pdf/PDF32000_2008.pdf

4. pyHanko documentation — PDF signing, CMS, ByteRange, PAdES, PKCS#11, validation, timestamps.  
   https://docs.pyhanko.eu/en/latest/

5. pyHanko GitHub — MIT license, PKCS#11 and signature tooling.  
   https://github.com/MatthiasValvekens/pyHanko

6. PyPI pyHanko — phiên bản tại thời điểm đặc tả: 0.37.0, phát hành 2026-08-31, Python >=3.10, MIT.  
   https://pypi.org/project/pyHanko/

7. Qt for Python / PySide6 — binding chính thức Python cho Qt 6, LGPLv3/GPLv3 hoặc commercial license.  
   https://doc.qt.io/qtforpython-6/

8. pypdfium2 — PDFium bindings, license Apache-2.0/BSD-3-Clause và yêu cầu shipping licenses của PDFium dependencies.  
   https://github.com/pypdfium2-team/pypdfium2

9. PyInstaller — đóng gói Python app standalone cho Windows, hỗ trợ onedir/onefile.  
   https://pyinstaller.org/en/stable/

10. pip-audit — audit dependency vulnerabilities và hỗ trợ SBOM.  
    https://github.com/pypa/pip-audit

11. Microsoft, SmartScreen reputation / code signing.  
    https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation

12. Microsoft, Authenticode signing.  
    https://learn.microsoft.com/en-us/windows/win32/dxtecharts/authenticode-signing-for-game-developers

---

# 42. Kết luận cuối cho AI Agent

Golden Signing phải được xây như một **cryptographic desktop application**, không phải một tiện ích chèn ảnh chữ ký.

Ưu tiên phiên bản đầu:

```text
PYTHON
+ PYSIDE6
+ PYHANKO
+ PKCS#11
+ PYPDFIUM2
+ SQLITE
+ PYINSTALLER
```

Trọng tâm:

```text
PUS compatibility
        ↓
Signing correctness
        ↓
Token reliability
        ↓
Batch stability
        ↓
Post-sign verification
        ↓
Modern UI
        ↓
Automation
        ↓
Secure updates
```

**Do not start with visual polish. Start with a reproducible cryptographic signing test that passes the two supplied golden PDFs and can subsequently be validated on PUS.**

---

# 43. Thông tin sản phẩm hiển thị chính thức

**Golden Signing**  
PDF Digital Signature Utility

**Developer:** HOC HK  
**Email:** hochk2019@gmail.com  
**Phone:** 0868.333.606  
**Dịch vụ:** Cung cấp dịch vụ tư vấn hải quan miễn phí - vận chuyển hàng hóa toàn quốc.

Phiên bản: `0.1.0-alpha`

---

## Phụ lục A — Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Đặt tên Golden Signing | DONE |
| Phân tích PDF gốc | DONE |
| Phân tích PDF ECUS | DONE |
| Xác định cấu trúc signature | DONE |
| Xác định PUS Safe direction | DONE - cần real PUS validation |
| Quyết định Python | APPROVED |
| UI framework | PySide6 |
| Signing engine | pyHanko |
| Rendering | pypdfium2 |
| Token backend | PKCS#11 first |
| Windows CSP/KSP fallback | TODO |
| Batch engine | TODO |
| PUS compatibility lab | TODO |
| Remote update | TODO |
| Code signing | TODO |
| Installer | TODO |

---

## Phụ lục B — Hai file mẫu phải được coi là tài sản test quan trọng

Tên logic:

```text
GOLDEN_INPUT_ECUS_SAMPLE
GOLDEN_OUTPUT_ECUS_SAMPLE
```

Không được thay thế fixture bằng file khác mà không cập nhật checksum và CHANGELOG.

---

## Phụ lục C — Ghi chú về dữ liệu mẫu

Các PDF mẫu chứa dữ liệu doanh nghiệp thực tế. Không đưa chúng lên repository public, issue tracker công khai hoặc hệ thống AI bên thứ ba nếu chưa được phép. Khi cần chia sẻ cho quá trình test, ưu tiên dùng bản đã ẩn thông tin nhạy cảm hoặc môi trường private.

---


# 44. REVISION 1.1.0 — Profile theo chứng thư, visible/invisible, metadata & AI guardrails

Phần này **ghi đè/bổ sung** các quyết định cũ khi có mâu thuẫn. AI Coding Agent phải đọc phần này sau cùng trước khi lập kế hoạch coding.

## 44.1. Quyết định về visible/invisible signature

Golden Signing **bắt buộc hỗ trợ cả hai**:

```text
INVISIBLE
VISIBLE
ASK_EVERY_TIME
```

Không được thiết kế sản phẩm theo giả định rằng mọi chứng từ Hải quan đều đã có con dấu/chữ ký hình ảnh.

### Quy tắc UX

- Nếu PDF đã có hình con dấu/chữ ký, preflight có thể phát hiện bằng heuristic/preview và hiển thị cảnh báo: `Tài liệu đã có nội dung giống chữ ký/con dấu. Bạn có muốn ký vô hình để giữ nguyên giao diện không?`.
- Đây là **gợi ý**, không phải quyết định cưỡng chế.
- Nếu profile được đặt `INVISIBLE`, không tạo visible widget/appearance.
- Nếu profile được đặt `VISIBLE`, bắt buộc cho xem preview appearance trước khi người dùng bấm Ký.
- `ASK_EVERY_TIME` dành cho người dùng cần xử lý lẫn hai loại chứng từ.
- Không dùng OCR để quyết định an toàn việc ký trong MVP; nếu có heuristic thì chỉ dùng để cảnh báo.

### UI nhanh

```text
Hiển thị chữ ký số
(●) Vô hình — không thay đổi giao diện tài liệu
( ) Hiển thị trên PDF
( ) Hỏi mỗi lần
```

---

## 44.2. Signature Profile — tính năng bắt buộc

Golden Signing phải có **profile riêng cho từng chứng thư/chủ thể ký** và không được chỉ lưu một profile toàn cục.

Mỗi profile phải có định danh ổn định dựa ưu tiên theo:

```text
certificate_sha256_fingerprint
        ↓
issuer + serial
        ↓
subject/organization (fallback display only)
```

Không dùng tên công ty đơn thuần làm primary key vì có thể trùng.

### Mỗi profile lưu

```text
Profile ID
Profile name
Certificate fingerprint SHA-256
Subject / Organization
Issuer
Certificate serial
Logo asset
Signature mode: visible / invisible / ask
Appearance template
Page placement
X/Y/W/H hoặc anchor
Opacity
Show signer name: ON/OFF
Show date/time: ON/OFF
Show reason: ON/OFF
Show location: ON/OFF
Show contact: ON/OFF
Show issuer: ON/OFF
Show certificate serial: ON/OFF
Show labels: ON/OFF
Custom text fields
Reason presets
Location
Contact information
Timestamp policy
Validation policy
PUS profile
Output naming rule
Output folder rule
Overwrite policy
Post-sign verification: ON/OFF (khuyến nghị ON và không cho tắt trong PUS Safe)
```

### Auto-load profile

Khi người dùng chọn chứng thư:

```text
Select Certificate
      ↓
Find certificate fingerprint
      ↓
Load linked Signing Profile
      ↓
Load logo
      ↓
Load appearance
      ↓
Load PUS/Modern profile
      ↓
Load output rules
      ↓
Preview current configuration
```

Nếu đã có profile cho certificate đó, **không hỏi lại mọi thiết lập**.

Nếu chưa có:

```text
Chưa có profile cho chứng thư này.
[ Tạo profile nhanh ]
[ Dùng profile mặc định ]
```

### Remember gần nhất

Phải lưu:

```text
last_used_certificate
last_used_profile
last_used_folder
last_used_signature_mode
last_used_appearance_template
```

Nhưng `last_used_profile` chỉ là convenience; **certificate-linked profile luôn có ưu tiên cao hơn**.

---

## 44.3. Logo management

Profile phải hỗ trợ logo độc lập.

Người dùng có thể:

```text
[ Chọn logo ]
[ Xóa logo ]
[ Thay logo ]
[ Xem trước ]
```

Định dạng đề xuất:

- PNG
- JPEG
- SVG nếu renderer/appearance pipeline hỗ trợ ổn định

Golden Signing phải copy asset vào thư mục dữ liệu ứng dụng hoặc dùng asset storage có version/hash, **không phụ thuộc vào đường dẫn tạm** như Desktop/Downloads.

Ví dụ:

```text
%LOCALAPPDATA%\GoldenSigning\profiles\assets\<sha256>.png
```

Không được để profile hỏng vì người dùng đổi tên hoặc di chuyển file logo gốc.

---

## 44.4. Appearance Designer — không chỉ logo

Visible signature phải hỗ trợ template kéo/thả hoặc cấu hình trực quan.

### Thành phần có thể bật/tắt

```text
[✓] Logo
[✓] Đã ký bởi / Signer name
[✓] Ngày giờ ký
[ ] Lý do ký
[ ] Địa điểm
[ ] Thông tin liên hệ
[ ] Issuer / CA
[ ] Serial chứng thư
[ ] Fingerprint rút gọn
[ ] Nhãn (Reason:, Location: ...)
[ ] QR kiểm tra
[ ] Custom text
```

Cho phép chỉnh:

- font
- cỡ chữ
- bold/italic
- căn lề
- màu
- opacity của logo
- khoảng cách
- bố cục
- kích thước khung
- vị trí
- xoay nếu cần ở phase sau

**Không được nhầm appearance với nội dung cryptographic của signature.**

---

## 44.5. Bổ sung thông tin “vào chữ ký số” — cách thiết kế đúng

Golden Signing phải phân biệt 3 lớp:

### Lớp A — Cryptographic signed data

Là dữ liệu thực sự được bảo vệ bởi chữ ký và/hoặc CMS/PAdES profile. Chỉ thêm dữ liệu nếu tiêu chuẩn/profile và thư viện signing hỗ trợ đúng cách.

### Lớp B — PDF signature dictionary / standard signing properties

Các trường chuẩn có thể có tùy profile như:

- Reason
- Location
- ContactInfo / Contact
- Signer identity
- Signing time
- Commitment / related properties khi profile hỗ trợ

### Lớp C — Visual appearance

Các trường được **hiển thị trên PDF**:

- logo
- tên
- ngày giờ
- lý do
- vị trí
- liên hệ
- issuer
- serial
- text tùy biến

**Custom text không được tự ý nhét vào CMS như một signed attribute tùy biến** nếu chưa có đặc tả/verification tương ứng. Mặc định custom text chỉ thuộc lớp appearance hoặc application profile metadata.

### Nút bật/tắt

Mọi trường hiển thị phải có checkbox.

Ví dụ:

```text
Thông tin hiển thị trên chữ ký

[✓] Người ký
[✓] Ngày giờ
[ ] Lý do: Thanh toán / Khai báo Hải quan
[ ] Địa điểm: Bắc Ninh, Việt Nam
[ ] Liên hệ
[ ] CA
[ ] Serial
[ ] Fingerprint
[ ] Nội dung tùy chỉnh: __________________
```

---

## 44.5. Golden Branding — logo ứng dụng và hệ thống nhận diện

### Mục tiêu

Golden Signing phải có nhận diện thương hiệu nhất quán nhưng **không được để logo chiếm quá nhiều diện tích giao diện làm việc**. Logo do chủ dự án cung cấp là `golden.svg`.

Logo hiện tại là artwork hình vuông, có biểu tượng vàng/cam, đường viền nâu và dòng chữ `GOLDEN LOGISTICS`.

**Không được tự ý vẽ lại, bóp méo tỷ lệ, crop bất thường, đổi màu hoặc thay nội dung logo** nếu chưa được chủ sở hữu thương hiệu cho phép.

### Quyết định vị trí logo

Với desktop application có persistent sidebar/navigation rail, vị trí hợp lý nhất là **góc trên của sidebar**, cạnh tên sản phẩm. Đây là vùng branding cấp ứng dụng và không lấy diện tích của vùng làm việc PDF. UI/UX Pro Max cũng khuyến nghị persistent sidebar/navigation rail cho nhóm chức năng desktop chính. citeturn745010search1turn745010search3

```text
┌───────────────────────────────────────────────────────────┐
│ ┌──────┐  Golden Signing                                  │
│ │MARK  │  Ký số PDF                                       │
│ └──────┘                                                  │
│                                                           │
│  Trang chủ                                                 │
│  Ký tài liệu                                               │
│  Hàng đợi                                                   │
│  Lịch sử                                                    │
│  Chứng thư & Profile                                       │
│  Thiết lập                                                  │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Kích thước và chế độ

**Sidebar mở**
- Logo mark: khoảng 36–40 px.
- `Golden Signing`: 17–19 px, semibold.
- Có thể có dòng phụ `Ký số PDF` với cỡ nhỏ hơn.

**Sidebar thu gọn**
- Chỉ hiển thị logo mark khoảng 28–32 px.
- Có tooltip/focus label `Golden Signing`.

**Không sử dụng full logo `GOLDEN LOGISTICS` kích thước lớn trong workspace chính.**

### Phân biệt thương hiệu và tên sản phẩm

`golden.svg` có dòng `GOLDEN LOGISTICS`, trong khi product name là `Golden Signing`.

Phải phân biệt:

```text
Product:  Golden Signing
Developer: HOC HK
Brand:     Golden Logistics (nếu sử dụng)
```

UI chính luôn ưu tiên tên **Golden Signing**. Không được hiển thị `GOLDEN LOGISTICS` như tên sản phẩm.

### Asset variants bắt buộc

AI Coding Agent phải chuẩn hóa asset:

```text
assets/
└── branding/
    ├── golden.svg
    ├── golden-mark.svg
    ├── golden-mark.png
    ├── golden-app-icon.ico
    └── README.md
```

Trong đó:
- `golden.svg`: giữ nguyên file nguồn.
- `golden-mark.svg`: phiên bản chỉ biểu tượng để dùng ở sidebar collapsed và icon.
- PNG là fallback khi component/renderer không dùng SVG ổn định.
- `.ico` phải chứa các kích thước Windows phù hợp: 16, 20, 24, 32, 40, 48, 64, 128, 256 px.

AI phải ưu tiên nguồn SVG vector cho các giao diện lớn, không rasterize một lần rồi phóng to lại.

### Windows App Icon

Dùng **logo mark**, không dùng full logo có chữ nhỏ, cho executable, shortcut, Start Menu, taskbar, installer và các nơi Windows yêu cầu application icon.

Phải kiểm tra icon ở kích thước nhỏ thực tế để bảo đảm nhận diện.

### Màu thương hiệu và design tokens

AI phải lấy màu hiện hữu của logo làm cơ sở cho brand tokens, sau đó kiểm tra contrast trên nền sáng/tối.

Ví dụ:

```text
brand.primary
brand.secondary
brand.neutral
brand.surface
brand.on-brand
```

Không được dùng màu thương hiệu làm tín hiệu duy nhất cho Success/Error/Warning; trạng thái phải có thêm icon, text hoặc hình thức khác.

### Sidebar và PDF workspace

Logo chỉ thuộc vùng global navigation/branding.

Workspace phải ưu tiên:
- PDF preview;
- file list;
- batch queue;
- certificate/profile;
- signing controls.

Không đặt logo lớn ở trung tâm màn hình hoặc đè lên vùng PDF.

### Title bar

Title nên theo dạng:

```text
Golden Signing — Ký số PDF
```

Không lặp một logo lớn ở title bar khi sidebar đã có branding.

Nếu dùng custom title bar, phải giữ đầy đủ hành vi Windows: drag, minimize, maximize/restore, close, system menu, keyboard accessibility và HiDPI.

### About

About dialog sử dụng full logo vừa phải:

```text
[ FULL GOLDEN LOGISTICS LOGO ]

Golden Signing
Phiên bản 0.1.0-alpha

Nhà phát triển: HOC HK
Email: hochk2019@gmail.com
SĐT: 0868.333.606

Cung cấp dịch vụ tư vấn hải quan miễn phí
Vận chuyển hàng hóa toàn quốc

[ Kiểm tra cập nhật ]
[ Chính sách bảo mật ]
[ Miễn trừ trách nhiệm ]
[ Open Source / Licenses ]
```

Thông tin nhà phát triển phải khớp metadata sản phẩm; không nhồi toàn bộ thông tin vào màn hình chính.

### Splash

Splash **không bắt buộc**. Nếu startup nhanh thì ưu tiên không dùng splash.

Nếu cần splash:
- logo;
- Golden Signing;
- version;
- không quảng cáo;
- không animation dài.

### Update dialog

Dùng logo mark nhỏ ở header:

```text
Golden Signing
Có bản cập nhật mới

v0.1.1 → v0.1.2

[ Xem thay đổi ]
[ Cập nhật ]
[ Để sau ]
```

Update phải tuân thủ cơ chế manifest + hash + signature verification đã quy định trong tài liệu; không được dùng logo thay cho xác thực file.

### Không nhầm logo ứng dụng với logo trong chữ ký PDF

Có hai loại logo hoàn toàn độc lập:

1. **App branding logo** — nhận diện Golden Signing.
2. **Signature Profile logo** — logo doanh nghiệp/người ký được phép xuất hiện trong visible signature.

**Không tự động lấy `golden.svg` chèn vào mọi PDF.**

Khi profile của một doanh nghiệp khác được chọn, Golden Signing phải dùng logo của profile đó.

### Signature Profile

Quan hệ:

```text
Certificate A
    ↓
Signature Profile A
    ├── Company logo A
    ├── Visible / Invisible
    ├── Appearance template
    └── Signing policy
```

Certificate B có profile/logo B độc lập.

### Branding ở First Run

Màn hình First Run có thể dùng full logo nhỏ-vừa ở bên trái hoặc phía trên, nhưng nội dung chính phải tập trung vào chọn chứng thư, tạo profile, chọn thư mục, kiểm tra token và thử ký mẫu.

Không biến First Run thành màn hình quảng cáo.

### Quality gate

AI phải kiểm tra ở DPI 100/125/150/175/200%:
- không méo logo;
- không mờ;
- sidebar mở/thu gọn cân đối;
- dark/light theme ổn;
- taskbar/icon ổn;
- installer và About ổn;
- không tăng đáng kể startup time.

### UX/Design gate bắt buộc

Trước khi triển khai UI, AI phải đọc và áp dụng UI/UX Pro Max. Skill hiện công bố nhiều UI styles, color palettes, typography pairings và UX guidelines, đồng thời hỗ trợ các AI coding platforms. citeturn745010search4turn745010search1

Deliverables:

```text
docs/design/BRANDING_SPEC.md
docs/design/DESIGN_TOKENS.md
docs/design/UX_BRIEF.md
docs/design/UI_REVIEW.md
```

### Acceptance

Branding được PASS khi:
1. Người dùng nhận biết ngay Golden Signing.
2. Logo không lấn át tác vụ ký PDF.
3. Sidebar mở/thu gọn đều hợp lý.
4. Windows icon rõ ở kích thước nhỏ.
5. Không nhầm `Golden Logistics` với tên sản phẩm.
6. Full logo chỉ xuất hiện ở các vị trí có giá trị branding.
7. Logo trong Signature Profile không bị nhầm với app logo.
8. Branding không làm giảm hiệu năng hoặc độ ổn định Signing Core.

---

# 45. Feature benchmark — học từ phần mềm hiện có, không sao chép máy móc

AI Agent phải nghiên cứu lại tính năng của các phần mềm PDF signing hiện có trước khi chốt UX.

Các tính năng đã được xác nhận qua tài liệu công khai:

| Phần mềm | Tính năng đáng học | Quyết định Golden Signing |
|---|---|---|
| Adobe Acrobat | appearance tùy biến; Name, Date, Location, Reason, Distinguished Name, Labels, Logo | **Adopt** |
| ABBYY FineReader Server | visible/hidden; logo; kích thước/vị trí; Reason/Location/Contact; preview | **Adopt** |
| Foxit PDF Editor | Reason/Location; nhớ thiết lập; appearance types; preview; lock document | **Adopt có điều chỉnh** |
| PDF-XChange Editor | signature templates; Reason/Location/Contact; timestamp; permission/lock | **Adopt có điều chỉnh** |
| Ascertia PDF Sign&Seal | dynamic positioning; configurable appearance; company logo; reason/location | **Adopt** |

Adobe cho phép cấu hình graphic và bật/tắt các trường như Name, Date, Location, Reason, Distinguished Name, Labels và Logo trong signature appearance. citeturn314031search8

ABBYY cho phép chọn visible/hidden signature, thêm image/logo và đặt size/position, đồng thời cung cấp Reason/Location/Contact. citeturn314031search1

Foxit cho phép lưu Reason/Location để tái sử dụng, chọn appearance type và xem preview; tài liệu cũng mô tả kiểm tra validity và certificate. citeturn314031search0turn314031search5

PDF-XChange có signature templates và cho phép quản lý/customize appearance, logo và các display text. citeturn314031search4

**Kết luận:** Golden Signing cần có `Signature Profile + Appearance Template + Field Toggles + Remember Last Used + Auto-load by Certificate` ngay từ kiến trúc, thay vì thêm sau.

---

# 46. AI Skill Gate — bắt buộc trước UI/backend/database coding

AI Coding Agent **không được bắt đầu code UI/backend/database ngay khi nhận repo**.

## 46.1. UI/UX Skill — bắt buộc

Phải nghiên cứu và áp dụng:

**UI/UX Pro Max**

Repository chính thức: `nextlevelbuilder/ui-ux-pro-max-skill`

Tại thời điểm đặc tả này, skill công bố version `2.13.0`, với 79 UI styles, 192 color palettes, 74 font pairings, 119 UX guidelines, 105 icons và 22 stacks; repository có template riêng cho Codex. citeturn281664search0turn281664search4

### Quy trình bắt buộc

```text
Read skill
   ↓
Search applicable desktop/UI guidance
   ↓
Create UX brief
   ↓
Create design tokens
   ↓
Create information architecture
   ↓
Create wireframe
   ↓
Review accessibility
   ↓
Create visual UI
   ↓
Human review checkpoint
   ↓
Only then implement Qt UI
```

Không được “lắp widget cho chạy” rồi mới tìm cách làm đẹp.

Skill này phải được dùng cả khi:

- tạo UI mới
- sửa UI
- review UI
- accessibility review
- interaction design
- design system

Đây cũng đúng với mô tả chính thức của skill. citeturn281664search1

### Lưu ý

Repository hiện vẫn đang có issue/PR hoạt động, vì vậy AI phải **pin phiên bản/commit đã kiểm thử**, không phụ thuộc mù quáng vào `main`. citeturn281664search2turn281664search5

---

## 46.2. Backend Architecture Skill Gate

Trước khi viết service/backend modules, AI phải:

1. Tìm skill/references tốt nhất hiện có cho:
   - clean architecture
   - modular monolith desktop application
   - dependency inversion
   - Python typing
   - async/concurrency
   - secure secret handling
   - error taxonomy
   - observability
2. Đánh giá ít nhất 2 phương án.
3. Chốt ADR.
4. Viết architecture diagram.
5. Chỉ sau đó code.

Không được tự phát minh architecture lớn nếu không cần.

### Backend principle

```text
UI
 ↓
Application Services
 ↓
Domain / Contracts
 ↓
Infrastructure Adapters
```

Signing Core không được import UI.
UI không được truy cập PKCS#11 trực tiếp.
Database không được chứa business logic cryptographic.

---

## 46.3. Database Skill Gate

Trước khi tạo schema, AI phải nghiên cứu skill/references về:

- SQLite production usage
- migrations
- WAL / transaction strategy
- indexing
- audit log design
- retention
- data integrity
- backup/export

### Database principle

SQLite là lựa chọn mặc định vì desktop app single-user/local phù hợp; không dựng server DB nếu không có yêu cầu.

Schema phải có migration versioning.

Ví dụ:

```text
schema_migrations
profiles
certificates_cache
profile_certificates
appearance_templates
appearance_assets
reason_presets
signing_jobs
signing_job_items
verification_results
application_settings
update_state
```

### Không lưu secret

Không lưu:

- PIN
- private key
- token password
- raw signing key

---

# 47. Anti-Forgetting / Resume System — cơ chế chống quên bắt buộc

AI Coding Agent phải được thiết kế như một quy trình có **persistent project memory**, không phụ thuộc vào context window của một phiên.

## 47.1. Thư mục bắt buộc

```text
.ai/
├── START_HERE.md
├── PROJECT_STATE.md
├── NEXT_ACTION.md
├── DECISIONS.md
├── WORK_LOG.md
├── SESSION_HANDOFF.md
├── RISKS.md
├── REVIEW_STATUS.md
└── tasks/
    ├── 001-foundation.md
    ├── 002-token.md
    ├── 003-signing-core.md
    ├── 004-profile.md
    ├── 005-batch.md
    ├── 006-ui.md
    ├── 007-update.md
    └── 008-release.md
```

## 47.2. START_HERE.md

Phải ghi:

```text
Project: Golden Signing
Current version: 0.1.0-alpha
Current milestone: <...>
Last verified commit: <hash>
Current blocker: <...>
Next task: <...>
Required skills: <...>
Last test result: <...>
```

AI session mới **bắt buộc đọc file này trước khi sửa code**.

## 47.3. PROJECT_STATE.md

Trạng thái dạng:

```text
DONE
IN_PROGRESS
BLOCKED
TODO
DEFERRED
```

Mỗi task phải có:

```text
ID
Objective
Status
Dependencies
Files changed
Tests
Evidence
Reviewer
Commit
Next action
```

## 47.4. Checkpoint bắt buộc

Sau mỗi milestone nhỏ:

1. chạy test
2. chạy lint/type-check
3. cập nhật state
4. ghi decision nếu có
5. commit Git
6. ghi commit hash vào state

### Nếu AI bị dừng đột ngột

Phiên tiếp theo phải làm:

```text
read START_HERE.md
↓
git status
↓
read PROJECT_STATE.md
↓
read NEXT_ACTION.md
↓
inspect uncommitted changes
↓
run focused tests
↓
reconcile state vs code
↓
continue next unchecked task
```

Không được bắt đầu lại dự án từ đầu.

## 47.5. Handoff bắt buộc

Trước khi kết thúc một phiên bình thường, AI phải cập nhật:

```text
SESSION_HANDOFF.md
```

với:

- đã làm gì
- chưa làm gì
- test nào chạy
- test nào chưa chạy
- vấn đề còn lại
- file quan trọng
- commit cuối
- bước tiếp theo duy nhất được khuyến nghị

## 47.6. Crash recovery

Nếu AI dừng mà không kịp ghi handoff:

- Git là nguồn sự thật cho code.
- PROJECT_STATE là nguồn sự thật thứ hai.
- Test suite là nguồn sự thật thứ ba.

AI phải **không đánh dấu DONE chỉ dựa trên ý định**.

---

# 48. AI Review Gate nâng cấp — review phải độc lập theo nhiều vai trò

Một AI coding agent có thể tự code, nhưng không được tự chấm “đạt” chỉ bằng việc chạy happy-path test.

Mỗi milestone production phải có ít nhất 5 review pass:

### Reviewer 1 — Architect

- boundaries
- dependencies
- extensibility
- unnecessary complexity

### Reviewer 2 — Security Engineer

- token/PIN
- DLL loading
- path traversal
- updater
- malicious PDF
- log leakage
- supply chain

### Reviewer 3 — PDF/PKI Engineer

- ByteRange
- CMS
- signature dictionary
- certificate
- PAdES profile
- incremental update
- existing signatures

### Reviewer 4 — UX Designer

Phải review theo UI/UX Pro Max skill, không chỉ theo cảm nhận cá nhân.

### Reviewer 5 — QA/Release Engineer

- regression
- packaging
- clean-machine installation
- update/rollback
- performance

### Review artifact bắt buộc

Mỗi review tạo:

```text
.ai/reviews/<milestone>-architecture.md
.ai/reviews/<milestone>-security.md
.ai/reviews/<milestone>-pdf-pki.md
.ai/reviews/<milestone>-ux.md
.ai/reviews/<milestone>-qa.md
```

Mỗi file phải có:

```text
PASS / FAIL / NEEDS_CHANGES
Evidence
Open issues
Recommended action
```

---

# 49. Profile data model đề xuất

Ví dụ logical model:

```yaml
SigningProfile:
  id: uuid
  name: string
  certificate_fingerprint_sha256: string
  mode: invisible | visible | ask
  pus_profile: pus-safe | modern-pades | custom

  appearance:
    template_id: uuid | null
    logo_asset_id: uuid | null
    show_name: bool
    show_date: bool
    show_reason: bool
    show_location: bool
    show_contact: bool
    show_issuer: bool
    show_serial: bool
    show_fingerprint: bool
    show_labels: bool
    show_qr: bool
    custom_text: string | null

  signing_details:
    reason: string | null
    location: string | null
    contact: string | null
    timestamp_profile: string | null

  placement:
    page_mode: first | last | selected | all | custom
    x: float | null
    y: float | null
    width: float | null
    height: float | null

  output:
    folder_mode: same | subfolder | custom
    subfolder: string | null
    filename_template: string
    overwrite_policy: skip | rename | ask

  behavior:
    verify_after_sign: bool
    atomic_commit: bool
    preserve_original: bool
```

`verify_after_sign` phải luôn `true` trong PUS Safe.

---

# 50. UX flow chính sau revision

## Ký một file

```text
Drop PDF
   ↓
Preflight
   ↓
Certificate auto-discovery
   ↓
Auto-load company profile
   ↓
Mode loaded from profile
   ↓
[Visible] → appearance preview
[Invisible] → no visual change
   ↓
Sign
   ↓
Verify
   ↓
Success
```

## Ký hàng loạt nhiều công ty/chứng thư

Không giả định tất cả job dùng cùng certificate.

Job queue có thể phân nhóm:

```text
Company A / Certificate A → Token A lane
Company B / Certificate B → Token B lane
```

Nếu chỉ có một token được cắm:

```text
WAITING_FOR_TOKEN
```

không tự chọn nhầm certificate.

---

# 51. Settings / Profile UX

Sidebar:

```text
Tệp
Ký số
Kiểm tra
Lịch sử
────────────────
Hồ sơ ký
Mẫu hiển thị
Tự động
────────────────
Cài đặt
Cập nhật
Giới thiệu
```

Trong `Hồ sơ ký`:

```text
CÔNG TY ABC
  ✓ Chứng thư A
  Logo ABC
  PUS Safe
  Invisible

CÔNG TY XYZ
  ✓ Chứng thư B
  Logo XYZ
  Visible
  Corporate Blue
```

Nút:

```text
[+ Tạo hồ sơ]
[Sao chép]
[Chỉnh sửa]
[Xóa]
[Đặt mặc định]
[Nhập/Xuất profile]
```

Import/export profile phải **không bao giờ chứa private key hoặc PIN**.

---

# 52. Disclaimer / miễn trừ trách nhiệm

Trong `Giới thiệu`, `Settings`, installer và trang update phải có nội dung tương tự:

> **Miễn trừ trách nhiệm:** Golden Signing là công cụ hỗ trợ ký số và kiểm tra chữ ký điện tử. Người sử dụng tự chịu trách nhiệm lựa chọn chứng thư số, nội dung tài liệu, vị trí hiển thị chữ ký, cấu hình ký và việc sử dụng tài liệu sau khi ký. Golden Signing không phải là cơ quan Hải quan, không phải là tổ chức cung cấp dịch vụ chứng thực chữ ký số và không bảo đảm mọi tài liệu hoặc mọi cấu hình sẽ được mọi hệ thống bên thứ ba chấp nhận. Khả năng tiếp nhận/xác minh tại PUS hoặc hệ thống khác phụ thuộc vào hệ thống đích, chứng thư, CA, chuẩn kỹ thuật và tình trạng dịch vụ tại thời điểm sử dụng. Người dùng cần kiểm tra kết quả thực tế trước khi sử dụng tài liệu trong giao dịch chính thức.

Không dùng câu chữ mang tính cam kết pháp lý như `Đảm bảo 100%`, `PUS chắc chắn nhận`, `thay thế ECUS` trong UI hoặc marketing.

---

# 53. About / Developer information

Phải hiển thị:

```text
Golden Signing
PDF Digital Signature Utility

Developer: HOC HK
Email: hochk2019@gmail.com
Phone: 0868.333.606

Cung cấp dịch vụ tư vấn hải quan miễn phí
Vận chuyển hàng hóa toàn quốc

Version: x.y.z
Build: <build number>
Architecture: Windows x64
```

Thông tin liên hệ phải là text tĩnh trong app, nhưng phiên bản/build lấy từ build metadata.

---

# 54. Versioning policy

Dùng Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Ví dụ:

```text
0.1.0-alpha
0.1.1-alpha
0.2.0-beta
1.0.0
1.0.1
```

### Quy tắc

- PATCH: bug/security fix, không đổi contract đáng kể.
- MINOR: feature mới tương thích.
- MAJOR: breaking behavior/API/profile changes.

Không được tăng version chỉ để “có vẻ mới”.

---

# 55. Remote Update — nâng cấp yêu cầu

Updater phải có **signed manifest**, không chỉ HTTPS.

Manifest tối thiểu:

```json
{
  "product": "golden-signing",
  "version": "0.2.0",
  "channel": "stable",
  "min_os_build": "10.0.19045",
  "architecture": "x64",
  "package_url": "...",
  "sha256": "...",
  "package_size": 123456789,
  "release_notes_url": "...",
  "manifest_signature": "..."
}
```

Quy trình:

```text
HTTPS fetch
 ↓
validate manifest schema
 ↓
verify manifest signature
 ↓
compare version
 ↓
download package
 ↓
verify SHA-256
 ↓
verify package signature if applicable
 ↓
install staged update
 ↓
health check
 ↓
activate
 ↓
rollback if startup/health check fails
```

Update server compromise must **not** be enough to install arbitrary unsigned binaries.

Không chạy installer từ thư mục tạm mà không kiểm tra integrity.

---

# 56. Licensing / dependency gate cho Python desktop app

Việc chọn Python vẫn được giữ, nhưng trước khi đóng gói production AI phải lập `THIRD_PARTY_LICENSES.md`.

PyHanko hiện có bản 0.37.0 phát hành ngày 31/08/2026 và được phân phối theo MIT; package công bố extra cho `pkcs11`, `etsi`, `image-support`, `async-http` và các phần liên quan. citeturn894429search8

PySide6 là binding chính thức của Qt for Python nhưng Community Edition theo LGPLv3/GPLv3; Qt cũng có Commercial Edition. Vì vậy, **không được tự kết luận rằng đóng gói PySide6 closed-source/commercial là vô điều kiện**. AI phải review license/obligations của đúng gói/version được phân phối trước release. citeturn894429search0turn894429search1

pypdfium2 tự công bố Apache-2.0/BSD-3-Clause cho pypdfium2, đồng thời lưu ý các license của dependency/binary PDFium bundled phải được phát hành kèm binary distribution. citeturn894429search5

### Gate

```text
No release candidate
until license report is PASS.
```

---

# 57. Modern features review — thêm, nhưng có kiểm soát

AI phải đánh giá các tính năng sau và đưa vào roadmap:

### Nên có sớm

- certificate-linked profile
- auto-load profile
- recent profile
- visible/invisible/ask
- appearance templates
- logo asset management
- Reason/Location/Contact presets
- custom appearance text
- one-click “Ký lại với profile gần nhất”
- batch progress per file
- retry selected
- output preview/open folder
- signature verifier
- health check
- signed update
- rollback
- Windows Explorer context menu
- keyboard shortcuts
- dark/light/system theme
- import/export profile

### Nên có phase 2

- Watch Folder
- CLI
- multi-token lanes
- timestamp server presets
- trust-store manager
- QR verification
- notification center
- scheduled batch

### Chỉ thêm khi có use case và security model rõ

- AI document classification
- OCR
- cloud workspace
- account/login
- remote signing service
- server-based team approval

Không thêm AI vào cryptographic signing path.

---

# 58. Coding order đã điều chỉnh

AI phải thực hiện đúng thứ tự:

```text
0. Read spec + current repo
        ↓
1. Install/read mandatory skills
        ↓
2. Research & ADR
        ↓
3. Build project control-plane (.ai)
        ↓
4. Define domain contracts
        ↓
5. Token discovery prototype
        ↓
6. PDF inspection/preflight
        ↓
7. Signing Core
        ↓
8. Verification Core
        ↓
9. Profile + database
        ↓
10. Batch engine
        ↓
11. UI/UX implementation
        ↓
12. Appearance Designer
        ↓
13. Diagnostics
        ↓
14. Updater
        ↓
15. Packaging
        ↓
16. Independent AI reviews
        ↓
17. Golden fixture regression
        ↓
18. Real PUS acceptance test
        ↓
19. Release
```

**Đặc biệt:** UI/UX design phải diễn ra trước UI coding; backend architecture và DB schema phải được review trước implementation.

---

# 59. Acceptance criteria mới cho Profile

Profile subsystem chỉ PASS khi:

```text
[ ] Chọn Certificate A → tự load Profile A
[ ] Chọn Certificate B → tự load Profile B
[ ] Logo A không xuất hiện ở Profile B
[ ] Visible/Invisible được lưu riêng từng profile
[ ] Reason/Location/Contact được lưu riêng
[ ] Appearance fields bật/tắt độc lập
[ ] Last-used profile được nhớ
[ ] Reopen app vẫn khôi phục profile gần nhất
[ ] Import/export profile không chứa secret
[ ] Xóa profile không làm hỏng certificate/token
[ ] Certificate fingerprint change → không tự coi là cùng profile
```

---

# 60. Acceptance criteria mới cho Visible Signature

```text
[ ] Invisible ký không làm thay đổi nội dung hiển thị
[ ] Visible preview đúng trước khi ký
[ ] Không chèn nhầm appearance nếu profile invisible
[ ] Logo đúng profile
[ ] Custom text đúng profile
[ ] Reason/Location/Contact hiển thị đúng checkbox
[ ] Appearance không làm thay đổi page size
[ ] Appearance không rasterize toàn bộ PDF
[ ] Signature vẫn cryptographically valid
[ ] Verify pass sau commit
```

---

# 61. “Definition of Done” mới

Một feature chỉ được đánh dấu `DONE` khi có:

1. Code.
2. Test.
3. Documentation.
4. Review artifact.
5. Evidence.
6. State update.
7. Git commit.

Không chấp nhận:

```text
TODO → DONE
```

chỉ vì AI đã viết code.

---

# 62. Sources / research notes cho revision 1.1.0

- UI/UX Pro Max official repository and skill metadata: version 2.13.0, supported platforms and design intelligence scope. citeturn281664search0turn281664search1
- UI/UX Pro Max repository currently has active issues/PRs; pin tested revision for reproducible agent behavior. citeturn281664search2turn281664search5
- Adobe Acrobat digital signature appearance fields. citeturn314031search8
- ABBYY digital signature configuration and appearance options. citeturn314031search1
- Foxit PDF signing settings, reusable Reason/Location and appearance types. citeturn314031search0turn314031search5
- PDF-XChange signature templates and configurable appearance fields. citeturn314031search4
- Ascertia PDF Sign&Seal configurable appearance and dynamic positioning. citeturn314031search36
- pyHanko latest package information at time of revision. citeturn894429search8
- Qt for Python licensing. citeturn894429search0turn894429search1
- pypdfium2 licensing and bundled dependency obligations. citeturn894429search5

---

## Revision status 1.1.0

```text
Name: Golden Signing
Spec: 1.1.0
Application initial target: 0.1.0-alpha
Profile system: APPROVED
Visible + Invisible signing: APPROVED
Certificate-linked auto profile: APPROVED
Logo asset management: APPROVED
Optional signing details: APPROVED
AI skill gates: APPROVED
Anti-forgetting system: APPROVED
Independent AI review roles: APPROVED
Remote signed update: APPROVED
Disclaimer: APPROVED
Developer info: APPROVED
```

**END OF REVISION 1.1.0**

**END OF SPECIFICATION**
