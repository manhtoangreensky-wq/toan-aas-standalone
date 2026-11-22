# Trước phát hành — chi tiết thiết kế ảnh

BASE `f6aee803a72a80bf70cd0a4ce786858f94f9d7cc`. Hai tệp ứng dụng thay
đúng 21 câu cố định và một quy tắc màu. Luồng, dữ liệu, quyền, backend,
ví, nhà cung cấp và motion giữ nguyên. Đã cập nhật tài liệu vận hành,
đối chiếu chức năng gốc và phiên Tester gồm năm case.

30 Node/237Python/24 trạng thái/48 màn và96mẫu đạt sau sửa hai câu.
Hồi quy5151ca:5145PASS/6FAIL chữ thẻ đã đổi,
retest đúng tệp138/138PASS; không nhận một lượt fullPASS mới. Review phát
hiện câu suy đoán nguyên nhân; phiếu R2 sửa hai dòng trung tính. Review lại
hai dòng và phép đối chiếu thẻ ảnh không còn finding chặn; lifecycle tải
chi tiết vẫn mở riêng. Cần xác minh nguồn trước khi push. Signed production UI
và toàn goal chưa được xác nhận.
