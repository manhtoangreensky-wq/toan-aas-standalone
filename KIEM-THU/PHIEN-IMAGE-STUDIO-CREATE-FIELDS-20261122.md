# Phiên kiểm tra nhãn biểu mẫu thiết kế ảnh

BASE `05b7ba761bd35cf4da498443db9046ed59429d90`.
Nguồn case: nhóm ISF trong `DANH-SACH-CASE.md`.

- ISF-COPY: 18 khóa/54 giá trị, mười trường ở VI/EN/ZH.
- ISF-DATA: tên trường, giới hạn, required, options và tên dự án giả giữ.
- ISF-RENDER: tạo/chỉnh sửa × ba ngôn ngữ × 375/1440; 12 màn cô lập.
- ISF-OUTSIDE: sáu đối chiếu phần ngoài form và cấu trúc trong form;
  thay đổi giả ở giới hạn phải bị phát hiện.
- ISF-DELIVERY: CI, merge, VPS và asset phải có chứng cứ riêng; không
  suy giao diện sau đăng nhập từ mã asset.

11 kiểm tra mục tiêu, 12 màn và 147 Python đã đạt. Hồi quy 165 tệp có
5.139 dòng/sáu lỗi ở helper kiểm tra; sửa guard và chạy lại đúng hai
tệp cho 47/47 đạt, đã đối chiếu đủ sáu case từng lỗi.
Không dùng dữ liệu khách hoặc dịch vụ trả phí.
