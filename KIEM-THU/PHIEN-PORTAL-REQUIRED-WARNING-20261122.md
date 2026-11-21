# Phiên kiểm tra cảnh báo trường bắt buộc

Nguồn case: `DANH-SACH-CASE.md`, nhóm PORTAL-REQUIRED-WARNING-20261122.
BASE `a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc`; dùng dữ liệu giả,
không gọi nhà cung cấp hoặc ví.

| Case | Bằng chứng cục bộ |
| --- | --- |
| PRW-LOCALE | Bốn kiểm tra mã vật lý đạt, gồm ba ngôn ngữ và thiếu bộ dịch |
| PRW-FOCUS | Chrome cô lập 6/6 trường hợp ba ngôn ngữ × điện thoại/máy tính, cảnh báo nằm trong vùng nhìn thấy |
| PRW-PRESERVE | Sáu trường hợp mô phỏng giữ thao tác hợp lệ và nút lọc ngoại lệ |
| PRW-SOURCE | Đối chiếu toàn hai tệp với BASE cộng đúng thay đổi; kiểm tra lịch sử từ chối bản bị sửa/nhân đôi |
| PRW-DELIVERY | CI, merge, VPS và giao diện production sau đăng nhập là cổng riêng, chưa chứng nhận |

Hồi quy: 93 Node liên quan, 257 Node âm thanh, 129 Python lịch sử,
2 Python đối chiếu mới và 16 Python bộ dịch đạt; lượt riêng 152 tệp
đạt 4.796 trường hợp, không lỗi hoặc bỏ qua. Các nhóm báo riêng,
không cộng trùng. Không kiểm tra ngôn ngữ trình duyệt trên mọi thiết bị.
