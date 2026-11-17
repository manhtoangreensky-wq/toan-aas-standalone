# Phiên kiểm tra — chiều cao ô nhập Đổi kích thước ảnh

TESTER_PROJECT_ID=RESIZE-CONTROL-HEIGHT-20261118.
TESTER_PROJECT_STATUS=READY.
BASE_SHA=4180d4e2ec0ac4303037b409e55cb5f86106fa84.
HEAD_SHA=Source commit và receipt CI exact HEAD trước phát hành.
TRACKER=Issue689.

Nguồn case duy nhất: DANH-SACH-CASE.md, sáu hàng RCH.
Ứng dụng chỉ một rule align-content riêng Resize;150 tệp khác được bảo vệ.
Không thay chữ, control/options/giới hạn, quyền, dữ liệu, engine hoặc motion.

- [x] BASE Chrome12:6desktopRED/6mobilePASS đúng lỗi kéo cao.
- [x] Candidate Chrome12:12PASS,3,56s.
- [x] Đối chiếu exact worker addition và giữ byte ngoài.
- [x] Ba assertion nguồn bị ảnh hưởng đạt sau sửa QA reader, không đổi app.
- [x] Native actual localhost6READY,30control44–44,5px,3locale/2viewport.
- [x] Chọn ảnh,1080×1920/Tab,giới hạn/options/submit-enabled giữ,không submit.
- [x] Không overflow/pageerror/console/dialog/egress;22ownedstopped0active.
- [x] Dữ liệu/lược đồ/nguồn151/binding/fixture/scope giữ;exact3loginaudit.
- [ ] CI exact HEAD.
- [ ] Merge/deploy/runtime/assets receipt.
- [ ] Signed production UI nếu cần kết luận LIVE giao diện.

Bốn ảnh raw đã được xem; không coi crop hay localhost là thiết bị thật/
Safari/PNG cuối. Không chạy lại các nhóm đã đạt nếu nguồn không đổi.
Chi tiết từng lượt: docs/reports/image-resize-control-height-20261118.md.
Toàn goal vẫn mở, motion cuối.
