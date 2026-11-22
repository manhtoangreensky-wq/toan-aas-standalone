# Phiên kiểm tra tùy chọn ảnh

BASE `f4c5b6a9821cf957ce107778fd9abd884075fd50`.
Nguồn case: nhóm ISO trong `DANH-SACH-CASE.md`.

- ISO-RATIO: tám tỷ lệ đúng VI/EN/ZH, giữ keys/order/default.
- ISO-FORMAT: PNG/JPG/WebP rõ ràng, giữ giá trị và cách nhận hoa/thường.
- ISO-FALLBACK: thiếu bộ dịch vẫn có nhãn Việt đọc được.
- ISO-PRESERVE: nhãn trường, metadata, dữ liệu giả và phần ngoài form giữ.
- ISO-DELIVERY: CI, merge, deploy, VPS và asset có chứng cứ riêng.

16 mục tiêu, sáu đối chiếu renderer, 12 màn và 147 Python đã đạt;
kiểm tra rộng 165 tệp đạt 5.139/5.139, không lỗi hoặc bỏ qua.
Không dùng dữ liệu khách hoặc dịch vụ trả phí.
