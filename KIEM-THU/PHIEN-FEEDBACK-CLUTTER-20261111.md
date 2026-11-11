# Phiên kiểm tra FEEDBACK-CLUTTER-20261111

Nguồn: `8371c43d147b0074c71c00dc4d3f7f9927894d5c`. Issue #689.

|Mục|Điều kiện cần đạt|Bằng chứng hiện có|
|---|---|---|
|Thông báo|Cùng hiện với nút, không che nội dung hoặc vùng điều hướng|24 trạng thái hiển thị đang có thông báo đạt|
|Vòng đời|Một vùng thông báo; observer được dọn; không mất focus/nội dung|10 ca chạy helper thật đạt|
|Hội viên|Chỉ bỏ khối giải thích tĩnh; giữ dữ liệu thật kể cả số dư 0|12 ca renderer thật đạt, đối chiếu toàn bộ phần HTML còn lại|
|Landing|Câu giới thiệu đúng ngôn ngữ; mọi khóa/chức năng khác giữ nguyên|3 ca renderer thật đạt|
|Hồi quy|Giữ thao tác và trạng thái cũ|94 ca Node và 12 ca Python đạt|
|Hiển thị hai trang dọn chữ|Việt/Anh/Trung, 390/1440, không lỗi trang hoặc mất nút|12 lượt xem đạt; 3 lượt rời trang giữ nguyên vùng thông báo; không ghi kế hoạch|
|Giao hàng|Kiểm tra đúng HEAD, merge đúng bản, deploy và đối chiếu runtime/asset|Chưa thực hiện|

Không xác nhận đầu ra provider, thanh toán, thiết bị thật hoặc toàn goal.
Không thay thông báo thật bằng dữ liệu giả hay trì hoãn để che lỗi.
