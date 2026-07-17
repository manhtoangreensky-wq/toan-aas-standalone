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
| `/prompt-library/new` | Prompt Library riêng | Người dùng tự chuyển sang workflow versioned; Blueprint không được gửi qua URL hoặc browser storage. |

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
trả `status="draft"` với `blueprint` gồm prompt text, negative direction,
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

## Kiểm thử trọng yếu

- anonymous/CSRF/flag/strict-schema/input safety fail closed và `no-store`;
- response schema/boundary được Portal kiểm tra trước khi render;
- alias không rơi vào `FEATURE_BY_PATH`, generic canonical hydration hoặc
  Bridge action;
- compose lặp lại là deterministic nhưng không tạo idempotency receipt,
  Prompt Library template, audit text, asset, job, payment hay provider call;
- Prompt Library handoff là link tường minh không truyền blueprint qua query,
  localStorage hoặc sessionStorage.
