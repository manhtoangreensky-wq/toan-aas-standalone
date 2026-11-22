# Trước phát hành — chờ và bản đang sửa của chi tiết ảnh

BASE `e177ce5f5791fd22e517d95706331051223e0ccb`; Issue #689.
Khi mở bảng khác, giao diện nay có trạng thái chờ rõ ràng. Khi vẽ lại cùng
bảng và cùng phiên bản, các biểu mẫu giữ riêng nội dung đang gõ. Phiên,
revision, quyền, nhận dạng trùng và lựa chọn vô hiệu được kiểm tra trước khi
khôi phục. Chỉ ba tệp ứng dụng thay đổi; không có backend, ENV, provider,
ví, Bot, PayOS hoặc dữ liệu production.

Đã cập nhật vận hành, đối chiếu chức năng gốc, case và phiên Tester ISDL.
Node mục tiêu 40, nhóm riêng 16, Python màu 90 đạt; Chrome 20 tình huống và
36 màn tĩnh đạt; rà soát độc lập không có lỗi chặn mới. Hồi quy cuối
170 tệp/5.186 ca đạt, 0 lỗi/0 bỏ qua; Python bổ sung 136+4 đạt.
Dấu vết nguồn cần chốt trước push. Giao diện sau đăng nhập production chưa được
quan sát; các trường hợp bản nháp qua lỗi đọc/đổi revision/rời trang còn mở.
