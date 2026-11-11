# Nội dung đang nhập và khôi phục kế hoạch

Trạng thái: bản sửa ứng viên đã qua kiểm tra trong phạm vi này; phát hành và
đối chiếu bản chạy thực tế có receipt riêng trên Issue689.

## Phạm vi

Giữ đúng nội dung người dùng đang nhập khi đổi lựa chọn hoặc khi phản hồi đến
muộn. Nếu tạo lại thất bại, giữ nội dung đã có và cách tiếp tục. Khi đang lưu,
không gửi thêm lần lưu khác; sau mất phản hồi, chỉ thử lại đúng lần lưu đó để
tránh kế hoạch trùng.

Không thay đổi đăng nhập, quyền, thanh toán, dữ liệu khách hoặc bộ xử lý tạo
nội dung. Các phần đã phát hành ở PR719–721 được giữ nguyên.

## Bằng chứng đã có và phần còn mở

- Công cụ lập kế hoạch từ ảnh đã qua kiểm tra riêng bằng dữ liệu cô lập ở
  ba ngôn ngữ: sửa lựa chọn, tạo lại, chờ lưu và thử lại sau mất phản hồi.
  Lần thử lại trả về cùng kế hoạch, không tạo thêm bản ghi; dữ liệu gốc giữ nguyên.
- Công cụ lập kế hoạch từ tham chiếu đã qua các tình huống phản hồi cũ, giữ
  nội dung sau tạo lại thất bại, chờ lưu và thử lại không trùng ở ba ngôn ngữ.
  Hai lượt sửa đầu không đạt; phần sai được sửa trực tiếp đúng phạm vi sau đó.
- Chỉ phát hành khi các tiêu chí của đúng luồng đạt kiểm tra và bản chạy thực
  tế được đối chiếu với bản đã gộp.

## Kiểm tra trước phát hành

Các kiểm tra tự động liên quan đã đạt. Tình huống bổ sung bảo vệ việc kết thúc
một yêu cầu cũ được đối chiếu với hành vi trước sửa; chỉ kiểm lại phần ảnh hưởng.
Các luồng giao diện thực dùng dữ liệu cô lập, có lưu và đọc lại kế hoạch thật
trong môi trường đó; lần thử lại sau mất phản hồi không tạo thêm bản ghi.
Dữ liệu gốc, các luồng đăng nhập, quyền, thanh toán và phần ảnh đã đạt giữ nguyên.
Không gọi bộ xử lý tạo nội dung có phí hoặc thay đổi dữ liệu production.

Theo dõi duy nhất tại Issue689. Mục này không đóng toàn ứng dụng; ma trận
bàn phím, khả năng truy cập, đăng nhập, thiết bị và chuyển động vẫn theo thứ tự
checklist tổng. Chi tiết nội bộ được giữ tại máy, không đưa vào báo cáo công khai.
