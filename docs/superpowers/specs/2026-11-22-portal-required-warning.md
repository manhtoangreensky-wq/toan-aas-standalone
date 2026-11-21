# Thông báo trường bắt buộc theo ngôn ngữ

BASE: `a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc`.

Khi một biểu mẫu đi vào bộ xử lý chung và chưa hợp lệ, tiếp tục dùng
kiểm tra gốc, đưa con trỏ tới trường chưa hợp lệ đầu tiên và không gửi
thao tác. Thông báo của ứng dụng phải theo ngôn ngữ giao diện:

| Ngôn ngữ | Thông báo |
| --- | --- |
| Việt | Hãy hoàn tất các trường bắt buộc trước khi tiếp tục. |
| Anh | Complete the required fields before continuing. |
| Trung | 请先填写必填项，然后继续。 |

Khi bộ dịch không sẵn sàng, giữ câu tiếng Việt dự phòng. Không đổi các
ngoại lệ của biểu mẫu, hành vi nút lọc, dữ liệu, quyền, máy chủ, ví
hay nhà cung cấp.

Phạm vi này chỉ xử lý thông báo của ứng dụng khi bộ xử lý được gọi.
Một số biểu mẫu có thể bị trình duyệt tự chặn trước đó; ngôn ngữ thông
báo do trình duyệt tạo ra là vấn đề riêng và chưa được chứng nhận bởi
thay đổi này.

Kiểm tra: mã vật lý và ngôn ngữ dự phòng; biểu mẫu thiết kế ảnh do mã
hiện tại dựng ở ba ngôn ngữ, kích thước điện thoại/máy tính; trường
được chọn, thao tác không hợp lệ bị chặn, thao tác hợp lệ và nút lọc
được giữ. Kiểm tra trên dữ liệu giả không thay thế nghiệm thu sau đăng
nhập ở production.
