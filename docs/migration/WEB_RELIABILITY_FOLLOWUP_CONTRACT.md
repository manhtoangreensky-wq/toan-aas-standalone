# Web Reliability Follow-up Contract

## Mục đích

Reliability Follow-up giúp đội vận hành không bỏ sót lỗi Web lặp lại hoặc
complaint triage cần người phụ trách khi không có người trực. Đây là một hàng
chờ **metadata nội bộ đã được làm sạch**, không phải log viewer, auto-repair,
agent tự thay đổi hệ thống, hay kênh liên hệ khách hàng.

Không có phần nào của module được phép gọi Bot/Core Bridge, provider, Xu,
PayOS, job, delivery, Telegram, email, SMS, web push, deploy/restart Railway,
thay đổi ENV/secret/role hoặc sửa mã nguồn.

## Feature gate

| Biến Web service | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `WEBAPP_AUTOPILOT_ENABLED` | `false` | Mở Operations control plane đã ký. |
| `WEBAPP_AUTOPILOT_SAFE_REMEDIATION_ENABLED` | `false` | Cho phép scheduler materialize metadata follow-up cục bộ. |
| `WEBAPP_RELIABILITY_FOLLOWUP_ENABLED` | `false` | Mở Reliability read/write cho staff và intake 5xx đã allow-list. |
| `WEBAPP_AUTOPILOT_INCIDENT_SECRET` | unset | Web-only HMAC secret, tối thiểu 32 UTF-8 bytes; không đưa vào Cron/browser/log. |
| `WEBAPP_RELIABILITY_SIGNAL_THRESHOLD` | `3` | Số occurrence tối thiểu để scheduler tạo/refresh follow-up; chỉ nhận số nguyên `1..1000`. |
| `WEBAPP_RELIABILITY_CAPTURE_MIN_INTERVAL_MS` | `250` | Giới hạn ghi process-local theo route family/bucket, `0..5000`; chỉ dùng để bảo vệ response 5xx, không phải một claim về số lỗi chính xác. |

Intake 5xx cần Autopilot + Reliability flag + incident secret + threshold
hợp lệ. Scheduler materialization cần thêm safe-remediation và toàn bộ
Operations preflight (persistent SQLite, topology/replica, HMAC/nonce/lease)
đã đạt. `reliability_config_ready` chỉ mô tả key/threshold của module này;
nó không tuyên bố Railway Cron hay scheduler tổng thể đang chạy.

Một giá trị scheduler budget sai sẽ trả signed `guarded` receipt HTTP 200 và
consume nonce. Điều này để Railway không retry cùng một request rồi gửi mail
lỗi lặp. Không có deploy, restart, config mutation hay retry external nào
được thực hiện để “tự sửa”.

## Data minimization và retention

Chỉ `5xx` bất ngờ từ allow-list Web-native private API có thể tạo signal. Mỗi
signal lưu nhãn route family cố định, code `unexpected_5xx`, số occurrence và
timestamp UTC. Nó không đọc/lưu raw URL, path động, query, body, header,
cookie, IP, session, auth token, exception text hay stack trace.

`web_ops_runtime_signal_buckets` là bucket UTC 5 phút và được prune có giới
hạn sau 30 ngày bởi scheduler. `web_ops_runtime_signal_totals` giữ aggregate
monotonic theo route family, để một lỗi xuất hiện ở bucket sau vẫn re-open
được follow-up đã resolved. Khi count đạt cap an toàn, request path không ghi
thêm row/revision.

Follow-up complaint giữ private support-case reference để scheduler biết case
nào đã terminal, stale hoặc không còn actionable và chỉ `supersede` metadata
local. Một case Web Support thông thường có semantic customer-waiting clock
thiếu, malformed hoặc future được triage là `unverified` cũng có thể tạo đúng
một follow-up `medium` cho operator: đây là nhắc staff kiểm tra metadata, **không**
phải SLA breach, incident, cảnh báo khách hay kết luận sự cố. Financial,
external-dependency và unclassified vẫn đi theo `awaiting_operator` hiện có.
Nó **không** lưu account ID của khách và API staff list cũng không trả source
ID, fingerprint, account ID, raw route hay diagnostic payload.

