# Video Production Studio — Web-native contract

## Mục đích

Video Production Studio là không gian **lập kế hoạch sản xuất** thuộc Web App:
brief, shot list, scene order, transition, cue cho âm thanh/phụ đề, checklist
review và revision history. Nó chuyển các luồng lập brief/storyboard/video của
Telegram Bot thành một workflow Web dễ dùng hơn, nhưng không thay thế engine
render, hàng đợi job, preview hay delivery của Bot/provider.

Mỗi plan và scene thuộc một signed Web account. Web chỉ giữ metadata
authoring có thể kiểm soát: không giữ raw media, đường dẫn tệp, URL provider,
provider ID, Telegram file ID, job, Xu, PayOS hay trạng thái thanh toán.

## Scope Web-native

- `/video-studio`, `/video-studio/new`, `/video-studio/{uuid}`.
- Plan có brief, platform, aspect ratio, duration target, visual direction,
  CTA, tag, liên kết Project/record Web-owned bằng ID và lifecycle
  `draft → review → approved → archived`.
- Scene có thứ tự, shot/camera/movement, visual direction, transition,
  audio/subtitle intent và checklist; mọi thay đổi có revision riêng.
- Estimate runtime/storyboard là tính toán xác định để review planning. Nó
  luôn công khai `provider_called=false` và `video_created=false`.
- `approved` là self-review của Web, không phải approval tạo job, publish,
  charge, output hoặc delivery.

## Quy tắc bảo mật và dữ liệu

- Signed session bắt buộc; read/write đều owner-scoped. Record của account
  khác trả về not-found an toàn, không tiết lộ title/brief/scene.
- Mọi write cần CSRF, idempotency key, request ID và expected revision. Key
  được dùng lại với payload khác trả conflict; receipt/audit không sao chép
  brief hay scene text riêng tư.
- Schema và body đều bounded. Secret, token, credential, OTP, dữ liệu thẻ,
  chứng từ payment, marker provider/Bot/job/media ID, control character và
  input không an toàn bị chặn trước persistence.
- Archive plan khóa toàn bộ scene mutation/reorder/estimate ở server. Archive
  scene khóa các thao tác con tương ứng. Version/event history là immutable.
- Sau mỗi Portal remount, browser chỉ giữ projection đã allow-list của signed
  read: summary count, plan/scene authoring bounded, revision, event label,
  Project reference và runtime arithmetic. Projection phải giữ archive ordinal
  riêng của scene history (kể cả history legacy trước lần server repair kế
  tiếp), đồng thời loại account ID, boundary payload, storage key,
  media/provider URL, output, delivery, job và action/destination do server
  trả về. Estimate chỉ được hiển thị khi plan ID và phép trừ thời lượng đã
  được kiểm tra lại.
- PWA chỉ cache public shell; route/API Video Studio và mọi data private không
  nằm trong manifest cache.

## Boundary với legacy Video/Bot

`/video-studio` là route Web-native riêng, không phải alias `/video/*`.
Hydration native phải chạy trước generic legacy Video bridge để tránh route
collision. `/video/*` cũ tiếp tục hiển thị workflow canonical/guarded cho
engine readiness, quote, job, preview/export và delivery thực.

Module này không import/call Bot, Core Bridge, provider, FFmpeg, render API,
wallet, PayOS, worker hay Telegram. Không có player, preview URL, download,
completed status hay video output giả. Một engine/delivery integration tương
lai phải được xây thành contract riêng có authentication, ownership, policy,
quote/charge, output validation và review độc lập.

## Điều hướng Studio

Sidebar nhóm các route Video Studio theo quyết định tiếp theo của người dùng:

1. **Video Studio** — kế hoạch sản xuất và điểm bắt đầu workflow.
2. **Ý tưởng & kịch bản** — idea, story, prompt và cinematic concept.
3. **Phim & storyboard** — Script-to-Screen/Phim dài tập, long-form,
   self-shot và storyboard.
4. **Tư liệu & chuyển động** — image-motion và reference-format.

Đây chỉ là cấu trúc điều hướng có progressive disclosure. URL, signed
session/CSRF, owner check, capability và execution boundary của từng route
không thay đổi; menu không cấp render, provider, job, payment hay delivery.

## Kiểm thử trọng yếu

- Session/CSRF/body limit/idempotency/revision/owner isolation.
- Archive parent freeze, lifecycle and scene ordering/version history.
- Deterministic estimate does not become a render/job/output assertion.
- Native route/API boundary, legacy route separation, PWA private-cache
  exclusion, responsive UI action forwarding and guarded states.
