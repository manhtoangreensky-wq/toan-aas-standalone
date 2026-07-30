# Sổ quyết định nghiên cứu hậu UI/UX — Media Product & Service

**Trạng thái:** Tài liệu nghiên cứu đã được sàng lọc. Không phải là quyền mở
runtime, provider, payment, Bot, webhook hay deploy.

**Thứ tự bắt buộc:** Hoàn tất và nghiệm thu UI/UX customer + Admin ERP trên
desktop/mobile trước; sau đó chọn **một** capability Web-native, có owner
matrix và fixture-only plan. Không dùng nghiên cứu này để mở rộng phạm vi của
PR UI hiện tại.

## Nguồn đã đọc và cách sử dụng

Ba tài liệu do product owner cung cấp là đầu vào kiến thức:

1. *Kiến trúc và mô hình vận hành cho sản phẩm chỉnh sửa video tích hợp vào
   chat-bot*;
2. *Quy trình tốt nhất cho TOAN AAS là “Shared Semantic Master DAG”*; và
3. *Kiến trúc sản xuất cho Local Video Editing và Product Video nhiều cảnh*.

Chúng được đối chiếu với các decision record hiện có:

- [`POST_UI_UX_MEDIA_ORCHESTRATION_RESEARCH_TRIAGE.md`](POST_UI_UX_MEDIA_ORCHESTRATION_RESEARCH_TRIAGE.md)
- [`POST_UI_UX_MEDIA_PLATFORM_RESEARCH_TRIAGE.md`](POST_UI_UX_MEDIA_PLATFORM_RESEARCH_TRIAGE.md)
- [`POST_UI_UX_PRODUCT_SERVICE_RESEARCH_TRIAGE.md`](POST_UI_UX_PRODUCT_SERVICE_RESEARCH_TRIAGE.md)

Nguyên tắc quyết định: chỉ nhận một đề xuất khi nó tạo ra kết quả thật cho
khách hàng hoặc vận hành, có authority rõ, fail/retry trung thực, có fixture
và rollback; không nhận một stack hay một flow chỉ vì nó “trông đầy đủ”.

## Quyết định đã sàng lọc

| Đầu vào nghiên cứu | Quyết định | Lý do và điều kiện áp dụng |
| --- | --- | --- |
| Một `approved snapshot` bất biến, lifecycle monotonic và evidence/receipt sau delivery | **Nhận sau UI/UX** | Đây là contract trung lập nền tảng: refresh, retry hoặc restart không được đổi asset, scene, output policy hay quyết định đã xác nhận. `completed` chỉ có sau validation và owner-checked delivery. |
| Local deterministic media lane, allow-list, `ffprobe` + full decode | **Nhận cho lane đầu tiên** | Một output nhỏ, có fixture thật, dễ chứng minh hơn provider-first hoặc một “studio” rộng. Không tạo engine thứ hai; chỉ dùng runtime Web-native đã được chứng minh. |
| Shared Semantic Master, Translation Master, `segment_id` ổn định và offset theo timeline gốc | **Pilot sau local lane** | Có giá trị khi cùng một nguồn thực sự fan-out sang subtitle, dịch, dub hoặc combo. Pilot chỉ ở fixture/approved-artifact shadow/replay, không public route, provider, settlement hoặc delivery. |
| Subtitle copy tách dub copy; profile theo ngôn ngữ/đích xuất; QC có ngữ cảnh | **Nhận như invariant V2** | Tránh dịch lặp, drift giữa subtitle/dub, VAD làm lệch timestamp và “một CPS/LUFS dùng cho mọi ngôn ngữ”. Chưa có nghĩa là công khai hứa chất lượng engine chưa kiểm chứng. |
| Per-stage idempotency, durable manifest và exclusive recovery lease | **Điều kiện** | Chỉ thêm khi job thật sự dài hơn request hoặc cần restart/concurrency recovery. Mọi confirm/delivery/receipt trùng lặp phải trả lại outcome cũ, không tạo side effect mới. |
| Queue, Redis/RabbitMQ, object storage, real-time transport | **Defer theo số liệu** | Chỉ chọn sau authority, retention, chi phí, load và recovery evidence. Không cài Kafka/Kubernetes/WebRTC/GStreamer chỉ để “đủ kiến trúc”. |
| Provider adapter, paid job, webhook/poll recovery | **Defer cuối cùng** | Cần user confirmation, saved external task ID, signature/replay guard, monotonic terminal state, cost guard và recovery chỉ poll/retrieve task đã chấp nhận. Không auto resubmit khi `ACCEPTANCE_UNKNOWN`. |
| Telegram callback/backstack, raw Telegram ID, Bot Xu/PayOS/webhook hoặc historical job clone | **Từ chối cho Web/App** | Giữ abstract product facts, không copy UI state hay tạo ledger/webhook authority thứ hai. Bot-owned identity, Xu, PayOS, provider và historical records tiếp tục đứng riêng. |