Một `support_triage` follow-up active chỉ còn actionable khi Support case,
triage và follow-up cùng một `source_revision`, case chưa terminal, disposition
vẫn `awaiting_operator` hoặc SLA là `at_risk` / `breached` / `unverified`, và
required role còn khớp policy. Nếu bất kỳ điều kiện nào lệch, scheduler chỉ
`supersede` record local; không thay đổi case, triage, message, phân công hay
SLA. Chỉ triage mới hơn, đã được đối chiếu với case hiện tại, mới có thể mở lại
record `superseded`.

## Lifecycle và quyền

```text
runtime signal / support triage
  -> open -> acknowledged -> resolved
                         -> open (chỉ khi source revision mới)
support source terminal/stale/non-actionable -> superseded
superseded support triage -> open (chỉ khi triage mới hơn và còn actionable)
```

`unverified` không xuất hiện như một incident SLA. Nó chỉ là một lý do
actionable cho follow-up cục bộ khi case vẫn active; một customer-waiting event
genuine ở revision mới có thể đưa triage về `within_target`, khiến follow-up
cũ bị `supersede` thay vì tự đóng case hay tự báo khách.

- `support_operator` chỉ có thể cập nhật follow-up explicit `operator`.
- `support_manager`/Web admin có thể cập nhật cả record yêu cầu manager.
- Một handoff Support Desk chỉ có thể được trả cho staff có role phù hợp,
  follow-up active và source còn fresh. API trả duy nhất local route
  `/admin/support/{uuid}`; browser không gửi/đặt case ID hoặc redirect URL.
  Handoff không copy narrative khách, không mutate case và chỉ append audit
  access trail với follow-up ID opaque.
- Mọi write yêu cầu signed Web session, server-side role, CSRF, explicit
  confirmation, optimistic revision, idempotency key và audit event.
- `acknowledge`, `resolve`, `reopen` chỉ thay đổi metadata local; “resolved”
  không có nghĩa là customer, provider, code hay Railway đã được sửa.

## API và UI

```text
GET  /api/v1/operations/admin/reliability/summary
GET  /api/v1/operations/admin/followups?state=&severity=&limit=&offset=
GET  /api/v1/operations/admin/followups/{id}/handoff
POST /api/v1/operations/admin/followups/{id}/acknowledge
POST /api/v1/operations/admin/followups/{id}/resolve
POST /api/v1/operations/admin/followups/{id}/reopen
UI   /admin/reliability
```

`/admin/reliability` là Web-native staff route; nó không fallback sang generic
Bot admin/bridge. Service Worker không cache API hoặc route này. UI chỉ dùng
pull-to-refresh, không chạy scheduler trong browser và không hiển thị một
claim “đã tự sửa”. Nút `Mở Support Desk` chỉ xuất hiện với complaint triage
active; trước khi navigation browser luôn gọi handoff route server-side và
chỉ nhận route đã được strict-validate.

Hàng chờ có hai bộ lọc enum được server kiểm tra: `state` là `all`, `open`,
`acknowledged`, `resolved` hoặc `superseded`; `severity` là `all`, `low`,
`medium`, `high` hoặc `critical`. Lọc được giữ khi phân trang/làm mới trong
page-memory và có nút **Xóa lọc**. Không có filter theo source kind, source
reference, account, route, ID, nội dung, raw log hay sort; browser không lưu
giá trị lọc vào transient form state.

## Không nằm trong pha này

- Tự patch code, Git commit/merge, Railway deploy/restart hoặc đổi biến;
- auto refund/top-up/PayOS/wallet operation;
- provider/Bot/job retry, output delivery hoặc feature freeze;
- Telegram/email/SMS/web-push/customer reply;
- đọc raw log hoặc chẩn đoán stack trace trong Portal.

Mọi năng lực trên cần contract, authority, audit, rollback và phê duyệt riêng.
