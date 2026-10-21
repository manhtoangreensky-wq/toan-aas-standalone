# Q0-CUSTOMER-CONTENT — tiêu chí nội dung và hành động thật

Owner22/10/2026: “tuyệt đối không được ghi thử nghiệm hay từ ngữ tương tự,
không có những ô vô nghĩa”. Giữ thứ tự: xong UT-CSP-EMPTY-THUMB rồi rà tiếp
theo checklist mẹ; không bỏ các spec đang mở hoặc viết lại luồng đã khóa.

## Yêu cầu bắt buộc theo từng control

1. Không nhãn thử nghiệm/demo/beta/sandbox/POC trong fixed chrome khách; không
   tự điền thông tin QA vào sản phẩm. Không sửa/xóa nội dung thật do khách nhập.
2. Ô nhập, chọn giọng, mode, ngôn ngữ, âm lượng và thiết lập chức năng phải giữ.
   Loại nhãn khả dụng lặp, khung chỉ để nói không có dữ liệu, bảng chỉ toàn dấu
   gạch và lời giải thích kỹ thuật không giúp khách quyết định.
3. Kết quả/preview/tải tệp chỉ mở khi có dữ liệu tương ứng. Empty-state phải nói
   việc cụ thể có thể làm; khi chưa thao tác, ưu tiên không dựng ô kết quả rỗng.
4. Lỗi thật và lý do không gửi được vẫn phải rõ tại hành động liên quan, có
   cách thử lại/đăng nhập/điều chỉnh khi khả dụng. Không giấu lỗi bằng CSS.
5. Một nút phải có thao tác và phản hồi có thể kiểm. Lưu nháp gọi đúng API và
   đọc lại; tạo media phải có job/kết quả/tệp được xác nhận. UI pass không đóng
   provider/engine/output gate; không đổi tên nút lưu nháp thành tạo thật.

## Thứ tự nghiệm thu

- [x] Truy nguồn2ảnh Owner: chuỗi lời thoại đến từ default-gender-server.cjs
  của QA cũ; badge Voice do pageStatusBadge, được source CSS mới ẩn đúng.
- [x] Đưa tab sang app QA thật với DB cô lập; không dùng query quote/expires
  của fixture cũ làm bản bàn giao. Ô lời thoại trống và hero badge0.
- [x] Rà96initial states ởVoice4mode, Music create, SubDub, Image create,
  Free Tools; VI/EN/ZH ×light/dark ×390/1440. Bằng chứng ngày22/10 riêng.
- [ ] Rà các trạng thái sau thao tác/báo lỗi/kết quả của từng sản phẩm theo
  planR218; các dữ kiện/backend còn thiếu phải lưu trong ledger T0 hiện hữu.
- [ ] Rà các màn còn lại theo thứ tự Utilities →Admin →Video; không đóng toàn
  WebApp từ8route đầu. Mỗi phiếu2–5phút, allowlist/source snippet/verify rõ.
- [ ] Motion/performance làm cuối; đo riêng, không suy ra từ ảnh tĩnh.

Không thay palette xanh/navy/teal, auth/RBAC, Bot/engine, provider, ví, PayOS,
schema hoặc production data trong spec giao diện này. Lỗi kỹ thuật ngoài phạm
vi được ghi cuối checklist và chờ đúng bước/quyền.
