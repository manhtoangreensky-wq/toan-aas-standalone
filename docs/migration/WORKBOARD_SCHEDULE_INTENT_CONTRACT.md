# Workboard Schedule Intent Contract

## Mục đích và ranh giới

`Workboard Schedule Intent` là lịch nhắc riêng tư do chính chủ sở hữu Workboard
tạo. Đây là một intent có xác nhận, không phải cron của trình duyệt và không phải
lịch Campaign. Khi đến hạn, hệ thống chỉ materialize một bản ghi Inbox private
trong Web.

Module này không gọi Telegram, email, push notification, Bot, bridge, provider,
PayOS, wallet hoặc job runtime. Không có cơ chế tự sửa dữ liệu, tự dời giờ nhắc,
hay tự gửi lại sau khi nguồn đã đổi.

## Dữ liệu tối thiểu

Bảng additive `web_workboard_schedule_intents` lưu:

- `account_id`, `item_id`, `created_by_account_id` để giới hạn ownership.
- `source_revision` và `source_snapshot_hash` của immutable Workboard version
  được người dùng xác nhận.
- `trigger_local_at`, IANA `timezone` và `trigger_at` đã chuẩn hoá UTC.
- state/revision/audit timestamp cần thiết cho `active`, `dispatched`,
  `guarded` và `cancelled`.

Bảng intent **không** lưu title, description, body hoặc payload snapshot của thẻ
Workboard. Nội dung nguồn chỉ được đọc ngắn hạn để tính canonical hash tại thời
điểm tạo, reconfirm và dispatch.

Mỗi intent active chỉ có một bản ghi cho cùng item, source revision và UTC
trigger. Các giới hạn số lượng theo account/item bảo vệ Inbox và database khỏi
lạm dụng.

## Hợp đồng API

Tất cả endpoint nằm dưới `/api/v1/workboard/items/{item_id}` và chỉ hoạt động
khi Workboard feature đang được bật:

| Method | Route | Điều kiện |
| --- | --- | --- |
| `GET` | `/schedule-intents` | session owner/admin được server resolve |
| `POST` | `/schedule-intents` | CSRF, `opt_in: true`, `confirm: true`, current item revision |
| `POST` | `/schedule-intents/{intent_id}/cancel` | CSRF, explicit confirmation, expected intent revision |
| `POST` | `/schedule-intents/{intent_id}/reconfirm` | CSRF, explicit confirmation, current item revision |

Các POST sử dụng cùng idempotency boundary của Workboard. API không nhận quyền
từ browser; account ID và role được lấy từ signed web session. Mọi lookup chi tiết
và write action đều tái kiểm tra ownership/role phía server.

## Hợp đồng thời gian

Người dùng nhập thời điểm local ISO (`YYYY-MM-DDTHH:mm`) và IANA timezone. Server
phải:

1. kiểm tra timezone bằng `zoneinfo` và từ chối local time không tồn tại hoặc mơ
   hồ ở DST;
2. chuẩn hoá thành UTC `trigger_at`;
3. yêu cầu thời điểm nằm ngoài lead time tối thiểu và trong cửa sổ tối đa;
4. giữ nguyên trigger đã xác nhận khi intent bị guarded.

Một reconfirm chỉ rebind source revision/snapshot sau xác nhận rõ ràng; nó không
được tự ý đổi giờ nhắc.

## Vòng đời và dispatch

```text
owner confirms source + time
            |
         active
            |
  signed existing notification tick
      | source/version/hash exact        | mismatch, inaccessible, disabled, invalid
      v                                  v
  dispatched + one private Inbox       guarded (no delivery)
            ^                                  |
            |        owner reconfirms          |
            +----------------------------------+

owner cancels -> cancelled
```

Tick dùng hạ tầng notification tick đã có, xác thực như hiện hữu và chạy theo
candidate window có bounded limit. Không thêm browser polling hoặc self-healing
cron. Trước khi ghi Inbox, dispatcher kiểm tra đầy đủ account/item ownership,
current revision và canonical immutable snapshot hash. Bất kỳ sai lệch nào đều
chuyển intent sang `guarded` và không gửi gì.

Dispatch sử dụng dedupe fingerprint trên intent/revision/trigger. Khi retry hoặc
tick chạy trùng, hệ thống chỉ tạo tối đa một `web_notification_items` record với:

- `kind: workboard_schedule_due`
- `source_kind: workboard_schedule_intent`
- source ID opaque là schedule intent ID

Không có notification ngoài Web và không có thay đổi vào Workboard item/version
ở bước dispatch.

## Riêng tư và UI

Inbox chỉ hiển thị copy an toàn, không lộ nội dung Workboard qua notification
metadata. Trang Workboard là nơi người dùng xem nội dung sau khi server kiểm tra
ownership. UI nói rõ đây là thông báo Inbox riêng tư; không hứa Telegram/email/
push, không tạo success giả và hiển thị `guarded` cùng yêu cầu reconfirm khi
nguồn thay đổi.

Nếu signed API của riêng `schedule-intents` không trả được boundary hợp lệ,
Portal vẫn có thể hiển thị Workboard item/history đã được xác minh độc lập,
nhưng phải đặt phần lịch thành `guarded`: không dựng trạng thái “chưa có lịch”,
không giữ dữ liệu cũ, và khóa create/cancel/reconfirm cho đến khi đọc lại thành
`read_only`. Lỗi đọc lịch không được biến thành lỗi toàn bộ Workboard detail.

## Kiểm chứng tối thiểu

Focused checks bảo vệ các invariant chính:

- owner opt-in + CSRF/idempotency, UTC normalization và Inbox materialization
  đúng một lần;
- source revision/snapshot đổi thì guard, không delivery và không write ngược
  Workboard;
- reconfirm là hành động explicit, giữ trigger, và chỉ cập nhật source binding;
- static import boundary không kéo Bot, bridge, payment hay external notifier vào
  module Workboard schedule.
