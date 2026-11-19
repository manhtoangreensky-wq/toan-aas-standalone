# PDF — đúng ngôn ngữ, bỏ phần giải thích nội bộ

TASK=PDF-UTILITIES-CUSTOMER-COPY-20261119.
BASE_SHA=513557a9ece0f8fe049884868dc5fb3a1ac2339c.
BRANCH=codex/four-route-coverage-20261119; TRACKER=Issue689.

## Kết quả và thứ tự

1. Nén PDF: bỏ đúng một lời gọi renderNotes cuối trang, không đổi factory,
   cấu hình hoặc ghi chú của các trang khác.
2. Ảnh thành PDF: tám trường hiện nhãn, lựa chọn trống và hướng dẫn đúng
   VI/EN/ZH bằng sáu khóa dịch mới. Giữ nguyên thứ tự, tên, ID, bắt buộc ô đầu,
   nguồn lựa chọn, bộ tìm tệp và giá trị gửi.
3. Ảnh thành PDF: giữ tiêu đề, biểu mẫu, lịch sử và phân trang; bỏ intro,
   khung bên, thông báo giải thích kỹ thuật và ghi chú dư. Liên kết kho tệp
   chuyển vào chân biểu mẫu, không bị bỏ. Chín khóa trang mới đủ ba ngôn ngữ.
4. Nghiệm thu chung, một PR, CI đúng HEAD, gộp và triển khai trước nhóm Chỉnh ảnh.

Ba phiếu độc lập chỉ trả văn bản từ Antigravity3.8FlashHigh, đăng nhập CLI đã có.
Root ghép tuần tự. Không gửi test/fixture/API/login response hoặc dữ liệu thật.
Authority bất biến: tests/fixtures/pdf-utilities-customer-copy-reviewed.json,
SHA256 fb1ffa41f9d924a11caf78b840d5ebc2a8e6a270eb49e91838868def71973870.

## Phạm vi được phép

Hai tệp ứng dụng: static/portal/portal.js và static/portal/portal-i18n.js.
Đúng ba hàm và một lần chèn danh mục, 15 khóa/45 giá trị; 149 tệp ứng dụng
khác giữ nguyên. Không đổi backend/auth/API/schema/engine/provider/ví/PayOS/
ENV/CSS/motion hoặc dữ liệu production; không gửi thao tác tạo sản phẩm.

QA được thêm fixture, hai bài kiểm mới, finite inverse ở biên so nguồn lịch sử;
giữ golden, assertion và negative vector cũ. Current renderer đọc nguyên bundle
vật lý. Bộ PDF lịch sử phải ghi rõ không phải bằng chứng UI hiện tại.
CI chỉ thêm một dòng gọi hai bài kiểm mới trong bước Node có sẵn; không đổi
trigger, quyền, timeout, dependency, deploy hoặc ma trận456.

## Acceptance

- Nội dung cố định đúng locale, không từ kỹ thuật dư; tên khách/tên riêng giữ.
- Không ô trống thay thế; tám trường và các chốt quyền/nguồn/lịch sử còn đủ.
- So toàn nguồn ngoài bốn thay đổi phải đúng Git BASE. Keyset/freeze giữ nguyên.
- Kiểm renderer vật lý, quyền strict-boolean, escaping và input bất biến.
- Quan sát thật hai route × VI/EN/ZH × sáng/tối ×320×844,414×896,768×414,
  1024×768; keyboard thật, không submit; giữ audit/schema/core/egress/source.
- Không suy toàn AX hoặc tương phản đạt khi nền màu còn UNKNOWN; recovery,
  auth-lifecycle, phản hồi muộn, Safari/thiết bị, signed production và output riêng.
- Sau đủ local gate: tài liệu/Tester/review/provenance, một PR/CI/merge/treeeq/
  deploy/runtime/assets/receipt cùng Issue689.

## Lịch sử sai phiếu

Root sửa target thừa một dấu ngoặc và neo danh mục sau freeze. Giữ đúng proposal
worker đã trả, không tái tạo giá trị thiếu, không gọi lại; worker application
failure=0. Original packet/schema/raw và bằng chứng lỗi được giữ bất biến.
Native startup timeout chỉ là lỗi kiểm tra riêng, không được tính thành app/AGY fail.
Giới hạn giữ60/180/10/5giây; không nới để ép đạt.

Không đóng goal tổng từ đơn vị này; Chỉnh ảnh kế tiếp, motion M-FINAL01..06 cuối.