## Architecture boundary sau khi UI/UX được nghiệm thu

```mermaid
flowchart LR
  CW[Customer Web workspace] --> API[Owner-scoped product API]
  MA[Customer mobile companion] --> API
  ERP[Admin ERP] --> OPS[Redacted support and audit policy]
  API --> SNAP[Immutable approved snapshot]
  SNAP --> LANE[One proven local lane]
  LANE --> VALIDATE[Inspect + full decode]
  VALIDATE --> DELIVERY[Owner-checked temporary delivery]
  DELIVERY --> RECEIPT[Evidence receipt]
  BOT[Existing Bot-owned records] --> ADAPTER[Reviewed read/adapter boundary]
  ADAPTER --> API
  DAG[Semantic DAG V2] -. fixture shadow/replay only .-> API
  PROVIDER[Optional paid provider] -. separate reviewed gate .-> API
```

Đây là target boundary, không phải xác nhận rằng các service đã tồn tại.

## Candidate nhỏ nhất để bắt đầu sau UI/UX

Candidate ưu tiên là **một export MP4 một nguồn với preset cố định**, ví dụ
reframe asset riêng tư sang `9:16` bằng scale/pad bounded. Chỉ chọn candidate
này nếu capability tương đương đã có trong Web-native allow-list; nếu không,
chọn operation single-input gần nhất đã được chứng minh thay vì tạo renderer
mới để biện minh cho roadmap.

Lane này không có scene ordering, transition/audio mixing, provider, payment,
Bot bridge hay ledger mới. Tuy vậy, nó vẫn chứng minh được toàn bộ contract:

1. Intake owner-checked và fingerprint đầu vào;
2. Review/confirm tạo approved snapshot;
3. Execution allow-listed với fixture thật;
4. `ffprobe` **và** full decode trước delivery;
5. Download tạm thời kiểm tra owner lần nữa; và
6. Receipt trung thực, không suy ra hay copy chính sách `0 Xu` từ Bot.

## PR đầu tiên của Semantic DAG khi đã đủ điều kiện

PR đầu tiên không chạy media. Nó chỉ thêm versioned schema và legal replay
fixture cho `SourceSemanticMaster`, `TranslationMaster`, derivative copy và
stage manifest; test phải chứng minh stable IDs, offsets không đổi, subtitle
và dub tách biệt, lineage/QC đủ và không có side effect. Một PR shadow/replay
riêng chỉ được tính tiếp sau owner review.

## Guardrails không được nới lỏng

- Không đổi `bot.py`, LocalVideoStudio, provider, PayOS/Xu, production webhook
  hay historical Bot records.
- Không expose provider token, raw FFmpeg command, local path, object key hay
  permanent URL cho browser.
- Không fake progress/output; state guarded, failed, cancelled hoặc
  waiting-review phải hiện đúng sự thật.
- Không biến mobile thành desktop timeline hay Admin ERP thu nhỏ; mobile bắt
  đầu từ capture/upload, status, notification và review nhẹ.
- Mỗi capability public phải có safe-off flag, evidence test và rollback path.

## Checklist mở workstream product sau UI/UX

- [ ] UI/UX customer và Admin ERP được owner nghiệm thu trên desktop/mobile.
- [ ] Một capability Web-native có product owner, authority matrix và retention
      policy.
- [ ] Fixture-only test plan bao gồm duplicate confirmation, invalid output,
      cross-account access, expired delivery và receipt dedupe.
- [ ] Không có provider/payment/webhook/Bot mutation trong design hoặc fixture
      milestone.
- [ ] Support evidence đã redacted, role-scoped và không có mutable override.
- [ ] Một safe-off flag và rollback decision được ghi trước khi mở public lane.

## Kết luận

Nghiên cứu được giữ lại như một roadmap có điều kiện: xây Web/App thành sản
phẩm media đáng tin cậy và platform-neutral, nhưng khởi đầu bằng một lane nhỏ
chạy thật, có kiểm chứng. Nó không phải chỉ thị copy toàn bộ Bot hay dựng một
hệ microservice trước khi có evidence.
