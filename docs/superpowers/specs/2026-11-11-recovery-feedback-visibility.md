# Thông báo không che thao tác khôi phục

Mục tiêu: người dùng nhìn thấy và chạm được nút thử lại khi cần khôi phục lần
lưu chưa được xác nhận, trong khi thông báo kết quả/lỗi vẫn đọc được.

Trước khi sửa, đo trạng thái thực trên giao diện điện thoại: vị trí nút, thông
báo và thanh điều hướng; phân biệt bị che với trường hợp cần cuộn để xem nút.
Không kết luận chỉ từ ảnh chụp và không ẩn lỗi thật để làm giao diện trông gọn.

- [x] Đo đúng trạng thái khôi phục trước khi cuộn hoặc đổi vị trí: xác nhận
  thông báo có thể che chữ trên nút dù thao tác chạm vẫn đi qua.
- [x] Nếu có che khuất, sửa đúng phần trình bày và giao Antigravity trước.
  Hai lượt chưa đạt bị loại; sau đó sửa trực tiếp đúng phạm vi bố cục.
- [x] Giữ nguyên thao tác lưu/thử lại và nội dung đang nhập đã đạt ở #722.
- [x] Kiểm tra thao tác chạm, bàn phím, ngôn ngữ và kích thước liên quan:
  24 trạng thái có thông báo, 10 ca vòng đời và 3 lượt rời trang đạt.
- [ ] Chỉ phát hành sau khi kiểm tra đạt và đối chiếu bản chạy thực tế.

Không thay đổi đăng nhập, quyền, thanh toán, bộ xử lý tạo nội dung hoặc dữ liệu
khách. Đây là một mục trong checklist tổng, không đóng toàn bộ WebApp hay motion.
