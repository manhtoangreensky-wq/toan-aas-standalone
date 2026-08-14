# Prompt Studio → Prompt Blueprint Composer contract

`/prompt-studio` (alias `/prompts`) là Prompt Blueprint Composer Web-native.
Nó thay form generic Core Bridge cũ bằng một bề mặt authoring rõ ràng: người
dùng đưa mục tiêu, đối tượng, ngữ cảnh, tone, ngôn ngữ, định dạng và ràng buộc
để nhận một blueprint text có thể tự review.

## Nguồn tham chiếu và ranh giới

- Bot chỉ được đọc tĩnh để lấy grammar lập kế hoạch prompt; không đọc pending
  state, seed mutable, Telegram identity, job, provider, Xu hoặc PayOS.
- Không import hoặc sửa `bot.py`, không gọi Core Bridge, model/provider,
  social platform, job, wallet/Xu, PayOS, Asset Vault, render, publish hay
  delivery.
- Blueprint không phải AI output, template đã lưu, fact-check, xác nhận quyền
  hay nội dung đã sẵn sàng dùng ngoài Web App.

| Surface | Authority | Boundary |
| --- | --- | --- |
| `/prompt-studio`, `/prompts` | Signed Web session | Chỉ tạo receipt text tạm thời; không generic `draft → estimate → confirm`. |
| `GET /api/v1/prompt-studio/policy` | Web App | Metadata allowlist read-only, signed/no-store. |
| `POST /api/v1/prompt-studio/compose` | Web App | CSRF + strict request; không ghi database/idempotency/audit detail/template. |
| `POST /api/v1/prompt-studio/save-to-library` | Prompt Studio + Prompt Library | CSRF + `confirmed=true` + idempotency; server recompute blueprint từ brief gốc rồi Prompt Library ghi template owner-scoped/version/audit. |
| `/prompt-library/new` | Prompt Library riêng | Workflow versioned đầy đủ để soạn/chỉnh template; Blueprint không được gửi qua URL hoặc browser storage. |

## Request và response

`POST /api/v1/prompt-studio/compose` nhận JSON strict (`extra="forbid"`):

```json
{
  "goal": "2–300 ký tự một dòng",
  "audience": "tùy chọn, tối đa 300",
  "platform": "general|chat|social|website|email|image|video|voice|document",
  "tone": "clear|friendly|professional|persuasive|educational|creative|neutral",
  "language": "vi|en",
  "output_format": "general|content|caption|script|image_prompt|video_prompt|voice_script|document_outline",
  "constraints": "tùy chọn, tối đa 1.200 ký tự một dòng"
}
```

Server chặn control characters, markup, URL/path/file/social handle, secret,
token, OTP/CVV, dữ liệu thẻ và yêu cầu không nguyên bản/mạo danh. Thành công
trả `status="draft"` với `brief` đã chuẩn hóa cùng `blueprint` gồm prompt text, negative direction,
variable schema và checklist review. Kết quả chỉ nằm trong memory của tab và
bị xóa khi bootstrap session/account thay đổi.

Mọi receipt phải giữ boundary sau:

```json
{
  "execution": "web_native_deterministic_prompt_blueprint_only",
  "input_persisted": false,
  "template_persisted": false,
  "bot_called": false,
  "bridge_called": false,
  "provider_called": false,
  "job_created": false,
  "wallet_mutated": false,
  "payment_started": false,
  "asset_saved": false,
  "media_output_created": false,
  "publish_action_created": false,
  "delivery_created": false,
  "fact_checked": false,
  "rights_verified": false
}
```

Policy guard trả `status="guarded"` với cùng boundary và không trả blueprint.
`WEBAPP_PROMPT_STUDIO_ENABLED` là maintenance flag riêng (mặc định `true` cho
authoring text), không bật bất kỳ execution/runtime bên ngoài nào.

## Handoff có xác nhận vào Prompt Library

`POST /api/v1/prompt-studio/save-to-library` nhận lại đúng bảy trường `brief`
đã chuẩn hóa ở trên, cộng `confirmed: true` và `idempotency_key`. Không nhận
`blueprint`, prompt body, template/account ID, URL, asset, provider, job,
wallet, payment hay browser result/state. Server chạy policy guard trước rồi
server recompute blueprint bằng grammar Prompt Studio; Prompt Library là writer
canonical duy nhất cho quota, version, idempotency và audit owner-scoped.

Receipt thành công là metadata-only: `destination="prompt_library"`,
`execution="web_native_prompt_studio_library_save"`,
`blueprint_recomputed_on_server=true`, `template_persisted=true`, template chỉ
gồm `id`, fixed `category="Prompt Studio"`, `state` và `revision`; các boolean
side-effect ngoài Web đều `false`. Receipt không chứa title dẫn xuất từ goal,
platform, language, prompt text, negative prompt, brief, email, actor, audit
detail hay claim delivery. Owner vẫn xem title và metadata đầy đủ của template
đã lưu qua Prompt Library detail owner-scoped. Policy guard không tạo record
database hay idempotency receipt. Browser chỉ giữ `promptStudioSaveSource`,
`promptStudioSaveReceipt` và một compose-generation số, không-content trong
memory tab; generation được reset khi Compose mới bắt đầu và không được gửi
tới server, URL, localStorage hoặc sessionStorage. Khi một save cũ hoàn tất
sau Compose mới, browser chỉ bind receipt nếu compose-generation hiện hành
đúng bằng generation đã capture lúc Save bắt đầu, đồng thời source và result
hiện hành vẫn khớp save cũ; nếu không, state của Compose mới (kể cả receipt
của nó) không bị thay đổi và UI không khẳng định Compose mới đã được lưu.

## Kiểm thử trọng yếu

- anonymous/CSRF/flag/strict-schema/input safety fail closed và `no-store`;
- response schema/boundary được Portal kiểm tra trước khi render;
- alias không rơi vào `FEATURE_BY_PATH`, generic canonical hydration hoặc
  Bridge action;
- compose lặp lại là deterministic nhưng không tạo idempotency receipt,
  Prompt Library template, audit text, asset, job, payment hay provider call;
- handoff có xác nhận chỉ gửi brief gốc và retry key, server recompute rồi trả
  receipt metadata-only; replay cùng key trả cùng template, brief đổi khác
  conflict và account khác không đọc được template;
- Prompt Library handoff không truyền blueprint qua query, localStorage hoặc
  sessionStorage.
