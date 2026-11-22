# Phiên kiểm tra — chờ và giữ nội dung chi tiết ảnh

BASE `e177ce5f5791fd22e517d95706331051223e0ccb`, Issue #689.
Nguồn case duy nhất là `DANH-SACH-CASE.md`, nhóm ISDL.

Sử dụng dữ liệu giả. Kiểm VI/EN/ZH ở hai nhóm đường dẫn chi tiết; màn chờ,
thất bại và thiếu quyền ở 375/1440. Gõ các giá trị khác nhau vào sửa bảng,
tạo phương án và sửa hai phương án; cập nhật cùng phiên bản phải giữ đúng
từng giá trị. Đổi phiên/route/revision phải ngăn khôi phục nhầm. Lựa chọn
đã xóa/vô hiệu và biểu mẫu trùng mã phải không nhận nội dung của mục khác.

Đã kiểm trên Chrome thực: 12 ca thông thường + 2 ca trùng mã + 6 ca lựa
chọn; 36 màn trạng thái tĩnh, không lỗi trang hoặc mạng; màu sáng 12,352:1
và tối 13,903:1. Node mục tiêu 40/40, nhóm riêng 16/16, Python màu 90/90.
Hồi quy 170 tệp/5.186 ca đạt, 0 lỗi/0 bỏ qua. Hai ca Chrome bổ sung giữ
toàn bộ trường dài/lựa chọn đạt; Python lịch sử 136/136, shell 4/4.

Chưa nghiệm thu việc giữ bản nháp qua lỗi đọc, rời trang hoặc đổi phiên bản.
CI/merge/deploy/runtime và tương tác production sau đăng nhập là các cổng
riêng. Không gửi sản phẩm, thanh toán hoặc gọi provider.
