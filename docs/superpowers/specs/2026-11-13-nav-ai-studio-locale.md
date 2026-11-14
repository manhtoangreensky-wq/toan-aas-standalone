# Nhãn nhóm sáng tạo theo ngôn ngữ

BASE: `c4da5f4a90a4ca37c46b66220c81928b806a4f2a`, PR #725 đã triển khai.
Tracker: Issue #689. Chỉ thêm alias cố định `AI Studio` vào
`NAVIGATION_I18N_KEYS`, tái dùng khóa `shellNav.aiStudios` hiện có.

Không đổi helper/chữ ký, manifest, khóa dịch, tên hoặc dữ liệu khách, route,
controls, auth/API/backend, giá/tiền/provider/Bot hoặc motion.

- [x] Renderer bundle xác nhận nhãn gốc ở bảy nhóm và nhánh `/features` cũ.
- [x] Phiếu nguồn công khai đầy đủ MAP trả đúng một phép thêm alias.
- [x] RED27: 24 nhãn cần đổi, ba ca bảo vệ nhãn khách/unknown; sau sửa27đạt.
- [x] Áp dụng đúng đề xuất, so mọi dữ liệu/control/HTML ngoài hai phạm vi đã duyệt.
- [x] Giao diện nhóm ảnh/tài liệu/nội dung thật VI/EN/ZH mobile/desktop,18click sang video.
- [ ] Nghiệm thu hồi quy, tài liệu/Tester/provenance và phát hành đúng SHA.

Phiếu bỏ khối trạng thái Hội viên được rút trước mọi sửa mã: CSS hiện tại
đã ẩn `.portal-status-grid`; chuyển thẻ ra ngoài khối ẩn có thể làm hiện lại
chữ kỹ thuật ở các trạng thái khác. Đây là thiếu sót khảo sát/spec, không
chấm lỗi ứng dụng cho worker và không tự sửa hoặc bỏ bài kiểm tra để xanh.
Giữ nguyên renderer/CSS/trạng thái đó; không đóng khả năng nhìn thấy lỗi thật
trên toàn app bằng việc quan sát source. Motion vẫn cuối theo checklist mẹ.

Đối chiếu entry thật: `/features` root hiện dùng bundle danh mục nhẹ riêng,
không nạp `portal.js`/`integration.js`. Do đó không dùng ca renderer nhánh root
cũ làm bằng chứng giao diện root hiện tại. Native phải vào `/features/image`
và chuyển nhóm thật, là nơi dùng alias này; entry root không đổi trong đợt này.

Prerequisite helper giả đã được bỏ theo spec riêng cùng ngày; Node421đạt và
native18view/18click không còn36lỗi CSP của lượt trước. Gate phát hành vẫn riêng.
