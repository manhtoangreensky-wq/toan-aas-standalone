# Đọc chữ từ ảnh/PDF và PDF quét sang Word

TASK_ID=DOCUMENT-OCR-CUSTOMER-COPY-20261119
BASE_SHA=8ba0d0452f86dcc3d72e5087351134902eb4e659
TRACKER=Issue689/comment7008143289
DEPENDENCY=PR776_DELIVERED_RECEIPTS_READBACK

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức tạp thì làm từng spec

## Phạm vi

Chỉ ba trang `/documents/ocr`, `/documents/pdf-ocr`,
`/documents/pdf-ocr-to-word`. Ba field factory, ba renderer, sáu nhánh
tên/mô tả JS và sáu entry từ điển HTML đầu; 36 khóa mới.
Đúng 19 phép thay/3 tệp ứng dụng, 148/151 nguồn bảo vệ. Không thay API,
quyền, mặc định/mã `auto/vi/en`, bộ xử lý, Bot, ví, PayOS, ENV hay motion.

Bỏ intro/aside/notice/notes/state-meta và mô tả lặp trên đầu form; không
khung trống. Giữ hero, hai ô nguồn/ngôn ngữ, form, lịch sử, làm mới,
phân trang và tải kết quả; chuyển liên kết kho tệp vào chân form.
Mọi ngôn ngữ giao diện phải đầy đủ, tên/giá trị khách không dịch.
Đọc chữ không dịch nội dung. Word chỉ tái tạo chữ, không giữ hình/bảng/
phông/bố cục; PDF giữ giới hạn 20 MB/5 trang.

## Thứ tự

| Spec | Kết quả | Bằng chứng | Phụ thuộc |
|---|---|---|---|
| OCR-00 | PR776 đã giao, local/GitHub/VPS đúng bản | Receipt/HEAD/tree | Không |
| OCR-01 | Tái hiện chữ còn sai | Whole physical BASE + native72views | 00 |
| OCR-02F | Trường nguồn/ngôn ngữ đủ locale | 3factory/14sharedkeys, public codes giữ | 01 |
| OCR-02A | Trang đọc ảnh rõ, gọn | Renderer/meta/7keys | 01 |
| OCR-02B | Trang đọc PDF rõ, gọn | Renderer/meta/7keys | 01 |
| OCR-02C | PDF quét sang Word rõ giới hạn | Renderer/meta/8keys | 01 |
| OCR-03 | Ghép chính xác bốn worker | Schema/literal/source151 | 02F/A/B/C |
| OCR-04 | Đúng hành vi, không hồi quy | Physical/source/shell/native và comparator | 03 |
| OCR-05 | Tài liệu/Tester/review đủ | Case/manifest/prepush | 04 |
| OCR-06 | Một PR và giao ngay | Exact HEAD CI/merge/deploy/VPS/assets/receipt | 05 |

Bốn phiên Antigravity độc lập chỉ trả JSON, không ghi shared source.
Root nghiệm thu chung và áp dụng tuần tự; không takeover trước hai lỗi
thật cùng đoạn. Lỗi đặc tả hoặc QA của Root không tính worker.

## Không nhận nhầm trạng thái khả dụng

Cờ/form không chứng minh Tesseract, gói ngôn ngữ hoặc kết quả TXT/DOCX.
Đọc trạng thái UI không gọi OCR. Cờ QA chỉ trong child với dữ liệu tạm.
PDF quét sang Word cần cả OCR-to-Word, PDF-OCR và PDF-to-Word; điều kiện
này có trong API và handler gốc, không bị nới. Sửa đặc tả child trước chạy
để giữ đúng ba phụ thuộc; không chỉnh cấu hình máy hay production.

Mọi UNKNOWN màu/focus/thiết bị/Safari/production có đăng nhập và đầu ra
cuối giữ mở nếu chưa có bằng chứng trực tiếp. Goal ACTIVE/incomplete;
motion M-FINAL-01..06 cuối.
