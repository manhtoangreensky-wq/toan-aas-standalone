# Publish Review Pack — Web-native contract

`/content/publish-review` chuyển `freehub|publish_package` của Telegram Bot
thành một bề mặt review copy rõ nguồn trên Web. Đây là công cụ chuẩn bị text
để người dùng tự kiểm tra trước khi sử dụng ở một kênh đã được cấp quyền; nó
không phải post, lịch đăng, social draft, analytics hay biên nhận delivery.

## Nguồn Bot và cách chuyển đổi

- Nút Free Hub gốc: `bot.py:46042–46050` và nút tiếp theo từ kết quả text:
  `bot.py:46479–46487`.
- Callback Bot: `bot.py:59704–59718` chỉ lấy `result` đang nằm trong pending
  record Telegram rồi gọi `free_hub_publish_package_text()`.
- Formatter text thuần: `bot.py:46546–46582`. Nó ghép title, caption,
  hashtag, CTA, prompt nền và checklist; Bot cũng ghi rõ chưa gọi provider
  hoặc trừ Xu.

Web **không** import Bot, đọc pending record Telegram, tái tạo kết quả cũ từ
browser/session, hoặc dùng Bot như một API. Thay vào đó, tài khoản chủ động
gửi toàn bộ copy cần review trong một request có signed session và CSRF. Cách
này bỏ hidden state Telegram và giữ ranh giới giữa bản nháp review với một
đăng bài thật.

## API và dữ liệu

- UI route: `/content/publish-review`
- API: `POST /api/v1/content-studio/tools/publish-review-pack`
- Maintenance gate: `WEBAPP_CONTENT_STUDIO_ENABLED`

Request strict (`extra="forbid"`):

```json
{
  "title": "Bình giữ nhiệt cho ngày làm việc",
  "caption": "Một caption do bạn chủ động đưa vào để rà soát.",
  "hashtags": ["#ContentDraft", "#ReviewBeforePost"],
  "cta": "Xem thêm thông tin phù hợp trước khi quyết định.",
  "source_prompt": "Prompt nền tùy chọn để đối chiếu."
}
```

`title` là một dòng 2–180 ký tự; `caption` tối đa 2.000 ký tự;
`hashtags` tối đa 12 phần tử được chuẩn hóa thành `#tag`; `cta` là tùy chọn,
tối đa 240 ký tự; `source_prompt` là tùy chọn, tối đa 3.200 ký tự. Server
chặn field lạ, control characters, secret/token/private key, dữ liệu
thanh toán/OTP và marker yêu cầu mô phỏng tác giả, nghệ sĩ, bài hát hoặc phong
cách cụ thể.

Thành công trả `status="draft"`, `package` với title/caption/hashtags/CTA,
prompt nền, checklist review và hướng dẫn copy. Hashtag hoặc CTA thiếu chỉ nhận
default text cố định; không có model, provider hoặc suy luận ẩn. Nếu guard
originality kích hoạt, response là `status="guarded"` với
`WEB_PUBLISH_REVIEW_ORIGINALITY_GUARD` và không có package.

## Execution boundary và bảo mật

Mọi receipt được portal chấp nhận phải mang
`execution="web_native_publish_review_text_only"` và toàn bộ các giá trị sau
phải là `false`:

```text
input_persisted, provider_called, bot_called, job_created, wallet_mutated,
payment_started, asset_saved, media_output_created, publish_action_created,
delivery_created, fact_checked, rights_verified
```

- Endpoint yêu cầu signed Web session và CSRF trước khi tạo template.
- Không có database write, revision, audit detail chứa copy, project relation,
  browser local/session storage, history endpoint hay PWA private cache.
- Không gọi Telegram/Bot/Core Bridge, social account, scheduler, provider,
  Key4U, PayOS, wallet/Xu, webhook, asset vault, upload, render, job, output
  URL, publish action hoặc delivery.
- Web không fact-check, xác thực quyền, xác nhận disclosure, kiểm tra chính
  sách kênh, kết nối kênh hay tự đăng. Người dùng phải tự kiểm chứng claim,
  quyền của asset/người xuất hiện/thương hiệu và chính sách của nơi đăng.

## Không thuộc phạm vi

Lưu version, workflow approval, social connections, scheduler, actual
publishing, analytics/performance tracking, asset upload/delivery, AI/media
generation, provider execution, Xu/wallet, PayOS và notification cần các
contract và capability riêng. Publish Review Pack không được dùng để suy luận
rằng bất kỳ khả năng nào trong số đó đã bật hoặc an toàn để dùng.
