# R214 — Video UI/UX và locale presentation

Ngày kiểm tra: 2026-10-15
Phạm vi: `/tools/video`, `/video/create`, `/video/multiscene`,
`/video-studio` và `/video-studio/:id`; chỉ presentation/locale/flow guidance,
không bao gồm engine, provider, output thật, Bot/Core, ví/Xu, PayOS, dữ liệu
production, VPS hoặc deploy.

## Kết quả

- `SOURCE_GREEN`: đạt.
- `LIVE_PASS`: chưa công nhận. QA runtime/browser cô lập hiện không khả dụng;
  không có DOM snapshot, screenshot, console/network trace hoặc tương tác thật.
- Fixed chrome VI/EN/ZH của Video Hub, form video và Video Studio dùng catalogue
  cân bằng; dữ liệu server-owned (tiêu đề, brief, mục tiêu, cảnh, ID, revision,
  timestamp, tag) vẫn giữ nguyên.
- Flow generic video được trình bày theo thứ tự dọc: nhập nội dung → lập kế
  hoạch → rà soát báo giá → xác nhận → theo dõi → kết quả/báo cáo → khôi phục.
  Các trường chính (`brief`, `scene_count`, `format`) đứng trước; thiết lập phụ
  nằm trong disclosure, không đổi tên field hay action.
- Video Studio giữ ranh giới trung thực: kế hoạch/cảnh/lịch sử là metadata
  biên tập; không dựng, tải lên, phát, tạo URL, tạo job hay giả kết quả media.

## Thay đổi theo spec

- `static/portal/portal.js`
  - Localize Video Studio bằng helper `videoStudioText()` và catalogue
    `videoStudioUi.*` cho trang danh sách, form tạo, thẻ kế hoạch, chi tiết,
    cảnh, lịch sử, hoạt động, trạng thái, boundary và trạng thái rỗng/lỗi.
  - Bổ sung `aria-label` cho nút đưa cảnh lên/xuống.
  - Localize generic video form bằng `videoUi.*`, giữ flow bảy bước, core fields
    trước optional settings và output/report boundary.
  - Giữ nguyên route, `data-portal-action`, `data-portal-route`, tên field,
    capability, CSRF, idempotency, revision và dữ liệu động.
- `static/portal/portal-i18n.js`
  - Thêm catalogue cân bằng `videoUi.*` và `videoStudioUi.*` cho VI/EN/ZH.
  - Không dịch prompt, title, ID, timestamp, tag hoặc dữ liệu do server trả.
- `tests/video-uiux-locale-presentation.test.mjs`
  - Khóa keyset cân bằng cho Video Studio và generic video-task.
  - Render Video Hub ở cả ba locale, kiểm tra fixed chrome, route hiện có và
    trạng thái ready/guarded.
  - Khóa form `/video/create` và `/video/multiscene` theo flow bảy bước,
    core/optional fields và boundary không provider/wallet/job.
  - Giữ kiểm thử render home/detail Video Studio, contract action/field/revision
    và bảo toàn dữ liệu động.

## Bằng chứng terminal

```text
node --check static/portal/portal.js: PASS (exit 0)
node --check static/portal/portal-i18n.js: PASS (exit 0)
node --test tests/video-uiux-locale-presentation.test.mjs: 10 passed, 0 failed
node --test tests/*.test.mjs: 445 passed, 0 failed
git diff --check: PASS (exit 0)
```

## Chốt phạm vi và việc chưa làm

- Không gọi provider, không tạo job, không mutation ví/Xu/PayOS, không sửa
  backend/route/engine và không deploy.
- Motion (auth render hai lần, `left` transition, scroll reveal, popup Telegram,
  PWA readiness, reduced-motion/CLS/LCP/INP) vẫn để R216 sau R215 theo thứ tự.
- Browser acceptance ở 375/390/768/1440, keyboard/focus, computed style,
  console/network và persistence vẫn mở vì thiếu QA runtime cô lập.
- R215 là nghiệm thu UI/UX toàn app; chỉ sau khi R215 đóng mới chuyển R216 Motion.

```ini
SPEC_ID=R214-video-uiux-locale-presentation
STATUS=SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=WORKTREE_UNCOMMITTED
FILES_CHANGED=static/portal/portal.js,static/portal/portal-i18n.js,tests/video-uiux-locale-presentation.test.mjs
TESTS=syntax+focused10+node445+diff-check
BASELINE_FAILURES=0
BRANCH_FAILURES=0
NEW_FAILURES=0
PROTECTED_COMPARATORS=routes/actions/fields/capabilities/csrf/idempotency/revisions/dynamic_server_data
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=UNAVAILABLE
LIVE_PASS=NO
BROWSER=QA_RUNTIME_UNAVAILABLE
BLOCKERS=isolated QA runtime not supplied
COMMIT=NO
PUSH=NO
MERGE=NO
```
