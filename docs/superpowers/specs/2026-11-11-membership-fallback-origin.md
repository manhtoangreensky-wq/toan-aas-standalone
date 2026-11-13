# Hội viên: phân biệt nội dung thật và giá trị thay thế

Tiếp sau PR #724 đã triển khai. Chỉ phần trình bày của formatter riêng Hội viên
và đoạn ghi chú thẻ; không sửa bộ chuẩn hóa dùng chung, giá, quyền hoặc API.

- [x] Xác định nhãn mặc định luôn tiếng Việt và ghi chú tự chèn khi nguồn thiếu.
- [x] Kiểm tra trước sửa 60 trường hợp ba ngôn ngữ: thiếu/rỗng/không hợp lệ,
  trùng câu mặc định, nội dung kỹ thuật thật, ghi chú cũ, thứ tự/duplicate/giới hạn.
- [x] Nhãn mặc định theo ngôn ngữ; dùng khóa dịch hiện có, không thêm khóa.
- [x] Nguồn không có ghi chú hợp lệ: không tạo đoạn giả hoặc paragraph rỗng.
- [x] Nguồn có ghi chú: giữ nguyên nội dung đã chuẩn hóa/escape, kể cả trùng câu mặc định.
- [x] Dữ liệu/nút/markup ngoài phạm vi giữ nguyên; 240 ca hồi quy đạt.
- [x] 12 giao diện component có nguồn tổng hợp và 12 lượt xem trang đăng nhập QA đạt.
- [ ] CI đúng HEAD, merge, deploy, runtime/assets và receipt trong Issue #689.

Không dùng so sánh một câu hiển thị để suy luận nguồn dữ liệu. Không khôi phục
các trường raw bị bộ chuẩn hóa bỏ, không thay tiền hoặc lọc/xóa nội dung khách.
