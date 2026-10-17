# R213-01 — Free Prompt Gallery locale/presentation audit

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Phạm vi

- Surface: `/free-prompt-gallery` trong Web App standalone.
- Chỉ sửa fixed UI chrome; không sửa Bot/Core, provider, ví/Xu, PayOS,
  production data, VPS, deploy, video hoặc motion.
- Dữ liệu prompt, tiêu đề, thẻ, ngành, mục tiêu, nền tảng, ID, revision,
  timestamp và receipt vẫn là dữ liệu server-owned, không dịch ở browser.

## Đã xử lý

1. Bộ lọc không còn hard-code tiếng Việt. Nhãn tìm kiếm, placeholder, help,
   nhóm mẫu, ngành, mục tiêu, nền tảng và các option “tất cả” đều đi qua
   `freePromptGalleryText()`.
2. Bổ sung 12 khóa tương ứng trong cả ba catalogue VI/EN/ZH, giữ keyset cân
   bằng và không đổi action/route/field contract.
3. Mở rộng test presentation để kiểm tra cả filter chrome, đồng thời tách dữ
   liệu mẫu server-owned theo locale nhằm tránh coi dữ liệu động là fixed UI.

## Bằng chứng kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| `node --check static/portal/portal.js` | PASS |
| `node --check static/portal/portal-i18n.js` | PASS |
| `node --test tests/free-prompt-gallery-locale-presentation.test.mjs` | 5/5 PASS |
| `node --test tests/*.test.mjs` | 430/430 PASS |
| `git diff --check` | PASS |
| Browser DOM/screenshot/console/runtime | `QA_RUNTIME_UNAVAILABLE` |

## FSM và delivery state

`READ -> CONTRACT -> BUILD -> REVIEW -> VERIFY -> REPORT`

```ini
TASK=R213-01-free-prompt-gallery-locale
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=UNCOMMITTED_WORKTREE
FILES_CHANGED=static/portal/portal.js;static/portal/portal-i18n.js;tests/free-prompt-gallery-locale-presentation.test.mjs;checklist/state/spec
TESTS=focused 5/5; Node suite 430/430; syntax 2/2; diff-check PASS
BASELINE_FAILURES=0 observed in executed Node suite
BRANCH_FAILURES=0 observed in executed Node suite
NEW_FAILURES=0
PROTECTED_COMPARATORS=route/action/field/capability/CSRF/idempotency/revision/server-owned data unchanged
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=UNKNOWN (QA runtime unavailable)
LIVE_PASS=NO
BLOCKERS=Isolated browser QA runtime has not been supplied; DOM/screenshot/console acceptance remains open.
```

## Trạng thái checklist

R213-01 đạt `SOURCE_GREEN_BROWSER_ACCEPTANCE_OPEN`. Chưa đóng cổng browser,
chưa chuyển sang R214 Video hay R216 Motion. Bước tiếp theo là inventory và
spec hẹp cho surface non-video kế tiếp sau khi giữ nguyên bằng chứng này.
