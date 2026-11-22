# Kiểm tra nhãn biểu mẫu thiết kế ảnh

BASE `05b7ba761bd35cf4da498443db9046ed59429d90`.
Trạng thái: kiểm tra cục bộ, chờ CI và phát hành.

Trước sửa, ba trường hợp ngôn ngữ chưa đạt; ba đối chứng về dữ liệu,
giới hạn và lựa chọn đạt. Antigravity R1 trả đúng hai record; nguồn
hai tệp sau áp dụng bằng BASE cộng đúng hai record đó.

Nhóm mục tiêu gồm sáu kiểm tra nhãn/dữ liệu và năm kiểm tra hiện có
đều đạt (11/11). Chrome cô lập có 12 trường hợp tạo/chỉnh sửa ×
VI/EN/ZH × điện thoại/máy tính: nhãn đúng, dữ liệu chỉnh sửa giữ,
không tràn ngang, không lỗi trang hoặc yêu cầu mạng.

Sáu đối chiếu renderer với BASE giữ nguyên toàn phần ngoài form và
cấu trúc/dữ liệu trong form ngoài đúng chữ cho phép. Đối chứng thay
giới hạn trường được phát hiện. 147 kiểm tra Python đạt.

Hồi quy rộng 165 tệp có 5.139 dòng kết quả, trong đó sáu lỗi thuộc hai
tệp do bộ đối chiếu mới chưa giữ khóa không phải chuỗi. Đã sửa guard
ở helper kiểm tra và chạy lại đúng hai tệp: 47/47 đạt, bao gồm đủ sáu
case từng lỗi. Các receipt được đối chiếu, không gọi đây là một lượt
chạy toàn bộ mới hoặc tổng đã khử trùng. Mã ứng dụng worker giữ nguyên.

Không thay chữ của lựa chọn tỷ lệ/định dạng, không tạo ảnh, không gọi
nhà cung cấp hoặc ví. CI, runtime, giao diện production sau đăng nhập
và toàn bộ goal vẫn là các cổng riêng.
