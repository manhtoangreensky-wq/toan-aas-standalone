# Content Prompt Pack contract

`/content/prompt-pack` chuyển năm recipe text thuần từ baseline Telegram Bot thành một công cụ Web-native có thể biên tập. Nó là lớp lập kế hoạch nội dung, không phải một AI engine hay một đường dẫn tạo media.

## Nguồn tham chiếu và phạm vi

- Baseline Bot chỉ được đọc tĩnh: `bot.py` các hàm `free_hub_meta_prompt_pack`, `free_hub_caption_pack`, `free_hub_content_ideas_pack`, `free_hub_image_video_prompt_pack` và `free_tools_hub.py:355` (`hook_script_pack`) ở baseline P0.
- Web giữ cấu trúc hữu ích: prompt scaffold, caption/hashtag, content ideas, hook/script và visual/video storyboard text.
- Web chủ ý bỏ ngôn ngữ Telegram, Bot, provider affiliation, Xu/thanh toán, brand tag cố định và lời hứa inbox/publish.
- Không import, gọi hoặc sửa `bot.py`.

## Contract đang có

- UI route: `/content/prompt-pack`
- API tạo bản nháp tạm thời: `POST /api/v1/content-studio/tools/prompt-pack`
- API lưu có chủ đích: `POST /api/v1/content-studio/tools/prompt-pack/save`

Các lối tắt Web cũ được giữ cho bookmark và điều hướng ổn định, nhưng đều mở
cùng Prompt Pack Web-native với một `kind` cố định đã allowlist. Chúng không
đi vào generic Core Bridge `draft → estimate → confirm`:

| Route chính | Alias | Kind mặc định |
| --- | --- | --- |
| `/content/caption` | `/caption` | `caption_hashtag` |
| `/content/hashtag` | `/hashtag` | `caption_hashtag` |
| `/content/hook` | `/hook` | `hook_script` |
| `/content/script` | `/script` | `hook_script` |
| `/content/storyboard` | `/storyboard` | `image_video_prompt` |
| `/content/pack` | `/content-pack` | `content_ideas` |

Người dùng vẫn có thể đổi recipe ngay trong form. Alias không nhận pending
Telegram result, không mang topic qua URL và không khởi tạo bridge, provider,
job, payment, asset, publish hay delivery.

- Request strict (`extra="forbid"`):

```json
{
  "kind": "meta_ai_prompt | caption_hashtag | content_ideas | hook_script | image_video_prompt",
  "topic": "2–180 ký tự một dòng",
  "variant_seed": 0
}
```

Endpoint cần signed Web session và CSRF. `variant_seed` chỉ chọn biến thể template xác định, không seed model, không tạo prompt execution và không được dùng như quyền truy cập.

Mỗi phản hồi thành công có `status="draft"`, `pack` đã được kiểm tra schema và luôn xác nhận đủ biên giới sau:

```json
{
  "execution": "local_deterministic_text_only",
  "input_persisted": false,
  "provider_called": false,
  "job_created": false,
  "payment_started": false,
  "publish_action_created": false,
  "fact_checked": false,
  "rights_verified": false
}
```

Portal chỉ render kết quả khi toàn bộ fields trên, kind, độ dài topic, sections, items và checklist xác minh đều hợp lệ. Kết quả chỉ ở memory của portal và bị xóa trong bootstrap/session transition.

## Lưu bản nháp vào Memory Center

Bot `freehub|save` chỉ lưu kết quả đang xem thành ghi chú; nó không chạy model, tạo job, trừ Xu hay gọi PayOS. Web giữ cùng ý nghĩa bằng một hành động riêng sau khi người dùng đã review Prompt Pack:

```json
{
  "kind": "hook_script",
  "topic": "Bộ dụng cụ pha cà phê cho người mới",
  "variant_seed": 2,
  "destination": "memory_note",
  "idempotency_key": "content-prompt-pack-save-0001"
}
```

