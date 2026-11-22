# Phiên Tester — IMAGE-STUDIO-PRESENTATION-20261122

- Sản phẩm/kho: standalone WebApp, Issue689.
- BASE: `07a89b79c442981ecb7433b607c981740c95c774`.
- Nhánh: `codex/image-studio-presentation-20261122`; HEAD theo PR khi công bố.
- Trạng thái: local checked; hồi quy đã đối chiếu lỗi và chạy lại nhóm ảnh hưởng;
  phát hành và signed production UI chờ.
- Case nguồn: ISP-COPY, ISP-BOUNDARY, ISP-LAYOUT, ISP-CONTRAST,
  ISP-PRESERVE, ISP-SOURCE, ISP-DELIVERY trong `DANH-SACH-CASE.md`.

Kiểm 19 câu ở Việt/Anh/Trung, hai màn tạo/chi tiết của Thiết kế ảnh và Trung
tâm ảnh,375/1440px,sáng/tối. Không còn khung giải thích lặp hoặc khung rỗng;
form tạo dùng đủ chiều ngang, tên/nội dung khách giữ nguyên. Nhập tên và
chọn tỷ lệ không đổi thao tác/giá trị. Không gửi biểu mẫu vào production.

Số đếm màn chi tiết sáng phải rõ; hình học/nội dung và màu các theme còn
lại giữ nguyên. Đối chiếu DOM không che chữ/thuộc tính; BASE dùng cùng bộ
dịch đã được kiểm riêng57giá trị, chỉ bỏ đúng khung và textnode trống.

Đã đo: năm ca trước sửa RED;23ca mục tiêu sau sửa PASS,48màn/8ảnh/57giá trị
dịch/0overflow/0pageerror/0request,147PythonPASS.
Hồi quy166tệp/5146ca:5145PASS/1FAIL lịch sử; một reader dùng inverse hữu hạn
đã có thay vì đọc CSS mới trực tiếp vào golden cũ. Giữ nguyên assertions;
chạy lại đúng tệp ảnh hưởng4/4PASS, không có lỗi chưa giải quyết. Không gọi
đây là một lượt fullPASS mới. CI/deploy chưa nhận từ các con số này.
Chỉ dùng dữ liệu giả, không provider, ví, API thật hoặc thông tin đăng nhập.

Ghi bằng chứng phát hành vào cùng Issue689; không tạo thẻ/PR trống.
Signed production UI và toàn goal còn mở; motion cuối.
