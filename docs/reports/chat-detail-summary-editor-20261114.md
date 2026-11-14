# Hội thoại chi tiết: thông tin và phần chỉnh sửa đúng ngôn ngữ

BASE `20c3e6fdf25f834fd6b62fbccbe6f8934e188119`, sau PR734 đã triển khai.
Theo dõi duy nhất tại Issue689. Hai phiên Antigravity 3.8 Flash High độc lập
trả năm thay đổi trong hai tệp ứng dụng, gồm 11 khóa/33 giá trị VI/EN/ZH.

## Hành vi hiện tại

Thông báo chưa mở được hội thoại có hướng dẫn quay về danh sách, giữ nguyên
điều kiện quyền/thiếu bản ghi/ID. Phần thông tin dùng nhãn trạng thái, lần cập
nhật, ghi chú/lượt trao đổi đúng ngôn ngữ; tên và nội dung khách giữ nguyên.
Chỉ bỏ tiền tố `v` trước số cập nhật, không đổi phép tính hoặc dữ liệu.
Phần chỉnh sửa có năm nhãn/hướng dẫn/nút theo ngôn ngữ; huy hiệu dùng chữ
trạng thái hiện có, không đổi lớp, mã trạng thái hay quyền thao tác.

Giữ tám trường, constraint, ID, thứ tự lựa chọn, lifecycle calls, thuộc tính
xác nhận, disabled, route, số đếm, fallback nội dung và escaping. Không sửa
backend, auth, API, ví, Bot, provider, CSS, motion hoặc cache.

## Bằng chứng đã đo

- Candidate thực thi bundle trong VM: BASE0/30 đạt, ứng viên30/30 đạt.
- Permanent tests: BASE22/22 lỗi; sau áp dụng chạy gộp với các kiểm tra cũ
  125/125 đạt, exit0. Nhóm ảnh hưởng286/286 đạt; Python9/9 đạt.
- Kiểm cú pháp hai JS và `py_compile app.py` exit0.
- Adapter hữu hạn kiểm đúng 11 khóa theo thứ tự và toàn hàm chi tiết có hash;
  khóa lạ/thiếu/đổi chữ/đảo thứ tự hay sửa ngoài phạm vi vẫn bị phát hiện.
  Độ đóng băng đo trực tiếp trên từ điển thật trước khi tạo bản chiếu.
- 17 tệp ứng dụng được bảo vệ và toàn bộ Python không đổi so với BASE.
  Review độc lập C0/I0/M1; không chạy lặp suites hoặc browser bởi reviewer.

M1 là ba dòng trống điều phối thêm trong i18n. Nội dung và thứ tự năm thay
đổi worker đúng; `portal.js` khớp byte LF hoàn toàn. i18n chỉ khác ba byte LF,
được ghi amendment rõ ràng, không quy lỗi worker. Giữ nguyên bản native đã
đo, không sửa app sau kiểm tra và không nhận là exact-byte replay cả hai tệp.

### Kiểm tra giao diện trên dữ liệu QA riêng

Ba máy chủ riêng cho VI/EN/ZH, mỗi ngôn ngữ tám trạng thái:
375px sáng và1440px tối × bản nháp/xem lại/sẵn sàng/lưu trữ.
24/24 trạng thái duy nhất đạt;13 ảnh. Dùng liên kết thật, GET danh sách/
chi tiết/lượt xử lý thật, cùng quyền sở hữu. Không giả định public account
có ID nội bộ, không thay auth hoặc RateGuard.

Không lỗi trang/console/dialog/tràn; không request ngoài hoặc ghi sản phẩm.
Mỗi lượt có đúng ba fake-auth POST; còn lại GET/HEAD.15 bản ghi hội thoại QA,
ba chủ sở hữu, sáu kế hoạch/18 cảnh, schema/fingerprint và bằng chứng nguồn
được giữ. Tiến trình do từng lượt tạo đều về0.

Nguồn ứng dụng giữ nguyên qua cả ba lượt; hash tệp thực tế:

- portal.js `9cd56089232c72660061ededc276412d3aba95b9aa6d9a7d987560e3871869ec`
- portal-i18n.js `76118f081f48670031ad40af6da3224815bccfb757052494c0758aa73f51b7ef`

Bằng chứng cục bộ: `chat-summary-editor-permanent-red-nov14.log`,
`chat-summary-editor-green-prior-nov14.log`,
`chat-summary-editor-affected-nov14.log`,
`chat-detail-summary-editor-native-aggregate-nov14.json`.
Chỉ công bố số đo; không công bố DB, tài khoản, token hoặc phản hồi khách.

## Giao hàng và giới hạn

PR734 đã gộp và triển khai: HEAD10fa0844, CI43595369145 đạt hai nhóm,
merge/runtime20c3e6fd, deploy43607141243 đạt, tree d93f4e09 khớp.
Receipt Issue6896879247049 và PR7346879247351.

Đợt hiện tại có cổng commit/provenance/exact-head CI/merge/deploy/runtime/
assets riêng; chưa suy ra giao hàng từ local PASS. Checkbox mặc định
“Tôi xác nhận” còn trong EN, cùng context/turn/history/run/toast ngoài phiếu,
được giữ mở và không che đi. Toàn AX/auth/device/Safari/signed production
và M-FINAL01..06 vẫn mở. UI PASS không chứng minh đầu ra engine thật.

`PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_WRITES=0`.