- Request strict (`extra="forbid"`), signed session, CSRF, `WEBAPP_CONTENT_STUDIO_ENABLED` và `WEBAPP_MEMORY_CENTER_ENABLED` đều bắt buộc.
- Browser không gửi `pack`, `title`, `content`, account ID hay pending Telegram result. Server dựng lại template từ `kind/topic/variant_seed`, rồi atomically tạo một Web-owned Memory note, version 1, event và audit record đã sanitize.
- Idempotency scope theo account. Receipt replay chỉ có opaque note ID, revision/state/category/priority và boundary fields; không có topic, title, prompt, excerpt, tag hay nội dung ghi chú.
- Không có sửa bảng Bot, đọc Bot pending state, gửi Telegram, Bot/Core Bridge/provider/Key4U call, job, Xu/wallet mutation, PayOS/payment, asset, publish hay delivery.

Phản hồi thành công dùng `status="completed"` và luôn phân biệt rõ:

```json
{
  "execution": "web_native_memory_note_server_recomputed",
  "draft_recomputed_on_server": true,
  "web_note_persisted": true,
  "browser_result_persisted": false,
  "pending_bot_save_created": false,
  "telegram_state_changed": false,
  "bot_called": false,
  "bridge_called": false,
  "provider_called": false,
  "job_created": false,
  "wallet_mutated": false,
  "payment_started": false,
  "asset_saved": false,
  "publish_action_created": false,
  "delivery_created": false
}
```

Originality guard không tái tạo/lưu note; quota guard sau tái tạo trả `draft_recomputed_on_server=true` nhưng `web_note_persisted=false`. Không có cắt ngắn im lặng: nội dung vượt giới hạn Memory Center bị từ chối trước khi ghi.

Handoff này bao phủ năm recipe deterministic mà `freehub|save` có thể lưu trong baseline Bot: Meta prompt, caption/hashtag, content ideas, hook/script và image/video direction. Audit vì thế map callback generic đó về `/content/prompt-pack` với trạng thái `COPIED_GUARDED`. Điều này không có nghĩa Web đọc “kết quả gần nhất” của Telegram: mỗi save Web chỉ hợp lệ sau khi chính `/content/prompt-pack` đã trả một selection khớp trong phiên, và server dựng lại toàn bộ note từ selection đó.

## Bảo mật, ownership và claim boundary

- Request được kiểm tra body/rate limit chung của Content Studio, signed session và CSRF trước khi tạo template.
- `topic` bị chặn control character, secret/token/private key, chứng từ/thông tin thanh toán và marker imitation/copyright policy. Server là authority; browser chỉ kiểm tra phòng thủ thêm.
- Endpoint tạo bản nháp không có database write, revision, audit detail chứa topic, project relation, browser local storage hay history endpoint.
- Endpoint lưu chỉ ghi Memory note/version/event thuộc signed Web account sau xác nhận. Idempotency/audit không chứa topic hoặc prompt; portal không giữ draft/receipt trong localStorage hay sessionStorage.
- Không gọi Bot, Core Bridge, Telegram, provider/model, Key4U, PayOS, wallet, webhook, asset vault, upload, output URL, job hoặc publish action.
- Không hứa fact checking, quyền sử dụng, chất lượng, hiệu quả marketing, xu hướng, render hay delivery. Người dùng phải biên tập và xác minh claim/quyền trước khi dùng bên ngoài.
- `WEBAPP_CONTENT_STUDIO_ENABLED` là maintenance gate cho Prompt Pack. Handoff Memory còn cần `WEBAPP_MEMORY_CENTER_ENABLED`; hai flag không bật Bot, engine/provider, wallet, payment hay publish capability.

## Không thuộc phạm vi

Lưu/publish content, social platform connection, image/video generation, rendering, upload, asset delivery, analytics, wallet/Xu, PayOS, job queue, provider result, Telegram notification và automation outbound cần các contract riêng. Prompt Pack không được dùng để suy luận rằng các khả năng đó đã sẵn sàng.
