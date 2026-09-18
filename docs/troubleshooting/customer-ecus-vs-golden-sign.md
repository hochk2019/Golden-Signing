# Phân tích: cửa sổ ECUS sau khi bấm Ký (Golden Sign)

## 1. Cửa sổ trong ảnh là gì?

| Đặc điểm | Giá trị trong ảnh | Golden Sign thật |
|---|---|---|
| Title bar | `ECUS` | `Golden Sign — Sản phẩm của Golden Logistics` |
| Nội dung | `Lấy kết quả trình ký` / `Lấy phản hồi trình ký ...` | `Ký số` / `Chọn chứng thư số` / `Token` / `Chứng thư số` |
| Nút | `Đóng` (ECUS) | `OK` trên QMessageBox Golden Sign |

**Kết luận:** Ảnh là app **ECUS5VNACCS / ECUS**, không phải lỗi UI Golden Sign.

## 2. Golden Sign có mở ECUS khi bấm Ký không?

**Không.** Trong `src/golden_signing/` không có lệnh launch ECUS/ECUSSignPro/trình ký.

Chỉ các chỗ spawn process (không phải ECUS):

- `explorer` / mở thư mục output
- `certutil` ẩn cửa sổ (quét certmgr)
- PowerShell **update helper** (chỉ khi cập nhật app)
- LibreOffice headless (nếu convert Office)

Luồng bấm **Ký số** trong Golden Sign:

```text
_on_sign → chọn CKS/PKCS#11 → BatchEngine.sign từng PDF
  → file *_signed.pdf trong thư mục output
  → KHÔNG gọi ECUS
```

## 3. Vì sao sau khi ký lại thấy dialog ECUS?

Thực tế quy trình khách hàng thường là **hai app**:

```text
A. Golden Sign: ký PDF bằng USB token (local, PUS Safe)
B. ECUS5VNACCS: khai tờ khai / trình ký / lấy phản hồi từ ECUSSignPro
```

Dialog “Lấy phản hồi trình ký…” là **ECUS đang chờ server / bên duyệt ký** — không phải Golden Sign báo lỗi PIN.

Có thể khách:

1. Bấm Ký ở Golden Sign (thành công hoặc fail — phải xem **status bar / cửa sổ Golden Sign**).
2. Mở ECUS để lấy kết quả trình ký / gửi hải quan.
3. ECUS treo progress → hiểu nhầm là lỗi của Golden Sign.

Hoặc ECUS đang chạy nền sẵn và “bật lên” sau thao tác ký (người dùng thao tác song song).

## 4. Nhiều loại chữ ký số — ảnh hưởng thế nào?

| Loại CKS | Ký trong Golden Sign (64-bit) | ECUS / trình ký |
|---|---|---|
| **ECA token** + `eca_csp11_v1.dll` x64 | OK (máy dev đã test) | Theo profile ECUS |
| **CA2 / VNPT / FPT** middleware **x64** | OK nếu DLL load được | Tùy cấu hình ECUS |
| Middleware **chỉ 32-bit** (thư mục `TSD\ECUS_EX4`, SysWOW64) | **Không load PKCS#11** trong Golden Sign x64 | ECUS 32-bit **vẫn chạy được** |
| Certmgr có CKS nhưng **không private key / Secure Email** | Golden Sign **ẩn** (không cho ký) | ECUS có thể vẫn liệt kê |
| CKS **hết hạn** | **Không hiện** trong Golden Sign | Tùy app |

→ “Máy mình OK, máy khách lỗi” thường là **khác middleware CA / khác bitness DLL**, không phải Golden Sign tự mở ECUS.

## 5. Cách phân biệt lỗi thật của Golden Sign

Sau khi bấm **Ký số**, **chỉ nhìn Golden Sign**:

| Hiện tượng | Nghĩa là |
|---|---|
| Cột Trạng thái: `Đã ký` / `Thành công`, có file `*_signed.pdf` | Golden Sign **đã ký OK** |
| Dialog tiêu đề **Token** / **Chứng thư số** | Lỗi CKS/PIN/middleware — đây mới là lỗi Golden Sign |
| Dialog **Batch / Ký số** với thông báo exception | Lỗi khi ký file |
| Không có dialog Golden Sign, chỉ thấy ECUS | **Không phải lỗi Golden Sign** |

Log phụ trợ: `%LOCALAPPDATA%\GoldenSign\` (nếu bật file log).

## 6. Hướng xử lý đề xuất

### Với Golden Sign (app)

1. Đã thêm/bổ sung: lọc DLL PKCS#11 **đúng bitness** (bỏ x86 khi app x64).
2. Thông báo lỗi load PKCS#11 nêu rõ **DLL x64 vs app 64-bit** + cách cài middleware CA.
3. Nếu chọn CKS không có trên token: dialog liệt kê **serial trên token** vs serial đã chọn.
4. Sau batch ký: UI/cột trạng thái phải rõ **thành công/thất bại từng file** (khách chụp lại phần này nếu lỗi).

### Với quy trình khách hàng

1. Ký file bằng Golden Sign trước → mở **thư mục output** xác nhận `*_signed.pdf`.
2. **Chỉ** dùng ECUS cho khai tờ khai / quy trình trình ký riêng — không coi progress ECUS là kết quả Golden Sign.
3. Nếu ECUS “Lấy phản hồi trình ký” treo: đó là luồng **ECUSSignPro / server Thái Sơn** — kiểm tra bên duyệt ký, mạng, tài khoản trình ký — **ngoài phạm vi lỗi PIN Golden Sign**.
4. Cài middleware CA **x64** trên máy khách nếu Golden Sign báo sai kiến trúc DLL.

### Khi báo lỗi lại

Cần:

- Ảnh **cửa sổ Golden Sign** (title `Golden Sign…`) sau bấm Ký  
- Cột trạng thái file trong danh sách  
- Tên CKS + serial trong dialog Chọn chứng thư số  
- Có file `*_signed.pdf` hay không  

Không cần ảnh ECUS để chẩn đoán lỗi ký trong Golden Sign.

## 7. Kết luận

- Cửa sổ trong ảnh **không phải** lỗi PIN/CKS của Golden Sign.
- Golden Sign **không** launch ECUS khi ký.
- “Nhiều loại CKS” ảnh hưởng ở bước **load middleware PKCS#11 bitness** và **CKS có private key / còn hạn** — đã xử lý trong build mới; vẫn cần máy khách cài middleware **x64** đúng CA.
- Lỗi thật của Golden Sign phải lấy từ **UI/log Golden Sign** ngay sau bấm Ký.
