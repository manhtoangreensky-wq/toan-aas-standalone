# Cổng trước phát hành — FEEDBACK-CLUTTER-20261111

BASE: `8371c43d147b0074c71c00dc4d3f7f9927894d5c`.
Tracker: Issue #689, đúng kho `manhtoangreensky-wq/toan-aas-standalone`.

## Review và vận hành

Diff ứng dụng giới hạn ở helper/hook/CSS riêng cho thông báo trang tham chiếu,
hai phép xóa khối tĩnh Hội viên và ba giá trị giới thiệu landing. Không sửa
toast producers, timers, nội dung phản hồi thật, integration/API/auth, backend,
schema, ví/thanh toán, provider, Bot hoặc motion. Các tệp bảo vệ không có diff.

Tài liệu đã cập nhật:

- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`: hành vi hiện tại và giới hạn kiểm tra.
- `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`: đối chiếu hành vi cũ với mới.
- `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`: một ledger
  duy nhất, giữ các cổng rộng hơn và motion mở.

## Đối chiếu chức năng ban đầu

Tài liệu chức năng hiện có được nối tiếp tại tài liệu đối chiếu nói trên,
không dựng danh sách chức năng mới. Thao tác, quyền lợi thật, route và các
bước quy trình đều giữ; không thêm quyền, giá, kết quả giả hoặc lời hứa mới.

## Chỗ kiểm tra độc lập

TESTER_PROJECT_ID=FEEDBACK-CLUTTER-20261111.
TESTER_PROJECT_STATUS=READY.
Nguồn ca kiểm tra: `KIEM-THU/DANH-SACH-CASE.md`, FC-RECOVERY đến FC-PROTECTED.
Phiên: `KIEM-THU/PHIEN-FEEDBACK-CLUTTER-20261111.md`.
Các bài kiểm tra và hồ sơ nghiệm thu tách khỏi đề xuất của bên triển khai.

Đã chạy: 94 ca Node, 12 ca Python, 24 trạng thái thông báo thật và 12 lượt xem
chỉ đọc đạt; 3 lượt rời trang giữ đúng node. Không có lời gọi provider, thay đổi
ví hoặc ghi production. Phần xác minh sau merge/deploy theo receipt trên Issue689,
không suy từ các kết quả local này. Máy chủ/trình duyệt QA sở hữu đã được dọn.

PUSH_GATE=READY cho đúng phạm vi này. Merge/triển khai chỉ sau CI đúng HEAD đạt;
không coi merge/deploy là bằng chứng LIVE của phiên khách hoặc đầu ra provider.

Siêu dữ liệu nguồn ca kiểm tra được đo theo UTF-8/LF, giữ nguyên các trường lịch
sử 48 ca/P0/remote và an toàn. Không dùng số ca lịch sử làm số ca hiện tại.
