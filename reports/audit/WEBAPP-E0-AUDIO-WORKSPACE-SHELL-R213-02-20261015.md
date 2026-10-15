# R213-02 — Audio Workspace / Audio Hub shell locale

Ngày kiểm tra: 2026-10-15
Phạm vi: fixed chrome của `/media-workspace` và `/audio-hub`; không bao gồm
detail/editor, engine, provider, job, ví/Xu, PayOS, Bot hoặc dữ liệu production.

## Kết quả

- `SOURCE_GREEN`: đạt.
- `LIVE_PASS`: chưa công nhận vì runtime/browser QA cô lập chưa chạy
  (`QA_RUNTIME_UNAVAILABLE`). Không dùng source test hoặc HTTP 200 thay cho
  bằng chứng render thật.
- VI/EN/ZH có cùng catalogue `audioWorkspace.*` và renderer dùng helper locale
  cho overview, create shell, filter, list card, policy, audit feed và next-step
  cards.
- Dữ liệu động từ máy chủ (title, brief, tag, use-context, policy statement,
  event timestamp, ID, revision) vẫn giữ nguyên; test kiểm tra trực tiếp các
  giá trị mẫu.
- Giá trị hợp đồng `background`, `lyrics`, `script`, `melody`, `custom`,
  `music`, `sfx`, `reference` không đổi.

## Bằng chứng terminal

```text
node --check static/portal/portal.js: PASS (exit 0)
node --check static/portal/portal-i18n.js: PASS (exit 0)
node --test tests/audio-workspace-shell-locale.test.mjs: 5 passed, 0 failed
node --test tests/*.test.mjs: 435 passed, 0 failed
git diff --check: PASS (exit 0)
```

## Thay đổi theo spec

- Thêm `audioWorkspace.*` catalogue cân bằng VI/EN/ZH trong
  `static/portal/portal-i18n.js`.
- Thêm helper `audioWorkspaceText()` và mapping label/option chỉ dành cho
  shell trong `static/portal/portal.js`.
- Localize bộ lọc, form tạo mới, card collection, policy boundary, overview
  Audio Hub, next-step cards, audit feed và fallback/empty state.
- Tách `mediaCollectionShellFormFields()` để không mở rộng phạm vi sang
  detail/editor của checkpoint sau.
- Thêm `tests/audio-workspace-shell-locale.test.mjs` để khóa locale purity,
  contract route/action/field và bảo toàn dữ liệu động.

## Chưa làm trong R213-02

- Chưa dịch hoặc chỉnh detail/editor và các route audio chuyên dụng.
- Chưa chạy browser DOM/screenshot/console/network trên QA runtime vì runtime
  cô lập chưa được cung cấp.
- Chưa chuyển sang R214 Video, R215 nghiệm thu UI/UX toàn app hoặc R216 Motion;
  đúng thứ tự checklist.

```ini
SPEC_ID=R213-02-audio-workspace-shell-locale
STATUS=SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
BROWSER=QA_RUNTIME_UNAVAILABLE
LIVE_PASS=NO
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
```
