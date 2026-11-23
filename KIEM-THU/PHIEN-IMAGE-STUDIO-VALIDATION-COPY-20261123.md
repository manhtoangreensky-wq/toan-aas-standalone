# Phiên kiểm tra — thông báo nhập liệu thiết kế ảnh

ID `IMAGE-STUDIO-VALIDATION-COPY-20261123`, Issue #689;
contract7094579676, BASE5a95e48c9df922cc19a4bd83dfef46f2d85c04d2.
Case ISVC trong `DANH-SACH-CASE.md` là nguồn duy nhất.

Phạm vi30record trong integration.js/portal-i18n.js,51key VI/EN/ZH và
25nhãn tĩnh. Worker đề xuất, root áp dụng; không tự sửa ứng dụng ngoài
record. Hai thiếu sót phiếu dấu nháy/hướng dẫn chọn ảnh là SPEC_SAI,
không tính lỗi code worker; mọi đề xuất ban đầu còn được giữ.

RED nguồn vật lý213ca:172 lỗi câu chữ/nguồn,41 đạt. GREEN213/213.
Nhóm tám tệp ảnh hưởng391/391 đạt, bao gồm213 mới; không cộng lặp.
12màn Chrome375/1440/VIENZH, nhập sai tên hoặc dán liên kết vào Composer:
thông báo locale đúng, role alert, dữ liệu gõ giữ, không tràn/mạng/ghi.
Hai ảnh375 tiếng Việt chụp lại sau hiệu ứng hiện chữ kết thúc, không
cộng thành14màn mới. Không thay motion của ứng dụng.

Python Image/Composer16đạt/1lỗi. Lỗi cũ
`test_image_studio_is_truthful_about_no_execution_or_media_output` đòi
chuỗi giải thích rawURL đã bỏ trước đây; tái hiện exactBASEtest/app:
7ca6đạt1lỗi. Không đưa chữ kỹ thuật trở lại app để làm test xanh.

Review đề xuất gốc phát hiện đúng một hướng dẫn sai ngữ cảnh; sau phiếu
chỉnh, review delta cuối C0/I0/M0. Reviewer không chạy test lặp.
Hồi quy còn lại/Python locale, prepush/provenance/CI/deploy còn chờ
bằng chứng cuối; không nhận cả goal hoặc signed production UI hoàn tất.

Hồi quy còn lại đã đạt4.744 lượt/166tệp,0lỗi/0bỏ qua. Gộp với nhóm
391 là5.135lượt/174tệp chọn,4.925ca duy nhất theo JUnitfile/line/column/name.
Python tĩnh42/42 vàmetadata1/1, py_compile app/helper/test exit0.
Lượt auth cục bộ đứng sau16ca bundle đã dừng đúng tiến trình QA; không
nhận auth PASS. Hai ca native vẫn chờ exact-head CI, không sửa auth/app.
Prepush có tài liệu vận hành/đối chiếu/phiên Tester; đủ12nhãn và2mẫu
issue dùng lại, không tạo thêm thẻ trống. Source/provenance/CI/deploy còn riêng.

Flow trình duyệt dùng renderer/hàm kiểm tra/nhánh hành động và toast
nguồn vật lý với dữ liệu giả. Đây không phải fullbootstrap/auth/API.
Không đăng nhập mới, không đọc cookie/profile. Provider/ví/dữ liệu thật0.
