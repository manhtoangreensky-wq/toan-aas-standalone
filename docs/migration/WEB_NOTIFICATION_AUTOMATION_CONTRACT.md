# Web Notification & Automation Center Contract

## Mục đích và ranh giới

Notification & Automation Center giúp Web App vẫn có một **Inbox bền vững trong
chính ứng dụng** khi chủ tài khoản không mở trang. Đây là hệ thống materialize
và duy trì urgency metadata Web-native có kiểm soát, không phải agent tự sửa
code hay agent tự hành động ra bên ngoài.

Một bản ghi trong Inbox chỉ có nghĩa là bản ghi đó đã được lưu để chủ tài khoản
xem lại sau khi đăng nhập. Nó **không** có nghĩa Telegram, email, SMS, web push
hay bất kỳ kênh liên lạc nào đã được gửi/nhận.

Module này không được import/call Bot, bridge, provider hay API bên ngoài. Nó
không được tạo/cập nhật PayOS, Xu/wallet, job, output/download, asset delivery,
refund, customer reply, role, secret, code, deployment hoặc Railway restart.
Operations Autopilot là một module Web-native khác; Inbox scheduler không thừa
hưởng quyền hay secret của Operations Autopilot.

## Pha 1: nguồn và hành động được phép

Pha 1 chỉ có một allow-list tường minh; không có `due_at`, `scheduled_for`
hay metadata lịch nào được tự suy diễn thành automation:

    reminder_due_in_app_record
    workboard_schedule_due_in_app_record
    campaign_schedule_due_in_app_record

Nguồn Reminder Web Memory Center là một reminder đang 'active' và đã quá
'next_run_at'. Scheduler chỉ đọc tối thiểu:

    id, account_id, state, revision, next_run_at

Nó không đọc, copy, hash hay ghi vào Inbox title, body, note content, payload,
Telegram ID, email, provider handle hoặc dữ liệu nhạy cảm của reminder. Sau khi
re-read cùng transaction và xác nhận reminder vẫn active/quá hạn, scheduler có
thể tạo tối đa một bản ghi owner-scoped:

    kind=reminder_due
    source_kind=memory_reminder
    source_id=<opaque reminder id>
    source_revision=<current revision>
    occurrence_at=<current next_run_at>
    state=unread

Fingerprint dedupe dùng account, reminder ID, revision và occurrence time;
không chứa nội dung reminder. Một tick lặp, replay hoặc reminder đã đổi sẽ
không tạo bản ghi thứ hai. Scheduler không advance/repeat/pause/resume/complete
reminder và không làm thay đổi source record dưới bất kỳ hình thức nào.

Sau khi một record Inbox đã tồn tại, chỉ có một maintenance Web-native được
allow-list: `state=unread`, `severity=warning` và `occurrence_at` có timestamp
timezone-aware hợp lệ đã quá 24 giờ có thể được nâng thành `severity=urgent`.
Tick re-read chính record bằng ID/account/revision, giữ nguyên state/source/
dedupe, tăng revision, cập nhật `updated_at` và ghi một event
`overdue_escalated` với `actor_account_id=NULL`. Predicate update luôn đòi
đúng `id + account_id + revision + unread + warning`, vì vậy owner vừa read/
dismiss sẽ không bị scheduler ghi đè. Timestamp sai bị skip/fail-closed. Đây
không tạo item mới, không chuyển Reminder/Workboard/Campaign intent và không
gửi Telegram/email/SMS/web push.

Workboard/Campaign chỉ là nguồn khi owner đã tạo một **schedule intent riêng**
với opt-in, confirmation, timezone IANA, normalized UTC trigger,
revision/snapshot binding, limit và idempotency. 'due_at' của Workboard và
'scheduled_for' của Campaign vẫn là metadata local inert, không bao giờ tự tạo
intent. Tick chỉ đọc opaque intent coordinates; source đổi thì chỉ guard intent
để owner xác nhận lại, không tự đổi giờ hay cập nhật Workboard/Campaign.

Campaign detail materializes `kind=campaign_schedule_due` và
`source_kind=campaign_schedule_intent`; Workboard dùng
`kind=workboard_schedule_due` và `source_kind=workboard_schedule_intent`.
Mỗi loại dedupe theo account, opaque intent ID, revision và UTC occurrence.
Chúng dùng chung Notification tick HMAC/lease/flags hiện có, không thêm Cron,
secret hay external-delivery adapter. Contract chi tiết của Campaign nằm tại
[`CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md`](CAMPAIGN_SCHEDULE_INTENT_CONTRACT.md).

## Dữ liệu, ownership và trải nghiệm Inbox

Schema chỉ thêm các bảng Web-owned, additive:

    web_notification_nonces, web_notification_leases,
    web_notification_runs, web_notification_run_steps,
    web_notification_items, web_notification_dedupes,
    web_notification_events

