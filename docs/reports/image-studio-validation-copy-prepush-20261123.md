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

## Đồng bộ main —25/11/2026

PR800 CI45136242250 đã đạt cả hai job ở c7328b71 nhưng chưa merge.
Main/VPS đã chuyển sangb24da8f1e41f51c1f51ae5b3abb7d99da10cebf1,
CI45394416790 vàdeploy45398112184 success; PR800 hiện xung đột provenance.
Phụ lục689/7153324764 ghi trước merge. Giữ nguyên nguồn catalogue,
helperdetaildraft và timeout35phút từmain; không sửa validation30record.
Hai tệp ứng dụng riêng của PR vẫn bằng main+30record exact; hai tệp
upstreamcatalog/helper giữ exactmain. Tạo lại provenance trên merge
sourcecommit và chạy CI/AuthQA ở HEADmới; không dùng CIc732 thay bằng chứng.
Các số hồi quy trước sync là lịch sử đã đo, không nhận đã chạy lại toàn bộ.
Sau sync nhóm giao nhau391/391 vàmetadata1/1 đạt. App validation giữ
main+30record exact, upstreamcatalog/helperdiffexit0; không có thay đổi
chức năng mới. CI mới vẫn bắt buộc.

Owner đổi phiếu mới sang Gemini4.0; CLI models đã xác nhận
gemini-4-hydrogen-xhigh (Extra High theo Owner). Không sửa settings/login,
không gọi lại các phiếu
3.8 đã hoàn tất chỉ để đổi tên model; không có3.8worker đang chạy.
