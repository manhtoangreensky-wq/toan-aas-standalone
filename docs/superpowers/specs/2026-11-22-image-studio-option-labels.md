# Chữ lựa chọn tỷ lệ và định dạng ảnh

BASE `f4c5b6a9821cf957ce107778fd9abd884075fd50`.

Tám lựa chọn tỷ lệ dùng đúng VI/EN/ZH. Giá trị `1:1`, `4:5`, `3:4`,
`16:9`, `9:16`, `3:2`, `2:3`, `custom`, thứ tự và mặc định không đổi.
Khi thiếu bộ dịch, nhãn dự phòng là tiếng Việt.

Ba định dạng hiển thị PNG/JPG/WebP; bỏ hậu tố mô tả kỹ thuật. Giá trị
png/jpg/webp và cách nhận chữ hoa/thường giữ nguyên. Nhãn định dạng
không xác định theo ngôn ngữ giao diện, có câu Việt dự phòng.

Chỉ đổi chữ cố định trên hai biểu mẫu tạo/chỉnh sửa. Không đổi bộ kiểm
tra trong integration.js, giới hạn, quyền, nội dung khách, backend hay
khả năng tạo ảnh. Kiểm tra mã thực và renderer ở ba ngôn ngữ, điện
thoại/máy tính; CI, phát hành và production sau đăng nhập là cổng riêng.
