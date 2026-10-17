# R213-01 — Free Prompt Gallery locale chrome

## Mục tiêu

Đưa toàn bộ chữ giao diện cố định của `/free-prompt-gallery` về catalogue
VI/EN/ZH đồng nhất. Surface này chỉ là catalog đọc dữ liệu server và thao tác
sao chép/lưu có kiểm soát; không mở thêm engine, provider, job, ví, PayOS hay
luồng Bot.

## Phạm vi được phép

- `static/portal/portal.js`
- `static/portal/portal-i18n.js`
- `tests/free-prompt-gallery-locale-presentation.test.mjs`
- Checklist/state/spec/report của R213-01.

## Bất biến phải giữ

- Không đổi route `/free-prompt-gallery`.
- Không đổi `data-portal-action`, `data-free-prompt-gallery-id`,
  `data-free-prompt-gallery-page`, `data-copy-text` hoặc `data-portal-confirm`.
- Không dịch prompt, tiêu đề, thẻ, ngành, mục tiêu, nền tảng, ID, revision,
  timestamp, receipt hoặc nội dung server-owned.
- Không gọi provider, không mutation ví, không production mutation, không deploy.

## Acceptance criteria

1. VI, EN và ZH có cùng tập khóa `freePromptGallery.*`.
2. Intro, số liệu, filter, kết quả, phân trang, chi tiết, lưu và boundary dùng
   helper locale; VI/ZH không còn cụm UI tiếng Anh cố định.
3. Test giữ nguyên contract action/route/ID và xác nhận dữ liệu động không bị
   dịch hoặc mất.
4. `node --check`, focused test, toàn bộ Node suite và `git diff --check` xanh.
5. Browser/runtime vẫn ghi `QA_RUNTIME_UNAVAILABLE` nếu chưa có runtime thật.

## Trình tự FSM

`READ -> CONTRACT -> BUILD -> REVIEW -> VERIFY -> REPORT -> LEARN`

## Kết quả verify và trạng thái bàn giao (2026-10-15)

- Đã chuyển toàn bộ nhãn, placeholder, help text và option mặc định của bộ
  lọc qua `freePromptGalleryText()`; không còn literal tiếng Việt trong
  `freePromptGalleryFilterFields()`.
- VI/EN/ZH giữ cùng tập khóa; action, route, ID, receipt và dữ liệu prompt do
  server trả không đổi.
- `node --check static/portal/portal.js`: PASS.
- `node --check static/portal/portal-i18n.js`: PASS.
- `node --test tests/free-prompt-gallery-locale-presentation.test.mjs`: 5/5
  PASS.
- `node --test tests/*.test.mjs`: 430/430 PASS.
- `git diff --check`: PASS.
- Browser acceptance: `QA_RUNTIME_UNAVAILABLE`; chưa có DOM/screenshot/
  console/runtime evidence nên chưa gọi là `LIVE_PASS`.

Trạng thái: `SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN`.
