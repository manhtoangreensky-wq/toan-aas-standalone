# Phiên Tester — chi tiết thiết kế ảnh

BASE `f6aee803a72a80bf70cd0a4ce786858f94f9d7cc`; Issue689.
Case ISD-COPY, ISD-STATES, ISD-CONTRAST, ISD-SOURCE, ISD-DELIVERY
trong `DANH-SACH-CASE.md`. Dùng dữ liệu giả, không gửi form thật.

Kiểm tra 21 câu ở Việt/Anh/Trung, trạng thái chưa mở được/không có dữ liệu/
phương án và giữ nguyên tên khách, quyền và thao tác. Hai dòng trợ giúp
đọc rõ trên Studio/Hub, tạo/chỉnh sửa, điện thoại/máy tính, sáng/tối.

Đã đo 24 trạng thái/63 giá trị, 48 màn/96 mẫu và 30 kiểm tra Node;
237 Python đạt sau sửa hai câu.
Hồi quy5151ca/5145PASS/6FAIL so sánh chữ thẻ; retest đúng tệp138PASS.
Không nhận là một lượt fullPASS mới. Phát hành chờ bằng chứng riêng.
Màn chi tiết khi đang tải chưa có trạng thái chờ riêng; theo dõi Issue689/
comment7078219437, không nhận đã sửa trong đợt chữ này.
