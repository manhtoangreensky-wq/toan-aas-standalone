# Phiên MEMBERSHIP-PLAIN-LANGUAGE-20261111

BASE: `e2afca85d96ed6a19c941924e5344ea40869cfac`. Tracker: Issue #689.

|Mục|Điều kiện|Bằng chứng hiện tại|
|---|---|---|
|Chữ cố định|14 khóa và bốn đoạn hộp dẫn đúng Việt/Anh/Trung|12 ca renderer đạt|
|Dữ liệu|Giữ tên gói/trạng thái/ghi chú kể cả chữ kỹ thuật, số dư 0 và giá thật|So toàn bộ dữ liệu, controls và HTML ngoài vùng chữ được duyệt|
|Ghi chú tĩnh|Bỏ đúng hai đoạn triển khai, không bỏ trạng thái thật/nguyên tắc/nút|12 ca renderer đạt|
|Màu|Chữ/nút >=4,5:1 ở sáng/tối và thường/rê chuột/focus|12 giao diện, 240 mẫu, min 5,216649621048673:1, 0 không xác định|
|Hồi quy|Không đổi nguồn/luồng đã khóa|556 Node +67 ca chịu ảnh hưởng kiểm lại, 5 Python/metadata đạt; nguồn bảo vệ không đổi|
|Chỉ đọc|Không ghi kế hoạch/ví/dữ liệu khách; rời trang dọn layout|12 lượt xem/3 lượt rời trang, 0 lỗi console/trang/tràn ngang, DB QA giữ nguyên và 0 tiến trình còn lại|
|Phát hành|CI đúng HEAD, merge, deploy, runtime/assets|Chưa thực hiện|

Các lượt QA chỉ dùng tài khoản và DB giả trong localhost, không ghi dữ liệu
sản phẩm, ví hoặc production; không gọi dịch vụ tạo nội dung có phí.
