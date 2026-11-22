# Phiên kiểm tra — phản hồi đọc thiết kế ảnh

BASE `ef3643d84c269aa2a07e411debe400a44f72d8e6`, Issue #689.
Các case ISRF-OUTCOME, ISRF-CURRENT, ISRF-VALIDATION, ISRF-LOCALE và
ISRF-DELIVERY được ghi trong `DANH-SACH-CASE.md`. Chỉ dùng dữ liệu giả.

- Kiểm thành công, danh sách rỗng, tải lỗi, đổi trang, đăng xuất và lượt
  mới ở Việt/Anh/Trung. Không phát thông báo thành công của lượt đã cũ.
- Khi bộ lọc đã lưu không hợp lệ trong lúc lượt cũ đang chờ, giữ lỗi cụ thể;
  lượt cũ không được ghi đè hoặc báo thành công.
- Thực thi toàn bộ hai bundle với GET giả: 48 trường hợp đạt; không mạng
  thật. Node mục tiêu 24/24; Python hồi quy 237/237.
- Hồi quy 168 tệp: 5.161 ca đạt, không lỗi hoặc bỏ qua. Bốn tệp không
  thuộc lượt đó được chạy riêng: 16/16 đạt. Hai ca guard bổ sung được
  kiểm trong lượt Node mục tiêu, không cộng vào lượt hồi quy đã chạy.
- CI, merge, deploy và giao diện production sau đăng nhập là các cổng
  riêng, chưa được chứng nhận trong tài liệu này.

Không xác nhận đầu ra nhà cung cấp, thanh toán, toàn bộ ngôn ngữ, motion
hoặc toàn goal từ các kiểm tra trên.
