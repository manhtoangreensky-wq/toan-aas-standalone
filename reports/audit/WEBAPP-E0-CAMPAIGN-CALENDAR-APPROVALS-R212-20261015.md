# Báo cáo R212 — Campaign / Calendar / Approvals locale và presentation

Đang đọc và áp dụng skill owner-governed-codex cho task này.

```text
TASK=WEBAPP-E0-CAMPAIGN-CALENDAR-APPROVALS-LOCALE-R212 / SOURCE REVIEW
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1 (workspace uncommitted)
FILES_CHANGED=R212 slice: static/portal/portal.js; static/portal/portal-i18n.js; tests/campaign-planner-locale-presentation.test.mjs; checklist/state/spec/report
PRE_EXISTING_DIRTY=worktree đã dirty từ các checkpoint UI/UX trước; không hoàn nguyên hoặc gán tệp ngoài lát R212 cho task này
TESTS=node --check portal.js -> exit 0; node --check portal-i18n.js -> exit 0; R212 focused -> 2/2 PASS; node --test tests/*.test.mjs -> 425/425 PASS; git diff --check -> exit 0
BASELINE_FAILURES=NOT_RUN (không có worktree sạch tương đương; trạng thái đầu vào đã dirty)
BRANCH_FAILURES=0 trong các lệnh trên
NEW_FAILURES=UNKNOWN (baseline không so sánh được; không suy diễn thành PASS)
PROTECTED_COMPARATORS=campaignUi keyset 204 VI/EN/ZH -> PASS; stale fixed-copy scan -> PASS; route/action/field/revision contracts -> PASS; syntax -> PASS; diff-check -> PASS
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=NOT_AVAILABLE
LIVE_PASS=NO
BLOCKERS=QA_RUNTIME_UNAVAILABLE; chưa có DOM/computed-style/keyboard/console/network/persistence evidence
```

## Đã xử lý

R212 đã hoàn tất source slice cho năm surface Campaign:

- `/campaigns`: bảng kế hoạch, trạng thái bảo vệ/đang tải/lỗi/rỗng, metrics,
  thư viện và nút tạo;
- `/campaigns/new`: form brief, CTA, mục tiêu, nền tảng, mốc nội bộ và ranh
  giới thực thi;
- `/campaigns/<id>`: chi tiết, thông tin trạng thái, ghi chú, chỉnh sửa và
  chuyển trạng thái;
- `/calendar`: bộ lọc, đổi tháng, lịch tháng, agenda, ngày chưa có mốc và
  thông báo giới hạn dữ liệu;
- `/approvals`: metrics, danh sách tự rà soát, trạng thái rỗng và liên kết
  hàng duyệt chính thức.

Catalogue `campaignUi.*` cân bằng 204 khóa ở cả VI/EN/ZH. Chỉ fixed chrome đi
qua `campaignText()`; tiêu đề kế hoạch, brief, ghi chú, URL, ID, timestamp,
timezone, revision, receipt và trạng thái server vẫn giữ nguyên dữ liệu gốc.

## Quyết định trạng thái

`wa35_r212_status=CAMPAIGN_CALENDAR_APPROVALS_SOURCE_GREEN;BROWSER_ACCEPTANCE_OPEN`

`wa35_r212_verify=FOCUSED_2_PASS;NODE_ALL_425_PASS;JS_CHECK_PASS;DIFF_CHECK_PASS`

R212 được khóa ở source gate và checklist đã chuyển thứ tự tiếp theo sang R213.
Chưa chuyển sang motion; motion vẫn chỉ bắt đầu sau khi R215 UI/UX acceptance
được đóng.

## Giới hạn

QA runtime chưa khả dụng nên chưa có ảnh chụp, DOM snapshot, kiểm tra bàn phím,
computed style, console/network hoặc persistence. Vì vậy `LIVE_PASS=NO`; không
được diễn giải `SOURCE_GREEN` thành đã merge, deploy hoặc live.
