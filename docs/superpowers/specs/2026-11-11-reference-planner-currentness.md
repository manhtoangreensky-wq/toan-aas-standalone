# Nội dung đang nhập và khôi phục kế hoạch

Mục tiêu: khi người dùng đổi trang hoặc đổi lựa chọn, phản hồi cũ không được
thay nội dung mới. Nếu tạo lại thất bại, giữ nội dung đã có để tiếp tục. Khi
đang lưu, không tạo thêm lần lưu khác. Nếu mất phản hồi sau lưu, thao tác thử
lại phải trả về cùng kế hoạch thay vì tạo bản ghi trùng.

Phạm vi: giao diện hai công cụ kế hoạch; không đổi đăng nhập, quyền, thanh toán,
dữ liệu khách hoặc bộ xử lý tạo nội dung. Chỉ phát hành sau khi kiểm tra phù hợp
đạt và đối chiếu bản đang chạy. Các phần đã phát hành ở PR #719–#721 giữ nguyên.

- [x] Phản hồi cũ không thay nội dung đang nhập.
- [x] Tạo lại thất bại giữ kết quả đã có và cách khôi phục.
- [x] Lưu đang chờ không tạo thêm yêu cầu khác.
- [x] Thử lại sau mất phản hồi không tạo kế hoạch trùng.
- [ ] Kiểm tra, phát hành và đối chiếu bản chạy thực tế.

Theo dõi tại Issue #689. Các cổng toàn ứng dụng, bàn phím, đăng nhập, thiết bị
và chuyển động vẫn theo thứ tự checklist tổng; tài liệu này không đóng goal.
