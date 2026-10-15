# Notes/Memory Center locale và presentation — R211

```ini
SPEC_ID=WEBAPP-E0-MEMORY-CENTER-LOCALE-R211
STATUS=LOCAL_SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
SCOPE=Web App standalone /notes, /notes/<id>, /reminders
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

Đưa toàn bộ chữ cố định của Notes/Memory Center qua catalogue `memory.*` cân
bằng VI/EN/ZH, giữ đúng cấu trúc thao tác của Web App và không biến dữ liệu
người dùng hoặc dữ liệu máy chủ thành bản dịch trình duyệt.

## Phạm vi và hợp đồng được bảo vệ

Tệp thuộc lát R211:

- `static/portal/portal.js`
- `static/portal/portal-i18n.js`
- `tests/memory-center-locale-presentation.test.mjs`

Route giữ nguyên:

- `/notes`, `/notes/<id>` và `/reminders`.

Action/field/attribute giữ nguyên:

- `memory-note-create`, `memory-note-update`, `memory-note-archive`,
  `memory-note-restore`, `memory-note-restore-version`, `memory-note-filter`;
- `memory-reminder-create`, `memory-reminder-update`,
  `memory-reminder-complete`, `memory-reminder-pause`,
  `memory-reminder-resume`, `memory-reminder-cancel`, `memory-reminder-filter`;
- `data-memory-note-id`, `data-memory-note-revision`,
  `data-memory-reminder-id`, `data-memory-reminder-revision`.

Không thuộc phạm vi: Bot/Core, Telegram, provider, ví/Xu, PayOS, production
data, VPS, deploy, backend contract hoặc motion runtime.

## Thay đổi đã khóa

- Chuẩn hóa priority, repeat rule, reminder state và event label qua
  `memoryText()` với fallback VI an toàn.
- Localize form ghi chú, bộ lọc, phân trang, danh sách, chi tiết, lịch sử,
  khôi phục, lời nhắc liên kết và ranh giới dữ liệu.
- Localize form tạo/sửa lời nhắc, trạng thái quá hạn, các nút vòng đời và
  bảng hoạt động an toàn.
- Thêm catalogue 139 khóa `memory.*` cân bằng VI/EN/ZH.
- Giữ nguyên tiêu đề, nội dung, thẻ, danh mục, thời gian, ID, revision,
  receipt và các giá trị timezone do server/người dùng cung cấp.

## Checklist nghiệm thu

- [x] Keyset `memory.*` cân bằng VI/EN/ZH và đủ 139 khóa.
- [x] Renderer Notes/Reminders dùng helper locale cho fixed chrome.
- [x] Không còn fixed English cũ trong vùng Memory Center.
- [x] Route/action/field/capability/CSRF/idempotency/revision không đổi.
- [x] Dữ liệu động không bị dịch hoặc viết lại.
- [x] `node --check static/portal/portal.js` đạt.
- [x] `node --check static/portal/portal-i18n.js` đạt.
- [x] `node --test tests/memory-center-locale-presentation.test.mjs` đạt 3/3.
- [x] `node --test tests/*.test.mjs` đạt 423/423.
- [x] `git diff --check` đạt.
- [ ] Browser runtime QA trên VI/EN/ZH ở desktop/tablet/mobile.
- [ ] DOM/computed style/keyboard/focus/console/network/persistence trong
      runtime QA.

## Bằng chứng và giới hạn

Đây là `SOURCE_GREEN`: toàn bộ kiểm thử tĩnh và Node hiện có đạt, nhưng runtime
QA cô lập chưa được cung cấp nên chưa thể kết luận browser/live pass. Không có
provider call, wallet mutation, production mutation, commit, push, merge hoặc
deploy trong checkpoint này.

## Bước kế tiếp

Giữ R211 ở trạng thái browser acceptance mở. Khi có runtime, chạy `/notes`, mở
chi tiết và `/reminders` ở VI/EN/ZH trên 375/390/768/1440px. Chỉ sau khi ghi
nhận bằng chứng runtime mới đóng browser gate và chuyển sang R212
Campaign/Calendar/Approvals.
