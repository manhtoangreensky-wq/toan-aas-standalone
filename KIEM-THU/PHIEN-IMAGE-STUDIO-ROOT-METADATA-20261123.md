# Phiên kiểm tra — chữ đầu trang gốc thiết kế ảnh

ID `IMAGE-STUDIO-ROOT-METADATA-20261123`, Issue #689.
BASE `3d21e950fb8e676ffd0b8c945a5ff6d9c8425736`.
Case ISRM trong `DANH-SACH-CASE.md` là nguồn duy nhất.

Kiểm hai trang `/image-studio`, `/image-hub` ở Việt/Anh/Trung, đang tải/
tải lỗi/sẵn sàng. Chữ cố định đúng ngôn ngữ; tên khách có chữ giống nhãn
và ký tự đặc biệt vẫn nguyên văn và được escape. Controls/options/giới
hạn/required giữ. Sáu route khác đối chiếu ở ba locale.

Từ điển thêm đúng2 khóa và đổi đúng4 hàng. So nguồn BASE+7record;
projection lịch sử chỉ nhận đúng các byte đã duyệt, không che thay đổi
khác. Chrome375/1440, không gửi form hoặc gọi dịch vụ thật.

Đã kiểm8 Node mới về metadata,18 trạng thái đọc/18 đối chiếu route,
12 màn Chrome375/1440 và nội dung khách/controls/input. Kiểm nguồn đúng
7 record metadata. Phụ lục ROOT-HEADING thêm1record CSS;36/36 mẫu màu
nguồn vật lý đạt, nền/hình học/màu tối không đổi. Tổng ứng dụng8record/
3tệp, không thêm hành động.

Node cục bộ99 ca duy nhất/16 tệp theo kết quả ghép, không phải lượt toàn
suite mới. Có15 lỗi đối chiếu cũ ban đầu, trong đó1 đã có trên BASE; sau
đọc hữu hạn và giữ assertion, không còn lỗi. Một lỗi idempotence helper
QA có RED riêng rồi sửa, không phải lỗi worker/app. Python245/245 đạt;
90 màu sau CSS là lượt kiểm lại tập con, không cộng thành335.

Review metadata và addendum CSS đều C0/I0/M0, không chạy lặp test bởi
reviewer. Trạng thái LOCAL_CHECKED_RELEASE_PENDING. CI/merge/deploy/
runtime/assets và tương tác production sau đăng nhập có bằng chứng riêng.

CI đầu45124090509 có6 lỗi legacy markup tại thẻ Hub của danh mục ảnh.
Đã sửa đúng đầu đọc i18n lịch sử, giữ assertions, thêm kiểm raw cả hai thẻ
ba locale.147/147 đạt (138 legacy+9 metadata);238 ca Node duy nhất/17tệp
theo kết quả ghép hiện tại. Ứng dụng không đổi sau CI đầu. Chờ CI mới.

Đã phát hành PR #799: CI45129027195 hai job success đúng HEADb05d786b;
merge/runtime5a95e48c9df922cc19a4bd83dfef46f2d85c04d2. Deploy45132203233
success; VPS nguồn sạch, ba dịch vụ/health đúng và5+5assets khớp commit.
Receipt689/7094535782 đọc lại đúng. Trạng thái DELIVERED, không phải
signed production UI PASS; bằng chứng tương tác production vẫn riêng.