'web_notification_items' chỉ lưu source ID opaque, revision, occurrence,
severity, state, dedupe fingerprint và timestamps. Nó không giữ title/body hay
payload source. 'web_notification_dedupes' là tombstone opaque của occurrence;
nó giữ fingerprint và source coordinates tối thiểu, không giữ nội dung source.
Mọi đọc/mutation Inbox đều đòi signed Web session; item luôn lọc theo
'account_id'. Mark-read và dismiss cần CSRF, optimistic revision, idempotency
key và audit event; dismiss còn cần xác nhận rõ ràng. Urgency maintenance chỉ
chạy bên trong internal signed tick có lease/fence; browser không có action để
ép escalation.

Customer summary không được dùng scheduler receipt toàn cục: nó chỉ có count
owner-scoped và 'last_materialized_at' của chính account đó. Request ID, run
counter, lease, lỗi hoặc metadata materialization của account khác không được
trả qua customer API hay Portal.

Dismissed item được giữ 30 ngày cho audit ngắn hạn rồi event/item liên quan mới
được xóa trong cùng transaction. Tombstone vẫn tồn tại khi reminder còn cùng
active/revision/occurrence để một reminder quá hạn không bị materialize lại sau
cleanup; tombstone tự được xóa khi source advance, đổi revision, complete hoặc
không còn cùng active occurrence. Unread/read item không bị tự xóa.

Receipt/step của scheduler là metadata vận hành có retention riêng, không phải
event ledger vĩnh viễn. Trong một tick đã có lease/fence và còn deadline,
Web có thể xóa tối đa một batch nhỏ run terminal cũ (`completed`, `failed` hoặc
`guarded`) cùng step của nó. Cleanup luôn giữ run hiện tại, run đang lease,
receipt replay `NOTIFY_TICK_REPLAYED`, mọi `web_notification_items` còn trỏ
`created_by_run_id` tới run đó, nonce, dedupe và tất cả source/item state. Lỗi
hoặc config retention sai chỉ bỏ qua cleanup; không được làm tick fail, tạo lại
source hay thay đổi receipt materialization hiện tại.

Customer API hiện có:

    GET  /api/v1/inbox/policy
    GET  /api/v1/inbox/summary
    GET  /api/v1/inbox/items
    POST /api/v1/inbox/items/{id}/read
    POST /api/v1/inbox/items/{id}/dismiss

Portal phải diễn đạt trung thực 'delivery: in_app_record_only', dẫn người dùng
về workspace Web-owned phù hợp để xem nội dung sau owner check, và không dựng thông báo
giả hay claim một kênh external đã delivered.

Mỗi render Portal phải giữ được kết quả signed hydration qua một projection thứ
hai, hẹp hơn: chỉ summary count, status scheduler đã chuẩn hóa, allow-list
source, opaque UUID/revision/state/severity/timestamp của record và pagination
bounded được phép tồn tại trong context. `title`, `body`, `payload`, account
identity, URL/destination từ server, scheduler receipt và mọi claim delivery
external bị bỏ trước khi renderer dùng dữ liệu. Nhờ đó Inbox/Automation không
hiển thị rỗng sau một render kế tiếp, nhưng cũng không trở thành cache nội dung
reminder hay kênh external.

## Feature flags và scheduler identity

| Variable | Default | Mục đích |
| --- | --- | --- |
| 'WEBAPP_NOTIFICATION_CENTER_ENABLED' | 'true' | Cho phép Inbox Web-native đã xác thực. Tắt flag này sẽ fail closed các API Inbox. |
| 'WEBAPP_NOTIFICATION_AUTOMATION_ENABLED' | 'false' | Opt-in riêng để scheduler materialize bản ghi. 'true' không cấp quyền external. |
| 'WEBAPP_NOTIFICATION_TICK_SECRET' | unset | HMAC secret riêng Web/Cron, tối thiểu 32 UTF-8 bytes; không đưa vào browser/log/ticket. |
| 'WEBAPP_NOTIFICATION_TICK_KEY_ID' | 'primary' | Key label '[a-z0-9_-]{1,32}'; implementation hiện chỉ hỗ trợ một active key. |
| 'WEBAPP_NOTIFICATION_MAX_RUN_SECONDS' | '20' | Ngân sách Web/Cron chung, integer từ 1 đến 25 giây. |
| 'WEBAPP_NOTIFICATION_MAX_ACTIONS_PER_RUN' | '20' | Cap Web-only, tối đa 20 materialization hoặc urgency-maintenance write cho mỗi tick. |
| 'WEBAPP_NOTIFICATION_RUN_RETENTION_DAYS' | '30' | Giữ receipt terminal không có provenance item trong 7–3.650 ngày; giá trị sai chỉ tắt prune an toàn. |
| 'WEBAPP_NOTIFICATION_RUN_PRUNE_BATCH_SIZE' | '50' | Xóa tối đa 1–100 run terminal/steps mỗi tick; không quét hoặc xóa toàn bộ history. |
| 'WEBAPP_NOTIFICATION_TOPOLOGY' | unset | Phải chính xác 'sqlite_single_replica' trước khi scheduler chạy trên SQLite hiện tại. |
| 'WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION' | unset | Production-like luôn bắt buộc replica attestation '=1', kể cả khi giá trị là 'false'. Local/test không bắt buộc khi unset/'false'; 'true' chỉ thêm guard nghiêm ngặt cho local/test. |
| 'WEBAPP_NOTIFICATION_TICK_URL' | unset | Cron-only exact HTTPS URL tới endpoint internal bên dưới. |
| 'WEBAPP_NOTIFICATION_TICK_ORIGIN' | unset | Cron-only pure pinned HTTPS origin; không path/query/fragment/userinfo/non-standard port. |
| 'WEBAPP_NOTIFICATION_ALLOW_INSECURE_LOCAL' | 'false' | Chỉ test localhost; luôn tắt trên Railway/production. |

