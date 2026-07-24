# Billing canonical journey contract

## Mục đích

`/wallet`, `/wallet/topup`, `/packages`, `/pricing` là các màn ứng dụng đọc
và điều hướng billing. Chúng không phải bản sao của ledger Bot hay một hệ
thống checkout thứ hai.

## Authority và ranh giới

| Phần việc | Authority duy nhất | Web App được làm gì |
| --- | --- | --- |
| Số dư Xu, chi tiêu, VIP, gói hiện tại | Bot ledger qua Core Bridge | Đọc projection owner-scoped đã kiểm tra schema |
| Lịch sử Xu | Bot ledger qua Core Bridge | Hiển thị tối đa 100 dòng đầy đủ time/type/delta/balance |
| PayOS checkout / webhook / finalize | Bot canonical | Hiển thị URL PayOS đã allowlist; poll GET owner-scoped |
| Nạp thủ công, bill, TXID, đối soát | Bot + vận hành | Handoff sang Bot và hướng dẫn trạng thái; không nhận chứng từ |
| Gói và giá | Catalog canonical | Hiển thị khi catalog hợp lệ; không suy đoán giá/tỷ lệ Xu |

Không có browser code nào được phép ghi Xu, tự tạo QR/link, quyết định
`approved`, tạo webhook PayOS, giữ QR tĩnh/số tài khoản, nhận bill/TXID/OTP,
hay biến package/combo thành mệnh giá nạp.

## Wallet read model

Một snapshot chỉ `ready` khi toàn bộ điều kiện sau đúng:

- `balance_xu` và `total_spent_xu` là safe integer không âm;
- `is_vip` là boolean rõ ràng;
- history là mảng tối đa 100 dòng;
- mỗi dòng có `created_at`, `event_type`, `delta_xu` safe integer và
  `balance_after_xu` safe integer không âm.

Response HTTP 2xx nhưng thiếu hoặc sai một trường không được đọc thành `0 Xu`,
list rỗng hay lịch sử giả. Khi hydration route lỗi, Portal xóa projection cũ
và hiển thị recovery state. Khi người dùng chủ động làm mới, snapshot cũ đã
xác minh chỉ được thay bằng snapshot mới hợp lệ; response lỗi không ghi đè nó.

## Hành trình người dùng

1. Ví Xu hiển thị projection canonical hoặc trạng thái loading/guarded/failed
   rõ ràng.
2. Nạp Xu cho thấy hai kênh: PayOS QR động và nạp thủ công có đối soát.
3. PayOS Web chỉ mở form khi Core Bridge công bố dedicated top-up catalog.
   Nếu không, Portal handoff `/naptien` sang Bot đã liên kết.
4. Nạp thủ công luôn handoff `/thucong`; chứng từ chỉ ở Telegram.
5. Sau thao tác Bot, người dùng có thể gửi signed GET làm mới Ví Xu. Đây không
   phải webhook, approval, credit, retry hay mutation.

## Catalog

Pricing/package card cần `available === true`, code dạng opaque bounded và
price field canonical phù hợp trước khi hiển thị. Một dòng thiếu giá không
được biến thành giá `0`; nó được gắn `guarded` và ghi rõ đang chờ Core Bridge.

## Kiểm thử trọng tâm

- malformed wallet/history 2xx không được thành số dư 0 hoặc list rỗng;
- refresh chỉ gọi `GET /wallet` và `GET /wallet/history`, giữ ownership/session
  và bỏ response stale;
- manual top-up không có input/textarea/receipt processing ở Web;
- không có endpoint tạo payment-link hay webhook browser;
- checkout chỉ chấp nhận HTTPS PayOS allowlist đã có.
