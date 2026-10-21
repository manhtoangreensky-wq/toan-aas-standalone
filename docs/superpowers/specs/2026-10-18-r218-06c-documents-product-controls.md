# R218-06C — Documents/PDF control-level parity

## Mục tiêu

Khóa lớp UI/UX của nhóm Tài liệu/PDF theo đúng flow đã có trong Bot nhưng giữ
Web-native: chọn nguồn private → sắp xếp hoặc cấu hình → xác nhận → theo dõi
trạng thái → chỉ tải khi máy chủ xác minh artifact và quyền sở hữu.

## Phạm vi đã kiểm tra

- Một bảng `/documents` và `/documents/pdf`, không tạo thêm bảng trùng.
- Tách PDF: một nguồn, một trang hoặc một dải liên tiếp.
- Gộp PDF: tối đa tám ô theo thứ tự, tối thiểu hai nguồn khác nhau.
- Tối ưu PDF: lựa chọn workflow lossless; file gốc không bị thay đổi.
- Ảnh sang PDF: tối đa tám ô theo thứ tự trang.
- PDF sang ảnh, PDF có chữ sang Word, OCR ảnh, OCR PDF và OCR PDF sang Word.
- Bảng lịch sử owner-scoped, empty/loading/guarded/failed/completed, nút làm mới,
  xác nhận trước thao tác và nút tải chỉ xuất hiện khi `completed + download_ready`.

## Hợp đồng giao diện

Mọi form dùng mã tài sản từ Asset Vault, không nhận URL/path/bytes từ trình duyệt.
Các lựa chọn chưa có capability vẫn hiển thị trạng thái có điều kiện thay vì giả
đã sẵn sàng. Thứ tự DOM là nguồn → cấu hình → review/xác nhận → kết quả; mobile
xếp một cột và giữ nút tối thiểu 44px.

## Bằng chứng control-level

`tests/documents-product-controls.test.mjs` khóa route, form, page range, tám ô
thứ tự, nhóm workflow, confirm, kết quả và điều kiện tải. Test không gọi API ngoài,
không tạo file, không sửa ví/Xu và không mở provider.

## Chưa đóng

Đây chưa phải runtime parity: capability máy chủ, upload/preview bytes thật,
quote/job/output/delivery, browser authenticated/AX và LIVE vẫn để `[~]` trong
completion ledger. Không được suy diễn từ route, HTTP 200 hoặc test tĩnh.
