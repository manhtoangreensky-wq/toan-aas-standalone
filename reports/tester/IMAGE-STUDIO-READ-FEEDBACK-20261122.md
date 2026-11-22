# Kết quả kiểm tra cục bộ — phản hồi đọc thiết kế ảnh

BASE `ef3643d84c269aa2a07e411debe400a44f72d8e6`.
Sáu thay đổi ứng dụng: một helper, bốn nhánh hành động, một bộ thông báo
Việt/Anh/Trung. Bộ kiểm tra đối chiếu đúng sáu thay đổi và giữ nguyên phần
ngoài phạm vi.

Mã vật lý: 75 tình huống trạng thái; 14 kiểm tra guard; một tình huống hai
lượt đọc chồng nhau. Toàn bộ bundle và GET giả: 48 trường hợp, không mạng
thật. Node mục tiêu 24/24, Python 237/237. Hồi quy 168 tệp đạt
5.161/5.161, không bỏ qua; bốn tệp không thuộc lượt đó đạt 16/16 riêng.
Không cộng lại các ca trùng giữa các lượt. Chưa xác nhận CI hoặc giao
diện production đã đăng nhập trong báo cáo này.

Hai tranh chấp khác và trạng thái chờ chi tiết vẫn theo dõi riêng; không
khẳng định chúng được sửa trong đợt này. Không gọi provider hoặc thay đổi ví.
