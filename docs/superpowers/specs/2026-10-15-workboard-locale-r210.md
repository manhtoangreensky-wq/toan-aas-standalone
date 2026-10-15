# Workboard locale và presentation — R210

```ini
SPEC_ID=WEBAPP-E0-WORKBOARD-LOCALE-R210
STATUS=LOCAL_SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN
SCOPE=Web App standalone /workboard và /workboard/new
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
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

Chuẩn hóa toàn bộ chữ cố định của Workboard theo VI/EN/ZH mà không thay đổi
luồng dữ liệu, quyền, route, action, field, CSRF, idempotency hoặc revision.
Người dùng phải nhìn thấy cùng một cấu trúc bảng, danh sách, tạo việc,
checklist, lịch sử, hoạt động và lịch nhắc; chỉ ngôn ngữ hiển thị thay đổi.

## Phạm vi và hợp đồng được bảo vệ

Tệp thuộc lát R210:

- `static/portal/portal.js`
- `static/portal/portal-i18n.js`
- `tests/workboard-locale-presentation.test.mjs`

Hợp đồng giữ nguyên:

- `/workboard`, `/workboard/new` và route chi tiết `/workboard/<id>`;
- `data-portal-action="workboard-create"`, `workboard-update`,
  `workboard-state`, `workboard-checklist-update`,
  `workboard-schedule-create`;
- `data-workboard-item-id`, `data-workboard-item-revision`, checklist id,
  schedule attributes và toàn bộ payload do server cấp;
- dữ liệu động của người dùng/máy chủ (tiêu đề, mô tả, checklist, bản ghi,
  thời gian, mã guard, revision, receipt) không bị dịch hoặc viết lại.

Không thuộc phạm vi: Bot/Core, Telegram, provider, ví/Xu, PayOS, admin write,
production data, VPS, deploy, motion runtime hoặc thay đổi backend.

## Thay đổi đã khóa

- Thêm `workboardText()` làm cổng dịch cố định theo locale.
- Thêm nhãn locale cho trạng thái, mức ưu tiên, loại bản ghi liên kết, sự kiện
  và trạng thái lịch nhắc.
- Localize các vùng: hero/metadata, tab bảng–danh sách–tạo mới, bộ lọc,
  bảng Kanban, danh sách, phân trang, metrics, trạng thái rỗng/loading/failed/
  guarded, biểu mẫu tạo/sửa, checklist, lịch sử phiên bản, hoạt động, lịch
  nhắc, xác nhận lại/hủy lịch và chi tiết công việc.
- Bổ sung catalogue `workboard.*` cân bằng VI/EN/ZH (hơn 140 khóa) trong
  `WORKBOARD_MESSAGES`.
- Không để các chuỗi tiếng Anh cố định cũ như `Item editor`, `Workflow state`,
  `Version history`, `Private planning workspace`, `external reference` hoặc
  `record Inbox` lọt vào renderer Workboard.

## Checklist nghiệm thu

- [x] Keyset `workboard.*` cân bằng và không rỗng ở VI/EN/ZH.
- [x] Renderer dùng helper locale cho các vùng cố định chính.
- [x] Không đổi route, action, field, revision, capability hoặc payload.
- [x] Không dịch dữ liệu động do người dùng/máy chủ trả về.
- [x] Kiểm tra cú pháp `portal.js` và `portal-i18n.js`.
- [x] Bộ test tập trung R210 và các surface UI/locale liên quan đạt.
- [x] Toàn bộ Node suite hiện có đạt.
- [x] `git diff --check` đạt.
- [ ] Browser runtime QA trên VI/EN/ZH, desktop/tablet/mobile.
- [ ] Kiểm tra DOM thật, computed style, keyboard/focus, console/network và
      persistence trong runtime QA.

## Bằng chứng kiểm thử

```text
node --check static/portal/portal.js                         PASS (exit 0)
node --check static/portal/portal-i18n.js                    PASS (exit 0)
node --test <R210 + related UI/locale files>                 64/64 PASS
node --test tests/*.test.mjs                                 420/420 PASS
git diff --check                                             PASS (exit 0)
```

Worktree đã có thay đổi chưa commit từ các lượt UI/UX trước. Vì vậy chưa có
baseline sạch tương đương để kết luận `NEW_FAILURES=0`; kết quả trên là kiểm tra
fresh trên trạng thái hiện tại. Đây là `SOURCE_GREEN`, không phải browser/live
pass.

## Rủi ro và bước kế tiếp

Browser acceptance đang mở vì runtime QA cô lập chưa chạy. Sau khi có runtime,
chạy đúng flow:

`/workboard -> đổi bảng/danh sách -> /workboard/new -> mở chi tiết -> checklist /
lịch sử / lịch nhắc` ở cả ba locale và ít nhất 375px + 1440px.

Sau khi khóa R210, tiếp tục theo master plan: Notes/Memory Center, rồi
Campaign/Calendar/Approvals, các surface non-video còn chuỗi cố định, Video,
nghiệm thu UI/UX toàn app; chỉ sau đó mới xử lý motion. `LIVE_PASS=NO` cho đến
khi có bằng chứng runtime thật.
