# R218-10/11/12/13 — Nghiệm thu, motion cuối, delivery và hàng đợi kỹ thuật

## R218-10 — Toàn bộ UI/UX

Input: inventory B01–B34 + control ledger của mỗi sản phẩm.
Kết quả: từng control có trạng thái evidence, nguồn file/commit/test/browser, không
đánh dấu cả sản phẩm đạt từ số test hoặc số route.

- So root/submenu/catalog với Web disposition: mapped/duplicate/legacy/admin-only/T0.
- Unclassified controls phải bằng 0 trong inventory đã chốt; mục chưa kiểm giữ OPEN.
- Renderer tests: local selection, data/focus preservation, error/retry, quoted values,
  output readiness và role visibility. Không xóa assertion do code chưa đáp ứng.
- Browser: VI/EN/ZH × light/dark × 375/390/768/1440. Shell/form thêm 320/414/1024.
- Case: default/selected/empty/loading/error/stale/forbidden/needs-review/completed;
  locale UI không dịch user data; account replacement không lộ dữ liệu cũ.
- Đo font/touch/contrast/overflow. Screenshot có context; AX có label/heading/focus.
- QA DB fixture đã được phép ở phiên này: synthetic account/record, không production.
  Provider/financial/publish actions dùng test seams, không gửi thực tế.

## R218-11 — Motion làm cuối

Các control/config/result ổn định trước khi sửa animation. Không đổi duration để
che double render hoặc layout shift.

| ID | Probe | Điều kiện đạt |
|---|---|---|
| MO-01 | Auth entry + async providers resolve ở 200/500/900ms | Animation không bị cắt/restart; provider space reserve |
| MO-02 | Route enter/exit/same-route hydration | Draft/focus/scroll không reset; cleanup RAF/observer/timer/listener |
| MO-03 | Page transitions | Transform/opacity; UI micro 150–300ms; exit nhanh hơn entry |
| MO-04 | Scroll reveal | Không left/top/layout per frame, không transition lag khi scrub; không vùng trống |
| MO-05 | Reduced motion trước/trong animation | Dừng chuyển động, content và controls còn đọc/dùng được |
| MO-06 | Loading/large media/list | Skeleton theo vùng, reserve size, responsive; không spinner khóa mọi view |
| MO-07 | Trace desktop/mobile | CLS <0.10, LCP ≤2.5s, INP ≤200ms khi phép đo hợp lệ |
| MO-08 | User-visible recording | Clip thao tác/scroll cho thấy hiệu ứng mượt trong scope; không suy FPS từ screenshot |

Report trace phải ghi device/viewport/browser/route/runtime/cache/throttle/sample.
Synthetic event latency không tự được gọi field INP. Thiếu metric thì UNKNOWN kèm
điều kiện cần, không tự PASS.

## R218-12 — Delivery/live

Trước merge: review diff từ remote base mới, required CI trên HEAD, protected files.
Trước deploy: đủ quyền Owner cho đúng PR/phạm vi, rollback path, service/runtime target.
Sau deploy: expected revision, service/readiness, browser scope đúng candidate.
Không suy MERGED=DEPLOYED=LIVE. Không tự đăng xuất GitHub/login hiện có.

Production UI probes chỉ đọc/navigation/keyboard/options nếu không mutation.
Không tạo provider job/publish/approve hoặc nạp tiền để chứng minh UI.
Local preview != isolated authenticated QA != production live.

Output: URL/route/time/SHA/viewport/locale/theme/DOM/AX/screenshot/console/network,
known limitations và checklist IDs đóng/mở. Hết UI/motion báo cáo, đợi lệnh phần kỹ thuật.

## R218-13 — Technical backlog, chưa triển khai

| ID | Gap | Spec backend tương lai phải có |
|---|---|---|
| T-01 | Canonical capability/catalog/DTO | Authority, versioning, supported values, backward compatibility |
| T-02 | Voice Vault + SubDub/Video | Owner profile/readiness/consent, return context, no re-clone |
| T-03 | Speaker policies/mapping | Auto 2/Multi 3–8/Smart Multi khác nhau, map/override/readiness/fail-closed |
| T-04 | Upload/quote/confirm/job/status | Source ownership, idempotency, expiry, same-job recovery, cost gate |
| T-05 | Outputs/delivery | Validate SRT/VTT/audio/image/MP4; download ready, receipt, partial/failure semantics |
| T-06 | Music 2 outputs/editor | Current contract and actual delivery count; không giả editor từ guard |
| T-07 | Video AI/manual/long | Provider capability/worker budgets/render/artifact criteria, locked controls |
| T-08 | AutoPost channels/publish/ads | OAuth secrets, targets, receipts, dedupe, explicit financial authority |
| T-09 | Admin linking/server permission | Customer request/job/report audit, RBAC/ABAC enforcement, no forged refs |
| T-10 | Manual approval/wallet/PayOS | Owner gate riêng, canonical ledger/idempotency/audit/rollback |

Mỗi T item: trigger → validate → authorize → explicit confirm → side effect →
artifact validate → report; request/job/provider task IDs tách; lỗi/Back/retry rõ.
Không mở T0 chỉ để hoàn tất checkbox UI. Không thay đổi secret/global rules.
