# Phiên kiểm tra — nội dung đang nhập và khôi phục kế hoạch

Phiên: REFERENCE-CURRENTNESS-20261111. Theo dõi: Issue689.
Trạng thái: đã đạt kiểm tra trong phạm vi; chờ cổng phát hành và đối chiếu bản chạy.

|Mục|Điều kiện cần đạt|Trạng thái|
|---|---|---|
|Nội dung hiện hành|Phản hồi cũ không thay nội dung mới khi đổi trang hoặc lựa chọn|Đạt trong phạm vi này|
|Tạo lại thất bại|Giữ kết quả trước và nội dung đang nhập để tiếp tục|Đạt trong phạm vi này|
|Lưu đang chờ|Không tạo thêm một lần lưu khác|Đạt trong phạm vi này|
|Khôi phục sau mất phản hồi|Thử lại đúng lần lưu, trả về cùng kế hoạch|Đạt trong phạm vi này|
|Luồng từ ảnh|Sửa, tạo lại, chờ lưu, thử lại không trùng đã kiểm tra riêng|Đạt trong phạm vi này|
|Phát hành|Kiểm tra đạt, gộp đúng bản, triển khai và đối chiếu|Chưa thực hiện|

Không dùng việc đạt của một công cụ để đóng công cụ khác hoặc toàn goal.
Không thay đổi dữ liệu khách, quyền, ví hoặc gọi dịch vụ tạo nội dung có phí.
Phần kiểm tra sau đăng nhập trên production và thiết bị thật vẫn có cổng riêng.
