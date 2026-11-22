# Kiểm tra chữ tùy chọn ảnh

BASE `f4c5b6a9821cf957ce107778fd9abd884075fd50`.
Trạng thái: kiểm tra cục bộ, chờ CI và phát hành.

Hai phiếu Antigravity chạy song song. Định dạng R1 có ba record đúng;
tỷ lệ giữ hai record R1 đúng và dùng một record R2 cho đăng ký bản
dịch. R1 thiếu mẫu đăng ký trong phiếu nên đã bổ sung đúng mẫu; đoạn
đăng ký sai chưa được áp dụng. Tổng sáu record được đối chiếu với toàn
nguồn của hai tệp trước và sau áp dụng.

16 kiểm tra mục tiêu đạt, gồm tám tỷ lệ ở ba ngôn ngữ, định dạng,
giá trị/defaults, fallback và bảo vệ các nhãn trường vừa phát hành.
Sáu đối chiếu renderer so với BASE giữ nguyên phần ngoài form và toàn
DOM trong form ngoài đúng chữ tùy chọn; đối chứng đổi giới hạn được
phát hiện. Cả 12 màn tạo/chỉnh sửa × ba ngôn ngữ × hai kích thước đạt,
không tràn ngang, lỗi trang hoặc yêu cầu mạng. 147 Python đạt. Hồi quy
rộng 165 tệp đạt 5.139/5.139 trường hợp, không lỗi hoặc bỏ qua.

Không tạo ảnh hoặc gọi provider/ví; toàn bộ goal và giao diện production
sau đăng nhập chưa được chứng nhận từ kiểm tra cục bộ.
