# Workspace Command Center — `/dashboard`

## Mục đích

`/dashboard` là điểm vào ứng dụng cho signed TOAN AAS Web account. Bản nâng
cấp này không tạo một dashboard mới hay một API mới: nó tổ chức lại màn hình
hiện có thành các lane rõ authority để người dùng không nhầm dữ liệu Web-owned
với dữ liệu canonical mà Bot/Core Bridge xác minh.

| Lane | Dữ liệu | Authority | Không làm |
| --- | --- | --- | --- |
| Continue Web work | Project và Workspace Draft | Signed Web account, owner-scoped | Không gọi Bot, provider, wallet/Xu, PayOS, job hay delivery. |
| Account & Security | Tài khoản, bảo mật và lựa chọn liên kết | Signed Web account | Không nhận Telegram ID, role hoặc permission từ browser. |
| Canonical integration | wallet, jobs, assets, tickets, feature readiness | Existing Core Bridge read models | Không cộng Xu, tạo job, tạo output/delivery URL, charge, refund, provider call hay webhook. |
| Start | Studio/route đã đăng ký | Route đích tự kiểm tra | Không tự tạo workflow, job, payment hoặc dữ liệu provider. |

Không có Bot source, `bot.py`, PayOS engine, wallet ledger, webhook, provider
production hay Railway configuration nào bị thay đổi trong module này.

## Route và API giữ nguyên

```text
GET /dashboard

GET /api/v1/wallet
GET /api/v1/jobs
GET /api/v1/assets
GET /api/v1/features/status
GET /api/v1/support/tickets
```

Các API canonical ở trên vẫn được đọc qua client đã có signed session,
request epoch và owner/authority checks. Không có browser API mới. Không có
database table/migration mới và không có request write từ Command Center.

## Lifecycle an toàn

`dashboardReadState` là projection presentation-only với đúng bốn giá trị:

```text
guarded → loading → ready
                  ↘ failed
```

- `guarded`: account chưa có canonical integration do server xác nhận.
- `loading`: ngay trước signed canonical read, Portal xóa `wallet`, `jobs`,
  `assets`, `tickets` và `readiness` của Dashboard trong memory.
- `ready`: chỉ sau khi năm read models trả về envelope **và schema hợp lệ**
  trong request epoch hiện tại; wallet phải có các Xu integer canonical và
  flag plan, mỗi list phải có `items` cùng identity/lifecycle hợp lệ, readiness
  phải có object `features`. HTTP `200`/`ok: true` nhưng thiếu hoặc sai cấu
  trúc vẫn là `failed`, không được diễn giải thành số 0 hay list rỗng. Khi đó
  mới hiển thị số Xu, công việc, asset metadata và ticket.
- `failed`: mọi canonical projection của Dashboard vẫn rỗng; user thấy nút
  **Thử lại**, không thấy số 0, output, queue hay ticket được suy đoán.

Projects/Drafts Web-native không bị xóa bởi canonical failure; chúng có reader
owner-scoped và lifecycle riêng. Retry dùng capability
`dashboard-refresh`, chỉ cho signed account có canonical integration; đây là
GET refresh, không cần và không tạo write authority.

Đặc biệt, `GET /api/v1/support/tickets` không còn bị biến thành mảng rỗng khi
lỗi. Nếu một canonical read không xác minh được, toàn bộ canonical lane là
`failed`; điều này tránh việc thông báo “không có ticket” hoặc “không có việc”
khi thực tế chỉ là lỗi kết nối.

## Bảo mật, quyền sở hữu và PWA

- Client không giữ cache/localStorage cho wallet, job, asset, ticket hoặc
  read state canonical; Portal normalizer chỉ giữ bounded presentation state
  hiện tại.
- Request epoch và signed session epoch chặn response cũ khi đổi account,
  route hoặc bridge availability thay đổi.
- **Service Worker** (`service-worker.js`) đưa `/dashboard` vào `PRIVATE_PATH_PREFIXES`. Nó không
  nằm trong public shell/offline fallback; không có dashboard của account cũ
  sau logout, switch account hoặc deploy.
- Button retry không thể bỏ qua server authorization; UI capability chỉ là
  hint và mỗi signed API read vẫn được server/Core Bridge kiểm tra.
- Dashboard không tuyên bố output thành công; asset chỉ hiển thị metadata và
  delivery vẫn phụ thuộc URL ký/ownership contract ở Asset Center.

## UI/UX

Command Center dùng surface slate/teal phẳng, token-driven, không thêm
landing hero/gradient cho scope mới. Nó giữ contrast, visible focus từ hệ
thống Portal, control mobile tối thiểu 44px, layout một cột ở mobile và
`prefers-reduced-motion`. Các state `loading`, `failed` và `guarded` đều có
text giải thích thay vì chỉ dùng màu.

## Non-goals và disposition Bot

Bot command/callback về wallet, job, assets, ticket và provider vẫn thuộc Bot
canonical. Web chỉ đọc projection đã có qua bridge sau signed authorization.
Không có Telegram message/callback, notification delivery, schedule executor,
auto-fix runtime, PayOS manual top-up/refund, ledger update, charge/retry job
hay provider smoke test trong contract này.

## Kiểm tra trọng điểm

- static contract: route `/dashboard`, read lifecycle, normalizer và retry;
- fail-closed: clear projection trước request, reject malformed `200` payload
  và clear trong catch;
- no-stale/no-fake: canonical lane không render khi không `ready`;
- PWA: `/dashboard` private, không phải shell;
- UI: lane authority, mobile 44px và reduced motion.
