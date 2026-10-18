# R218-07C — Account và Billing: control-level UI/UX

Ngày 2026-10-18. Phạm vi chỉ là WebApp standalone, tập trung vào UI/UX,
locale, responsive, accessibility, auth lifecycle và trạng thái guarded. Spec
này không mở quyền nạp tiền, duyệt tiền, cộng Xu, PayOS, Bot, provider,
production data hoặc triển khai.

## 1. Route và nguồn đối chiếu

| Mã | Route/surface | Mục tiêu kiểm tra |
|---|---|---|
| AC-01A | `/account` | Hồ sơ, ảnh đại diện, phương thức đăng nhập, liên kết, phiên và CTA chính |
| AC-01B | `/account/interface-language` | VI/EN/ZH, locale UI độc lập với ngôn ngữ Bot/content |
| AC-01C | `/account/security` | Tình trạng bảo mật, phiên, mật khẩu, OAuth, MFA, logout và trạng thái guarded |
| AC-01D | `/account/activity` | Nhật ký owner-scoped, rỗng/tải lỗi/làm mới, không lộ dữ liệu riêng tư |
| AC-01E | `/account/data-controls`, `/account/workspace-care` | Phạm vi dữ liệu Web, export/review request và ranh giới không đụng Bot |
| AC-02A | `/wallet` và `/wallet/history` | Số dư/lịch sử chỉ đọc từ nguồn chuẩn, unknown không biến thành số 0 |
| AC-02B | `/wallet/topup` | Chọn phương thức → nhập số tiền → review → hướng dẫn/QR → pending/history |
| AC-02C | `/packages`, `/pricing` | Catalog/gói/giá công khai, chỉ đọc, không tạo mua/checkout/charge |
| AC-02D | Admin handoff | Pending request có request ID/trạng thái thật để Admin đọc; approval/wallet write giữ T0 |

## 2. Bảng control bắt buộc

### AC-01 — Hồ sơ, locale, phiên và bảo mật

| Control | Đầu vào/trạng thái | Hành vi được phép | Cổng đóng |
|---|---|---|---|
| Hồ sơ | Tên hiển thị, avatar, timezone, locale; loading/empty/error | Giữ draft, submit chỉ khi capability + CSRF thật | Không tự suy diễn account/role |
| Phương thức đăng nhập | Email, Telegram, Google, GitHub, Apple; linked/ready/guarded | Hiển thị trạng thái server; OAuth bắt đầu từ action được cấp quyền | Không ghép account theo email ở client |
| Liên kết Bot | linked/unlinked/pending | Chỉ điều hướng/hiển thị projection đã sanitize | Không nhận Telegram ID/callback/state |
| Phiên | current/other/revoked/unknown | Hiển thị owner-scoped, logout/thu hồi có confirmation | Không lộ session ref/token |
| Mật khẩu/MFA | available/guarded/awaiting confirm | Form có autocomplete, no-store secret, confirmation rõ | Không lưu secret local/session storage |
| Hoạt động | list/loading/empty/error/stale | Tối đa 50 dòng đã redaction, refresh có epoch/path/session fence | Không trộn ví, Bot, PayOS, provider, ticket |
| Dữ liệu | export/review/cancel/closed | Nêu rõ phạm vi Web, giữ revision và confirmation | Không xóa tự động, không chạm dữ liệu Bot |

### AC-02 — Ví, gói, giá và nạp thủ công

