# Nhãn dùng chung ảnh và bỏ chip kỹ thuật Resize

BASE=ce40bf4089701d0ba47f46845e7061cb92d5bba1.
Branch=codex/image-shared-plain-copy-20261117.
Tracker=Issue689; phát hành tăng dần theo quyền Owner.

Mục tiêu: người dùng đọc được nhãn thao tác ảnh đúng VI/EN/ZH, không thấy hai
cụm nhãn kỹ thuật lặp trên Resize. Giữ nguyên toàn bộ chức năng và lỗi thật.

Phạm vi ứng dụng khóa:

1. static/portal/portal-i18n.js: đúng21hàng có sẵn trong
   IMAGE_OPERATION_COPY_ROWS từ proposal IMAGE-SHARED-FILE-COPY-20261117.
2. static/portal/portal.js: đúng hai dòng return của renderImageResize từ
   IMAGE-RESIZE-STATE-META-REMOVAL-20261117; chỉ bỏ nguyên div ba span.

Hai worker chạy output-only trong thư mục riêng, modelgemini-3.8-flash-high;
điều phối chỉ replay đề xuất khớp, không tự sửa ứng dụng. Lượt schema400
usage0 là lỗi mẫu gửi của điều phối, không tính worker thực hiện sai.

Acceptance:

- Chữ, trạng thái, source select, danh mục và phản hồi tải dùng giá trị đã duyệt.
- Hai div biến mất hoàn toàn; h2/p/state/ARIA/quyền/thử lại vẫn giữ.
- Khóa/thứ tự/placeholder/giới hạn/lựa chọn/customer literal giữ nguyên.
- Các tệp ứng dụng khác, Python/auth/ENV/engine/tiền/provider/motion giữ.
- RED trên BASE thật, kiểm ảnh hưởng một lượt, chỉ chạy lại lỗi phép đo.
- Native QA cô lập, tài liệu/Tester/provenance/CI/phát hành có bằng chứng riêng.

Không làm: đổi xử lý ảnh, thêm fallback/khả dụng, đổi Bot/routeengine/giá/ví/
PayOS/data/provider, sửa phụ đề custom hoặc cleanup utility khác ké phạm vi.
Toàn goal locale/AX/auth/responsive/Safari/device/signedUI/output còn mở;
M-FINAL01..06 vẫn cuối.
