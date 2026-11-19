# PDF sang ảnh và Word — chữ dành cho người dùng

TASK_ID=DOCUMENT-CONVERT-CUSTOMER-COPY-20261119
BASE_SHA=a589008be5d7be371789551ffc11e750db46270b
TRACKER=Issue689/comment7006239694
DEPENDENCY=PR774_AND_PR775_DELIVERED_RECEIPTS_CLOSED

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức tạp thì làm từng spec

## Phạm vi khóa

Hai trang `/documents/pdf-to-images` và `/documents/pdf-to-word`; chỉ chữ,
khối nội dung và tên/mô tả trang. Ba tệp ứng dụng: portal.js, portal-i18n.js,
copyfast_pages.py. Đúng 13 phép thay hữu hạn, 28 khóa mới; 148/151 tệp nguồn
bảo vệ. Không đổi tên hàm/chữ ký, quyền, API, dữ liệu, cấu hình, bộ xử lý,
Bot, provider, ví, PayOS hoặc chuyển động.

## Thứ tự và nghiệm thu

| Spec | Kết quả chính | Bằng chứng bắt buộc | Phụ thuộc |
|---|---|---|---|
| DCC-01 | Quan sát BASE thật của hai trang | 24 cấu hình/trang, screenshot và dữ liệu chỉ đọc | PR775 giao xong |
| DCC-02A | Hai ô nguồn và hướng dẫn đúng VI/EN/ZH | Thuộc tính không phải chữ giữ nguyên, giới hạn thật | BASE RED |
| DCC-02B | PDF sang ảnh không có panel giải thích thừa | Form, kho tệp, lịch sử và quyền giữ | BASE RED |
| DCC-02C | PDF sang Word rõ giới hạn chữ bôi chọn | Không hứa OCR hoặc giữ hình/bảng/phông/bố cục | BASE RED |
| DCC-02M | Tên/mô tả ngay từ HTML đầu đúng ngôn ngữ | HTMLResponse và bootstrap thật | Hai page proposal |
| DCC-03 | Ghép đúng bản sửa worker | So schema/OLD/NEW, 13 phép thay, nguồn ngoài phạm vi nguyên | Ba proposal độc lập |
| DCC-04 | Không hồi quy | Physical/source/native/shell, biên lịch sử hữu hạn, không lược assertion cũ | 03 |
| DCC-05 | Báo cáo và Tester đủ | Tài liệu hiện tại/gốc, case, review và manifest sạch | 04 |
| DCC-06 | Giao một đợt lên web | Một PR, exact HEAD CI, merge, tree, deploy, VPS/assets/receipt | 05 |

Ba worker Antigravity chỉ trả JSON trong ba thư mục riêng; Root áp dụng tuần tự.
Không có shared mutable source trong lúc worker chạy. Chỉ tiếp quản ứng dụng
sau hai lần sai thật cùng đoạn; lỗi phiếu hoặc QA của Root không tính worker.

## Những điều không được suy ra

Chỉ đọc biểu mẫu không chứng minh tệp PNG/ZIP/DOCX cuối thành công.
Native localhost không chứng minh production đã đăng nhập, thiết bị thật,
Safari, toàn bộ tương phản hoặc khả năng tiếp cận. Mọi UNKNOWN giữ mở.
Không bật cờ production để qua QA; hai cờ chuyển đổi chỉ bật trong child
QA dùng SQLite/assets mới riêng, môi trường máy không đổi.

Motion M-FINAL-01..06 vẫn cuối. Goal toàn ứng dụng ACTIVE/incomplete.
