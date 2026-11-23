# Trước phát hành — thông báo nhập liệu thiết kế ảnh

BASE/runtime5a95e48c9df922cc19a4bd83dfef46f2d85c04d2, contract689/7094579676.
PR799 đã triển khai; đợt này một nhánh/PR riêng, không trộn việc tiếp theo.

1. Vận hành hiện tại: đã cập nhật `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`,
   ghi riêng bản đang chạy và ứng viên30record/2UI files/51key. Không
   thay khả năng xử lý ảnh, auth, API, provider, tiền hoặc dữ liệu thật.
2. Đối chiếu tài liệu gốc: dùng các Image/Composer contracts hiện có và
   BASE đã triển khai; cập nhật `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`.
   Không bịa danh sách tính năng bộ mã mua sẵn. Các điều kiện xử lý giữ,
   chỉ lớp hiển thị đổi; không suy thêm tạo/lưu/giao ảnh.
3. Tester: phiên `IMAGE-STUDIO-VALIDATION-COPY-20261123` có8case nguồn,
   manifest và báo cáo riêng. Issue689 đang mở, đủ12nhãn Tester/22nhãn
   tổng, hai mẫu issue sẵn có đã kiểm lại. Không tạo thẻ/PR trống hoặc
   thay quyền project; trạng thái Projects cũ không được nhận đã xác minh.

RED213ca172fail/41pass; GREEN213/213. Hai nhóm chọn chạy174tệp,
5.135 lượt quan sát/4.925ca duy nhất, không lỗi/bỏ qua. Python tĩnh42/42
vàmetadata1/1; Image có1lỗi câu cũ trên exactBASE, không coi là lỗi mới.
Native auth cục bộ bị đứng, đã dừng đúng tiến trình QA; không nhận auth
PASS và không bỏ gate exact-head CI/Auth QA.

12màn Chrome375/1440 VIENZH với nguồn UI thật và dữ liệu giả đạt, không
mạng/ghi/tràn; hai ảnh chụp ổn định là kiểm lại. Reviewer delta cuối
C0/I0/M0, không kiểm lặp. Nguồn phải bằng BASE+đúng30record, phạm vi
và secret-shape phải kiểm trước commit;10statecũ không đọc/nạp/stage.
Provenance Web-only được tạo sau source commit rồi verify trước push.

PUSH_GATE yêu cầu mọi cổng trên và source/provenance đạt. ExactCI,
merge/tree, deploy/runtime/health/5+5assets/receipt vẫn tách riêng.
Signed production UI và toàn goal chưa hoàn tất; motion cuối.
