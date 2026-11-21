# Kiểm tra cảnh báo trường bắt buộc

BASE: `a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc`.
Trạng thái: kiểm tra cục bộ; CI, triển khai và nghiệm thu production
là các bước riêng.

Trước sửa, kiểm tra mã vật lý cho thấy tiếng Anh và tiếng Trung nhận
câu tiếng Việt; hai trường hợp còn lại đạt. Sau sửa, 4/4 kiểm tra mã
vật lý đạt. Đề xuất Antigravity R1 được đối chiếu với đúng hai thay
đổi cho phép trước khi áp dụng.

Chrome cô lập: biểu mẫu thiết kế ảnh do mã hiện tại tạo ra đạt 6/6
trường hợp (ba ngôn ngữ × hai kích thước), cảnh báo nằm trong vùng
nhìn thấy, chọn đúng trường chưa hợp lệ và không gửi thao tác; không
có lỗi trang hoặc kết nối mạng. Sáu trường hợp biểu mẫu mô phỏng khác
xác nhận thao tác hợp lệ và nút lọc ngoại lệ vẫn đi tiếp.

93 kiểm tra Node của cảnh báo và vùng chọn dùng chung, 257 kiểm tra
Node vùng âm thanh, 129 kiểm tra lịch sử Python, 2 kiểm tra bảo vệ
đối chiếu Python và 16 kiểm tra bộ dịch Python đạt tại máy. Một lượt
hồi quy riêng trên 152 tệp còn lại có 4.796 trường hợp đạt, không lỗi
và không bỏ qua. Các nhóm được báo riêng, không cộng gộp để tránh tính
trùng.

Không gọi nhà cung cấp hay thay đổi ví. Không chứng nhận ngôn ngữ của
thông báo do trình duyệt tự tạo, toàn bộ trang hoặc kết quả sau đăng
nhập production.