| Control | Đầu vào/trạng thái | Hành vi được phép | Cổng đóng |
|---|---|---|---|
| Số dư/lịch sử | balance, rows, pending, unavailable | Chỉ render canonical projection; unknown giữ unknown | Không tính lại ledger ở browser |
| Gói/giá | catalog version, SKU, sale price, unavailable | Hiển thị label/giá đã được nguồn chuẩn cấp | Không suy đoán giá/tỷ lệ/ưu đãi |
| Chọn nạp thủ công | phương thức hợp lệ và amount VND | Chỉ mở review sau khi đủ hai đầu vào | Không hiện QR/mã trước khi chọn đúng method |
| Review | amount, method, transfer content, confirmation | Hiển thị số tiền, phương thức, cảnh báo “chưa cộng Xu” | Không tự tạo approval/credit |
| Hướng dẫn/QR | ready/unavailable/expired | Chỉ hiển thị QR riêng tư sau readiness server; lỗi thì ẩn QR | Không public static QR/private path |
| Pending | request ID, pending_admin_review, rejected, approved projection | Hiển thị trạng thái, lịch sử, retry/reload an toàn | Browser không approve/reject/cộng Xu |
| PayOS | available/guarded/paid/pending/failed | Chỉ mở checkout/trạng thái khi server cấp capability | Không gọi provider/webhook/charge từ UI |
| Admin liên kết | request ID + amount + status + revision | Liên kết tới màn Admin read/approval surface khi có quyền | Approval/money mutation giữ T0 |

## 3. Quy tắc trình bày và ngôn ngữ

- Một thanh điều hướng Billing dùng anchor thường cho `/wallet`,
  `/wallet/topup`, `/packages`, `/pricing`; active route dùng `aria-current`.
- Desktop giữ một hàng gọn; mobile cuộn trong thanh điều hướng nội bộ, không
  tạo overflow toàn trang; control tối thiểu 44px.
- Luồng nạp hiển thị dọc: phương thức → số tiền → review → hướng dẫn/QR →
  pending/history. QR không xuất hiện ở trạng thái chưa chọn phương thức hoặc
  chưa có readiness.
- Màu nền tối là navy/xanh, chữ sáng; nền sáng dùng chữ tối tương phản. Không
  chuyển giao diện sang nền đen hoặc dùng màu làm nguồn trạng thái duy nhất.
- VI phải là tiếng Việt tự nhiên; EN và ZH có catalogue riêng. Tên riêng như
  Google, GitHub, Apple, Telegram, PayOS, MoMo, ZaloPay giữ nguyên.
- Error/empty/loading/stale/guarded phải có câu giải thích và hành động tiếp
  theo; không dùng spinner đơn độc hoặc dữ liệu giả.

## 4. Auth lifecycle và stale-data contract

1. Khi đổi account, logout, route hoặc session epoch, xóa projection riêng tư
   cũ trước khi request mới được phép ghi vào DOM.
2. Activity, drafts, link status và payment options phải kiểm tra đồng thời
   request epoch, session epoch, route hiện tại và `authenticated === true`.
3. Form draft chỉ giữ dữ liệu không nhạy cảm; password, OTP, MFA key, CSRF và
   token phải xóa trong `finally`/sign-out.
4. Mọi mutation thật phải dừng ở capability, CSRF, ownership, revision và
   idempotency do server cấp; control-level không được tự giả lập receipt.

## 5. Bằng chứng hiện có và phần còn mở

- Account profile/activity/dropdown locale và keyboard: Node targeted hiện đạt
  `9/9`; full Node baseline gần nhất `566/566`.
- Billing/manual-topup/backend contracts tồn tại trong bộ Python test nhưng
  chưa thể chạy ở workspace hiện tại vì thiếu `python`/`py`.
- Browser/AX matrix, authenticated runtime, QR/bytes, pending/admin record,
  CI cho HEAD mới và LIVE chưa được suy diễn từ static tests.
- AC-01/AC-02 vẫn giữ trạng thái mở trong checklist cho tới khi từng route có
  renderer/interaction + browser/AX evidence tương ứng.

## 6. Điều kiện đóng

Chỉ chuyển AC-01 hoặc AC-02 từ `[ ]` sang `[~]` khi control-level evidence
được chạy mới và có disposition rõ cho mọi control trong bảng. Chỉ chuyển sang
`[x]` sau khi có browser/AX VI/EN/ZH ở 375/390/768/1440, trạng thái loading/
empty/error/stale/guarded, và bằng chứng runtime đúng phạm vi. Không coi
`HTTP 200`, route tồn tại, QR hiển thị hoặc pending projection là approval,
credit, PayOS success hay LIVE PASS.
