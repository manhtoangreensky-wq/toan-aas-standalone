# Trước phát hành — phản hồi đọc thiết kế ảnh

BASE `ef3643d84c269aa2a07e411debe400a44f72d8e6`. Ứng viên chỉ sửa
phản hồi đọc của bốn hành động và thêm năm thông báo ba ngôn ngữ; không
đổi hàm tải, API, quyền, backend, ví hoặc nhà cung cấp. Đã cập nhật đối
chiếu hành vi gốc, tài liệu vận hành và phiên kiểm tra trong kho.

Các bằng chứng cục bộ gồm 75 tình huống nguồn vật lý, 14 guard, một kiểm
tra chồng lượt, 48 trường hợp toàn bundle với GET giả, Node 24/24 và
Python 237/237. Hồi quy 168 tệp 5.161/5.161, bốn tệp còn lại 16/16.
Các cổng phát hành chưa được kết luận tại thời điểm viết báo cáo. Giao
diện production sau đăng nhập chưa được kiểm tra.
