# R213-02 — Audio Workspace / Audio Hub shell locale

## Mục tiêu

Đưa fixed chrome của shell/home và bộ lọc `/media-workspace` cùng
`/audio-hub` về catalogue VI/EN/ZH đồng nhất. Đây là lớp trình bày của
workspace âm thanh; không mở thêm provider, engine, job, ví/Xu, PayOS hay
luồng Bot.

## Phạm vi được phép

- `static/portal/portal.js`
- `static/portal/portal-i18n.js`
- `tests/audio-workspace-shell-locale.test.mjs`
- State/checklist/plan/spec/report của R213-02.

## Bất biến phải giữ

- Không đổi route `/media-workspace`, `/audio-hub` hoặc route detail.
- Không đổi `data-portal-action`, field name, capability, CSRF, idempotency,
  revision, prompt-mode value, role value hoặc pagination contract.
- Không dịch collection title, brief, tag, use-context, event timestamp, ID,
  revision, policy text và dữ liệu dynamic do server trả.
- Không sửa detail/editor trong checkpoint này; không gọi provider và không
  mutation ví/dữ liệu production.

## Acceptance criteria

1. Shell/home, overview, policy, filter, list card, audit feed và next-step
   cards dùng helper locale; VI không còn generic English UI xen kẽ.
2. VI/EN/ZH có cùng tập khóa `audioWorkspace.*`; option values giữ nguyên
   canonical values.
3. Test chứng minh route/action/field/capability và dữ liệu dynamic không đổi.
4. `node --check`, focused test, toàn bộ Node suite và `git diff --check` xanh.
5. Browser vẫn ghi `QA_RUNTIME_UNAVAILABLE` nếu chưa có runtime cô lập.

## Trình tự FSM

`READ -> CONTRACT -> BUILD -> REVIEW -> VERIFY -> REPORT -> LEARN`
