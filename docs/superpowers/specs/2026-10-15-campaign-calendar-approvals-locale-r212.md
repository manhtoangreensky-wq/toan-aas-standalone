# Campaign / Calendar / Approvals locale và presentation — R212

Đang đọc và áp dụng skill owner-governed-codex cho task này.

```ini
SPEC_ID=WEBAPP-E0-CAMPAIGN-CALENDAR-APPROVALS-LOCALE-R212
STATUS=LOCAL_SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
SCOPE=Web App standalone /campaigns, /campaigns/new, /campaigns/<id>, /calendar, /approvals
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1 (workspace uncommitted)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
COMMIT=NO
PUSH=NO
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
```

## Mục tiêu

Đưa toàn bộ chữ cố định của Campaign Planner, lịch nội dung và hàng tự rà soát
qua catalogue `campaignUi.*` cân bằng VI/EN/ZH. Giao diện phải rõ thứ tự
`bảng kế hoạch → tạo/chỉnh sửa → chi tiết → lịch → tự rà soát`; dữ liệu người
dùng và dữ liệu máy chủ không bị dịch hoặc ghi đè trong trình duyệt.

## Phạm vi và hợp đồng được bảo vệ

Tệp thuộc lát R212:

- `static/portal/portal.js`
- `static/portal/portal-i18n.js`
- `tests/campaign-planner-locale-presentation.test.mjs`

Route giữ nguyên:

- `/campaigns`, `/campaigns/new`, `/campaigns/<id>`, `/calendar`, `/approvals`.

Giữ nguyên các action và thuộc tính workflow:

- `campaign-create`, `campaign-update`, `campaign-update-status`;
- `campaign-calendar-filter`, `campaign-calendar-month`,
  `campaign-calendar-refresh`;
- `campaign-schedule-create`, `campaign-schedule-cancel`,
  `campaign-schedule-reconfirm`;
- `data-campaign-plan-id`, `data-campaign-plan-revision`,
  `data-campaign-schedule-intent-id`,
  `data-campaign-schedule-intent-revision`.

Không thuộc phạm vi: Bot/Core, Telegram, provider, ví/Xu, PayOS, dữ liệu
production, VPS, deploy, backend contract hoặc motion runtime.

## Thay đổi đã khóa

- Gộp `CAMPAIGN_UI_MESSAGES` vào `MESSAGES` để helper locale thực sự có hiệu
  lực khi đổi VI/EN/ZH.
- Localize bảng kế hoạch, trạng thái, mục tiêu, nền tảng, tạo/chỉnh sửa,
  chi tiết, ghi chú, lịch nội dung, agenda, lời nhắc in-app và hàng tự rà soát.
- Localize các guard source/revision, trạng thái rỗng/đang tải/lỗi/bảo vệ,
  thông báo cửa sổ dữ liệu và nút điều hướng.
- Giữ nguyên giá trị enum, ID, URL HTTPS, timestamp, timezone, revision,
  receipt và mọi dữ liệu động do người dùng/máy chủ cung cấp.
- Không còn các cụm fixed English xen trong vùng renderer Campaign.

## Checklist nghiệm thu

- [x] Keyset `campaignUi.*` cân bằng VI/EN/ZH, 204 khóa mỗi locale.
- [x] Renderer Campaign/Calendar/Approvals dùng `campaignText()` cho fixed
  chrome và các nhãn map trạng thái/nền tảng/mục tiêu.
- [x] Không còn stale fixed copy: `New private campaign`, `Execution boundary`,
  `Private campaign operations`, `Owner-scoped library`, `Campaign Operations
  Board`, `Content Calendar`, `Self-review Queue`, `signed account`,
  `owner-scoped`, `Web-owned`.
- [x] Route/action/field/capability/CSRF/idempotency/revision contract không đổi.
- [x] Dữ liệu động không bị dịch hoặc viết lại.
- [x] `node --check static/portal/portal.js` đạt.
- [x] `node --check static/portal/portal-i18n.js` đạt.
- [x] `node --test tests/campaign-planner-locale-presentation.test.mjs` đạt 2/2.
- [x] `node --test tests/*.test.mjs` đạt 425/425.
- [x] `git diff --check` đạt.
- [ ] Browser runtime QA trên VI/EN/ZH ở desktop/tablet/mobile.
- [ ] DOM/computed style/keyboard/focus/console/network/persistence trong
  runtime QA.

## Bằng chứng và giới hạn

Đây là `SOURCE_GREEN`: kiểm thử tĩnh và Node đạt, nhưng runtime QA cô lập chưa
có dịch vụ đang lắng nghe nên chưa thể kết luận browser/live pass. Không có
provider call, wallet mutation, production mutation, commit, push, merge hoặc
deploy trong checkpoint này.

## Bước kế tiếp

Giữ R212 ở trạng thái browser acceptance mở. Khi có runtime, chạy bảng kế hoạch,
form tạo, chi tiết, lịch và hàng tự rà soát ở 375/390/768/1440px trong VI/EN/ZH;
kiểm tra bàn phím, focus, computed style, console/network và persistence. Sau
khi ghi nhận evidence, chuyển sang R213 — các surface non-video còn fixed copy.
