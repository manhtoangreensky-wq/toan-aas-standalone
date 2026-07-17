# Image Prompt Composer contract

`/image/prompt-composer` chuyển cấu trúc prompt ảnh thuần của Telegram Bot thành một công cụ Web-native để soạn và review text. Nó không phải image generator, vision tool hay đường dẫn upload ảnh. Bản nháp chỉ được lưu khi người dùng gọi action riêng; preview không tự ghi dữ liệu.

## Nguồn tham chiếu và phạm vi

- Bot chỉ được đọc tĩnh: `bot.py` các hàm goal label/style, `normalize_image_tool_ratio`, `build_image_prompt_output`, `image_prompt_state_with_ratio` và biến thể prompt quanh dòng 38964–39298 của baseline P0.
- Web giữ phần có thể xác định: mục tiêu, style default, chuẩn hoá tỷ lệ, short prompt, detailed prompt, negative prompt và ba biến thể theo thứ tự sales/premium/viral.
- Web không mang sang Telegram state, `file_id`, source image, provider selection, Xu/charge hoặc callback Bot. Action lưu Web được dựng riêng: nó không đọc hay tạo pending state của Telegram.

## Contract đang có

- UI route: `/image/prompt-composer`
- API: `POST /api/v1/image-studio/tools/prompt-composer`
- Explicit Memory action: `POST /api/v1/image-studio/tools/prompt-composer/save`
- Feature key: `image_prompt_composer`
- Action: `image-prompt-compose`

Request strict (`extra="forbid"`) chỉ nhận:

```json
{
  "goal_code": "product | ad | cinematic | custom",
  "custom_goal": "bắt buộc khi goal_code là custom",
  "subject": "2–260 ký tự",
  "style": "tùy chọn, 2–180 ký tự nếu có",
  "ratio": "1:1 | 9:16 | 16:9 | 4:5 | 3:4 | 4:3 | 3:2 | 2:3 | 21:9",
  "language": "vi | en"
}
```

Ratio alias Bot-compatible được chuẩn hoá: `1x1`, `square`, `vuong`; `9x16`, `doc`, `vertical`, `reels`, `tiktok`; `16x9`, `ngang`, `horizontal`, `youtube`; và dạng `×`. Ratio lạ bị từ chối, không tự suy đoán.

Endpoint cần signed Web session và CSRF. Response thành công luôn là `status="draft"`, `data.composer` chứa text prompt + đúng ba variant string, và boundary sau:

```json
{
  "execution": "web_native_deterministic_prompt_only",
  "input_persisted": false,
  "source_image_inspected": false,
  "provider_called": false,
  "image_created": false,
  "output_created": false,
  "job_created": false,
  "payment_started": false,
  "wallet_mutated": false,
  "asset_saved": false,
  "publish_action_created": false,
  "fact_checked": false,
  "rights_verified": false
}
```

`POST /tools/prompt-composer` luôn request-only: không có idempotency key, write, audit event hay Memory note. Portal render mọi text bằng escaped output và bản nháp không trở thành output ảnh.

## Lưu rõ ràng vào Memory Center

`POST /api/v1/image-studio/tools/prompt-composer/save` cần signed Web session, CSRF, `WEBAPP_IMAGE_STUDIO_ENABLED` và `WEBAPP_MEMORY_CENTER_ENABLED` cùng đang bật. Request cũng `extra="forbid"`; chỉ nhận lại đúng input composer đã giới hạn ở trên, cộng thêm:

```json
{
  "destination": "memory_note",
  "idempotency_key": "12–160 ký tự [A-Za-z0-9._:-]"
}
```

Không nhận `content`, `title`, `composer`, `pack`, `account_id`, image/file/asset/provider reference hoặc bất kỳ text kết quả nào do browser gửi. Máy chủ chạy lại deterministic composer trong cùng transaction, sau đó mới ghi một ghi chú Web-owned vào `web_memory_notes`, version đầu tiên, Memory event, audit event không chứa nội dung và receipt idempotency không chứa title/body/prompt.

Receipt thành công là `status="completed"`, chỉ trả UUID/revision/state/category/priority của note và các fact boundary; nội dung riêng tư chỉ được đọc qua endpoint Memory Center với đúng signed owner. Boundary save gồm:

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
  "source_image_inspected": false,
  "provider_called": false,
  "image_created": false,
  "output_created": false,
  "job_created": false,
  "wallet_mutated": false,
  "payment_started": false,
  "asset_saved": false,
  "publish_action_created": false,
  "delivery_created": false,
  "fact_checked": false,
  "rights_verified": false
}
```

Idempotency replay trả lại cùng receipt content-free. Dùng lại key với input khác trả `409`; đọc note qua account khác trả `WEB_MEMORY_NOTE_NOT_FOUND`.

## Bảo mật và claim boundary

- Body/rate limit của Image Studio, signed session và CSRF chạy trước template.
- URL, file/data/javascript scheme, provider/job/file handle, secret, private key, OTP, số thẻ/bằng chứng thanh toán và markup thực thi bị chặn ở cả server và browser defence-in-depth.
- Request mô phỏng nghệ sĩ, tác giả hoặc phong cách nhận diện bị guard; người dùng phải mô tả direction nguyên bản.
- Preview `/tools/prompt-composer` không có database write, audit detail, idempotency record, project/artboard relation, Asset Vault write, browser local storage hay history endpoint. Chỉ action save rõ ràng mới tạo một Web-owned Memory note theo contract ở trên.
- Không nhận ảnh, file, URL, `file_id`, asset ID hoặc hứa đã phân tích ảnh. Người dùng chỉ mô tả chủ thể bằng text.
- Không gọi Bot/Core Bridge, provider/model/vision, Key4U, PayOS, wallet, webhook, job, render, preview, output URL, publish hay delivery.

`WEBAPP_IMAGE_STUDIO_ENABLED` là maintenance gate cho cả preview và explicit save. `WEBAPP_MEMORY_CENTER_ENABLED` là gate độc lập bắt buộc cho save. Hai flag không bật image engine, asset delivery hay operation Image Studio khác.

## Không thuộc phạm vi

Upload/phân tích ảnh, create/edit/upscale/remove-background, preview/render ảnh, output asset, social publish, provider integration, billing/Xu/PayOS, job queue và Telegram callback cần contract/adapter riêng. Lưu một note prompt không bao giờ là bằng chứng rằng bất kỳ khả năng nào trong số đó đã chạy.
