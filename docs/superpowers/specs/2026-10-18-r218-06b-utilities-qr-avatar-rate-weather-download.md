# R218-06B — Utilities: QR, avatar, tỷ giá, thời tiết và tải media

Ngày 2026-10-18 · Trạng thái `CONTROL_LEVEL_PARTIAL`

## Mục tiêu

Đưa các tiện ích đã có trong inventory Bot vào một workspace Công cụ miễn phí
dễ quét, theo cùng một thứ tự dọc: nhập nguồn → chọn tùy chọn → xác nhận quyền
hoặc điều kiện → xem trạng thái/kết quả. QR giữ luồng cục bộ hiện có; bốn tiện
ích còn thiếu được bổ sung ở mức trình bày và control-level, không giả lập dữ
liệu ngoài hoặc kết quả AI.

## Phạm vi đã lát

- Workspace `/free-tools` có 10 tab và 10 panel accessible; bàn phím mũi tên,
  Home/End vẫn chuyển tab ngay tại chỗ.
- QR VietQR giữ bank/account/name/amount/memo/template, preview, tải ảnh và
  sao chép liên kết như trước; không đổi logic URL hiện có.
- Ảnh đại diện AI có chọn phong cách, brief, xác nhận quyền sử dụng, vùng
  preview rỗng và nút chuẩn bị bị khóa khi chưa có capability.
- Tỷ giá có USD/VNĐ/Xu, nguồn, dấu thời gian, độ mới và nút làm mới guarded;
  không tự dựng tỷ giá.
- Thời tiết có địa điểm, đơn vị C/F, vùng kết quả rỗng và các trạng thái tải,
  lỗi, dữ liệu cũ được chừa rõ trong copy; không gọi nguồn ngoài trong QA.
- Tải media có chọn nguồn (YouTube/TikTok/Facebook/liên kết trực tiếp), URL,
  xác nhận quyền sử dụng, vùng kiểm tra rỗng và nút kiểm tra bị khóa; chỉ mở
  tải sau khi server xác nhận link, quyền, file và delivery.
- VI/EN/ZH có catalogue riêng cho toàn bộ chrome mới; tên riêng YouTube,
  TikTok, Facebook, VietQR, USD, VNĐ, Xu được giữ nguyên.
- CSS thêm result/empty/state surface theo palette xanh/xanh ngọc hiện tại,
  không đổi theme sang đen và không thêm transition/layout motion mới.

## Ranh giới an toàn

- Không gọi external API tỷ giá/thời tiết, không gọi provider AI, không tải
  video/media, không tạo ảnh đại diện, không sinh quote/job/output/delivery.
- Nút `prepare-avatar`, `refresh-rate`, `lookup-weather`, `inspect-download`
  disabled cho tới khi capability server được công bố; form chỉ giữ lựa chọn
  trong DOM hiện tại.
- Không chạm wallet/PayOS, dữ liệu production, Bot bridge, secret hoặc route
  kỹ thuật; không thay đổi QR payment flow đang khóa.

## File trong lát này

```text
static/portal/portal.js
static/portal/portal.css
static/portal/portal-i18n.js
tests/free-tools-hub-presentation.test.mjs
docs/superpowers/specs/2026-10-18-r218-06b-utilities-qr-avatar-rate-weather-download.md
reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md
reports/prepush/WEBAPP-BOT-PARITY-R218-PR654-UPDATE.md
TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
.agents/state/WEBAPP-BOT-PARITY-R218.yaml
```

## Acceptance / evidence

```text
node --test tests/free-tools-hub-presentation.test.mjs = 5/5
node --test tests/*.test.mjs = 549/549
node --check static/portal/portal.js = PASS
node --check static/portal/portal-i18n.js = PASS
git diff --check = PASS
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

UT-04 vẫn `[~]`: browser authenticated/AX theo viewport, dữ liệu nguồn thật,
refresh/error/stale runtime, downloader delivery và live evidence còn ở wave QA
hoặc technical register. Không gọi control-level này là parity runtime.
