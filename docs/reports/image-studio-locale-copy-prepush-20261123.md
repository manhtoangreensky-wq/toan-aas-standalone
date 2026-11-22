# Trước phát hành — chữ thiết kế ảnh

BASE runtime `d165bad407a51a8cf6339b019a073f8a1a1eb37a`.
Ứng viên đổi 32 record trong ba UI files để chữ đầu trang, thư viện và
chín trường phương án đúng ngôn ngữ; làm tiêu đề thẻ sáng đọc rõ.
Nội dung khách, hành động, options, giới hạn, quyền và dữ liệu giữ nguyên.

Đã cập nhật vận hành, đối chiếu chức năng, spec và phiên Tester ISLC.
16 Node mục tiêu, 16 Node ở bốn tệp ngoài nhóm chung, 24 màn Chrome,
32 mẫu màu, hai ca nhập dài/lựa chọn đạt. Sáu ca header/sidebar kiểm riêng
trùng nhóm chung, không cộng lặp. Hồi quy 171 tệp/5.202 ca đạt, Python
lịch sử/vault/điều hướng 155/155, màu 90/90. Review tìm một câu hứa giữ lựa
chọn chưa lưu quá rộng; đã nhận một hàng sửa đúng từ Antigravity. Ba ca
RED tái hiện, 48 ca ảnh hưởng sau sửa đạt và 30 trạng thái thư viện vật lý
đạt. Không đổi logic dữ liệu; không có phát hiện chặn còn mở trong batch.
Provenance sẽ được xác minh trên commit trước push.

Không đổi backend, Bot, route-engine, provider, ví, PayOS,
ENV, dữ liệu production hoặc motion. Signed production UI chưa quan sát.