Scheduler dùng identity tách biệt với Operations Autopilot: endpoint, nonce
namespace, lease, request ID, HMAC secret và key ID đều riêng. Không reuse
'WEBAPP_AUTOPILOT_*' variables hoặc 'X-Ops-*' headers.

## Internal tick, HMAC và replay safety

Cron chỉ gọi:

    POST /internal/v1/notifications/tick

với 'Content-Type: application/json' và chính xác một header mỗi loại:

    X-Notify-Timestamp
    X-Notify-Nonce
    X-Notify-Request-Id
    X-Notify-Signature
    X-Notify-Key-Id

Body là canonical UTF-8 JSON (sorted keys, không whitespace):

    {"protocol_version":1,"requested_at":"<X-Notify-Timestamp>","trigger":"railway_cron"}

Signature là HMAC-SHA256 trên:

    POST + "\n" + /internal/v1/notifications/tick + "\n" + timestamp + "\n"
      + nonce + "\n" + request_id + "\n" + key_id + "\n" + SHA256(body)

Timestamp phải timezone-aware, khớp body/header và nằm trong 300 giây; nonce đủ
pattern phải được retain dưới dạng hash trong 600 giây. Body bị chặn ở 8 KiB.
Request ID là UUID và gắn với run receipt. HMAC được verify bằng constant-time
comparison trước khi nonce được persist.

Một request hợp lệ nhưng bị guard (flag tắt, persistent DB/topology/replica
không đạt, hoặc budget run/action không parse/ngoài range) vẫn tiêu thụ nonce
và tạo **minimal guarded receipt**. Nó không lấy lease, không đọc source và
không tạo item. Nhờ đó request đã ký không thể được replay sau khi environment
đổi từ guarded sang enabled. Lease/fencing chỉ được lấy sau preflight thành
công; lost lease không được tiếp tục ghi thêm dữ liệu. Nếu SQLite đang bị lock
đến hết deadline của tick, Web trả `NOTIFY_TICK_DEADLINE_REACHED` mà không chờ
30 giây theo timeout transaction chung; khi lock ngăn mọi write thì không thể
an toàn để persist nonce/receipt và Cron có thể thử lại. Nếu tick đã lấy lease,
lease vẫn được giữ đến expiry để retry không materialize bản ghi trùng.

Mọi read/write của scheduler dùng phần thời gian còn lại của
`WEBAPP_NOTIFICATION_MAX_RUN_SECONDS` (1–25 giây), có reserve nhỏ để đóng
receipt. SQLite busy/lock được fail-closed thành guarded state, không được
fallback sang transaction Web thông thường. Receipt failure muộn vẫn giữ lại
`action_count`/`candidate_count` phản ánh materialization hoặc urgency
maintenance đã thực hiện trước khi exception; counters không là tuyên bố
delivery external.

## SQLite topology và Railway Cron

Nonce, lease, run và dedupe phải sống qua restart. Trong production,
'WEBAPP_SESSION_DB_PATH' resolved phải nằm trong persistent Railway volume;
scheduler fail closed nếu điều này không được xác minh. Với SQLite hiện tại,
Web service phải chạy đúng **một replica**:

    WEBAPP_NOTIFICATION_TOPOLOGY=sqlite_single_replica
    RAILWAY_REPLICA_COUNT=1

Khi 'APP_ENV', 'ENVIRONMENT' hoặc 'RAILWAY_ENVIRONMENT' là production/prod/live,
scheduler **luôn** chỉ chạy khi có ít nhất một attestation hợp lệ '=1' từ
'RAILWAY_REPLICA_COUNT', 'RAILWAY_REPLICAS' hoặc 'WEBAPP_REPLICA_COUNT'; nếu
nhiều biến cùng được khai báo thì **mọi** giá trị phải là số '1'. Giá trị thiếu,
không phải số hoặc khác 1 đều trả guarded receipt; topology string không tự
chứng minh được state SQLite an toàn. `WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION=false`
không thể bypass production guard. Local/test có thể không khai báo replica
metadata trừ khi override `true` yêu cầu attestation.

