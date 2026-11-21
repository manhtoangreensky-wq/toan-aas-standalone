# Trước phát hành — cảnh báo trường bắt buộc

BASE `a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc`; nhánh riêng từ đúng
phiên bản đã triển khai. Trạng thái: kiểm tra cục bộ, chờ CI.

Antigravity R1 đề xuất hai thay đổi giao diện và được đối chiếu đúng
nguồn trước khi áp dụng. Cảnh báo ứng dụng có đủ ba ngôn ngữ; kiểm
tra gốc, focus, ngoại lệ, quyền, nội dung khách và luồng máy chủ giữ
nguyên. Tài liệu vận hành và đối chiếu chức năng đã cập nhật; năm case
trong `KIEM-THU/DANH-SACH-CASE.md` có phiên kiểm tra riêng.

Kiểm tra tại máy: 4/4 case mục tiêu, Chrome 6/6 màn và sáu case đối
chứng, 93 Node vùng chung, 257 Node âm thanh, 129+2+16 Python;
4.796 case của 152 tệp khác đạt trong một lượt. Không cộng các nhóm
thành một số duy nhất khi chưa đối chiếu trùng.

Chỉ thêm hai lệnh chạy kiểm tra vào quality workflow; không đổi workflow
triển khai hoặc quyền. CI đúng phiên bản, merge, triển khai, runtime và
giao diện production sau đăng nhập phải có bằng chứng riêng. Thông báo
do trình duyệt tự tạo và toàn bộ ngôn ngữ của trang vẫn là việc mở.
