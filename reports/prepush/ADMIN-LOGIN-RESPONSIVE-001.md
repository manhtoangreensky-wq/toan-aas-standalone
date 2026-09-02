# Pre-push report — ADMIN-LOGIN-RESPONSIVE-001

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Identity

```text
REPOSITORY=manhtoangreensky-wq/toan-aas-standalone
BASE_SHA=94dbd2825889f4ff71d201465870c182075a0282
BRANCH=fix/admin-login-responsive-001
RUNTIME_IMPLEMENTATION_FILES=2
DOCUMENTATION_TESTER_FILES=7
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

## 1. Review code và hành vi vận hành

Runtime diff:

1. `static/portal/portal-theme.css` — một block `ADMIN-LOGIN-RESPONSIVE-001`, Admin-scoped.
2. `tests/test_admin_login_responsive_001_contracts.py` — test portable, exact DOM/rule-body/scope/motion contracts.

Root cause được đo: base `.portal-shell--auth .portal-main` cap `560px`; Admin article nằm bên trong main và không có route-scoped desktop override. R1 dùng selector descendant không thể match; R2 mở mobile rule global và `git diff --check` fail. Primary dùng fresh BASE và không nhập candidate cũ. Independent review tìm thêm breakpoint capacity gap; corrective hiện dùng `≤840` stacked / `≥841` two-column và có numerical capacity assertion.

Fresh final gate trước report:

```text
PYTEST=12 passed, 1 StarletteDeprecationWarning, exit 0
TESTER_WORKSPACE=30 passed, 1 Windows-only POSIX mode case deselected, exit 0
NODE_CHECK=0
GIT_DIFF_CHECK=0
RUNTIME_CHANGED_PATHS=2
ARTIFACTS=0
FORBIDDEN_SECRET_MATCHES=0
```

Browser local:

| Viewport | Layout | Intro/card | Overflow/outside | Input/min target |
|---|---|---:|---:|---:|
| 1920×1080 | 2 cột | 504/616px | 0/0 | 15px/≥44px chính |
| 1440×900 | 2 cột | 506/619px | 0/0 | 15px/≥44px chính |
| 1024×768 | 2 cột | 411/502px | 0/0 | 15px/≥44px chính |
| 768×900 | 1 cột | hidden/648px | 0/0 | 15px/≥44px chính |
| 390×844 | 1 cột | hidden/326.4px | 0/0 | 16px/44px |
| 360×800 | 1 cột | hidden/296px | 0/0 | 16px/44px |

Light/dark geometry không đổi; system restored; console `0`; keyboard focus visible. Public `/login` và `/register` ở 390px có Admin marker false, overflow/outside `0`.

Independent review corrective:

```text
FIRST_REVIEW=FAILED_IMPORTANT breakpoint 769 too early
SOURCE_RECHECK=effective padding 16px/side; danger approximately 769–804
CORRECTIVE_BREAKPOINT=stacked through 840; two-column from 841
CAPACITY_AT_841=main 793 - padding 32 = 761px; grid minimum 280+420+25.23 = 725.23px; spare 35.77px
BOUNDARY_BROWSER=requested 769/804/805/821/840/841; backend reported 770/804/806/822/840/842
BOUNDARY_RESULT=stacked through 840; two-column at 842; overflow/outside 0/0 for all six
EXACT_841_CAPACITY_STATIC=761px content versus 725.23px minimum, spare 35.77px
```

Tài liệu vận hành được cập nhật:

- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`
- `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`

## 2. Đối chiếu chức năng gốc

`INITIAL_FEATURE_DOC=NOT_FOUND` theo bounded search đã ghi trong `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`: README, docs UX/migration, `123` plans và `139` specs theo inventory P0-05B. Không bịa danh sách gốc. Dòng Admin login mới ghi rõ candidate local, không biến thành production claim.

## 3. Tester workspace

- Nguồn case: `KIEM-THU/DANH-SACH-CASE.md`; thêm đúng `WA-39`.
- Issue templates hiện có: `01-case-test.yml`, `02-bao-loi.yml`.
- Tracker hiện hành: `https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/412`.
- Independent Tester phải review exact BASE/HEAD, two-file runtime diff, fresh `11P`, Browser matrix và protected public Auth trước khi `ACCEPTED`.
- GitHub labels/tracker đã được readback ngay trước push; không tạo hàng loạt thẻ/project. Existing Tester Project attachment từng được readback ở P0-05E; fresh project API hiện thiếu `read:project` scope.

Fresh GitHub readback 03/09/2026:

```text
LABEL_COUNT=22
REQUIRED_TESTER_LABELS=12/12
TRACKER_ISSUE=#412 OPEN
TRACKER_LABELS=case-test,chờ-test
TRACKER_URL=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/412
PROJECT_TITLE_PRIOR_ACCEPTED=TOAN AAS Web App · Tester P0
PROJECT_FRESH_READBACK=BLOCKED_MISSING_read:project_SCOPE
```

Không chạy `gh auth refresh`; quyền project không cần thiết để push code. Tester workspace/Issue vẫn usable; readiness JSON giữ project title đã được nghiệm thu trước đó và ghi external mutation `0`.

```text
TESTER_CASE=WA-39
TESTER_STATUS=PASS_0_CRITICAL_0_IMPORTANT_0_MINOR
TESTER_EVIDENCE=C:/Users/toann/Documents/Codex/2026-07-10/1-ngu-n-ch-nh-v/evidence/admin-login-responsive-001-primary
PUSH_GATE=READY
```