Không được scale ngang cho tới khi toàn bộ nonce/lease/idempotency chuyển sang
một transactional database dùng chung như PostgreSQL.

Cron phải là service short-lived độc lập, gọi rồi thoát bằng:

    python scripts/notifications/run_notification_tick.py

Runner pin origin, tắt proxy, reject redirect, giới hạn response và chỉ nhận
receipt JSON khớp request ID. Cron không mount SQLite volume, không import app
hay Bot, không giữ 'WEB_SESSION_SECRET', DB path, Bot/PayOS/wallet/provider
credentials. Nó chỉ nhận các 'WEBAPP_NOTIFICATION_TICK_*' cần thiết và
'WEBAPP_NOTIFICATION_MAX_RUN_SECONDS'.

### Thiết lập Railway theo từng service và tách quyền vận hành

Tạo **một Cron service riêng**, không đổi start command của Web service. Cron
chạy `python scripts/notifications/run_notification_tick.py` theo lịch tối
thiểu 5 phút; URL là HTTPS production chính xác của endpoint, origin là origin
thuần tương ứng. Web service giữ volume, topology/replica attestation, feature
flag và endpoint verify; Cron service chỉ nhận
`WEBAPP_NOTIFICATION_TICK_URL`, `WEBAPP_NOTIFICATION_TICK_ORIGIN`,
`WEBAPP_NOTIFICATION_TICK_SECRET`, `WEBAPP_NOTIFICATION_TICK_KEY_ID` và
`WEBAPP_NOTIFICATION_MAX_RUN_SECONDS`. Không copy `WEB_SESSION_SECRET`, DB
path, volume, Bot, PayOS, wallet hay provider credential sang Cron.

Trình tự operator: deploy Web với automation `false` → kiểm tra single-replica
và persistent volume → cấu hình Cron riêng, secret và lịch → bật flag tại **Web
service** → xem receipt/log opaque. Rollback: đặt flag Web thành `false` trước,
sau đó disable Cron schedule; không xóa nonce/run/item/audit rows hoặc đổi
secret vội trong lúc xử lý sự cố. Người quản lý schedule/log Cron không được
tự ý đổi Web volume, replica, feature flag hay credential thanh toán/provider;
nếu Railway role là project-wide thì quy trình review/release phải tạo sự phân
tách này, không giả định có RBAC theo service.

Railway Cron có đặc tính UTC, tối thiểu 5 phút, không đảm bảo minute-exact và
skip schedule nếu Cron trước còn chạy; xem
[Railway Cron Jobs](https://docs.railway.com/cron-jobs). Tạo/enable Cron, thay
schedule, cấp secret, scale replica hay deploy vẫn là thao tác release tường
minh; không bao giờ là side effect của merge code hoặc Inbox tick.

## Enablement và rollback an toàn

1. Deploy với 'WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=false'; Inbox UI/API có
   thể hiện policy nhưng scheduler chưa materialize record nào.
2. Xác nhận Web session DB nằm trên persistent volume và Web chỉ có một
   replica; sau đó đặt 'WEBAPP_NOTIFICATION_TOPOLOGY=sqlite_single_replica'.
   Trên production-like, cấp một replica attestation hợp lệ '=1' và giữ
   'WEBAPP_NOTIFICATION_REQUIRE_REPLICA_ATTESTATION' unset/true.
3. Cấu hình tick URL/origin, secret và key ID tách biệt cho Web/Cron. Cron chỉ
   được dùng variables tối thiểu nêu trên.
4. Bật 'WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=true', quan sát receipt
   'guarded'/'completed' và Inbox owner-scoped trước khi tăng phạm vi source.

Rollback: đặt 'WEBAPP_NOTIFICATION_AUTOMATION_ENABLED=false' trước, rồi disable
Cron. Không xóa nonce/run/item/audit rows để rollback. Secret/key rotation phải
ở planned window vì bản hiện tại chưa có dual-key grace period.

## Các giới hạn cố ý

Inbox không phải push delivery, case auto-resolver hay self-healing executor.
Khi không có người vận hành, nó có thể giữ lại một record Web-native an toàn để
người đúng chủ tài khoản xem sau; nó không tự trả lời khiếu nại, tự cấp tiền,
tự retry job, tự thay provider, tự deploy hoặc tự sửa code. Mỗi năng lực mới
với external effect cần một adapter/capability riêng, consent, rate limit,
human override, delivery receipt, least privilege, audit và test trước khi
được claim là automation.
