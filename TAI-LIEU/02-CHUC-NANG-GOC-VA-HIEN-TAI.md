# Chức năng gốc và hiện tại — TOAN AAS Admin

## Tài liệu giai đoạn xây dựng đã tìm

- `docs/UX_APP_FIRST_REDESIGN.md`
- `docs/superpowers/specs/2026-08-02-aura-erp-data-surfaces-design.md`
- `docs/superpowers/plans/2026-07-29-admin-desktop-navigation.md`
- `docs/superpowers/plans/2026-07-29-admin-mobile-navigation.md`
- `docs/superpowers/specs/2026-08-03-admin-delivery-runtime-navigation-locales-design.md`
- Các spec Admin/Auth/Billing khác trong `docs/superpowers/specs/`.

Không tìm thấy một tài liệu gốc duy nhất liệt kê toàn bộ chức năng lúc mới xây: `INITIAL_FEATURE_DOC=NOT_FOUND`. Phạm vi tìm: `README.md`, `documentation/`, `docs/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`.

## Đối chiếu chức năng

| Trích nguyên văn nguồn (file:line) | Hiện tại + bằng chứng (file:line) | Trạng thái |
|---|---|---|
| “Swiss-modern productivity workspace with a compact, Odoo-like information hierarchy.” — `docs/UX_APP_FIRST_REDESIGN.md:16-17` | App switcher cấp 1 được dựng tại `static/portal/portal.js:9855` và gắn vào header tại `static/portal/portal.js:10525`. | ⚠️ Source đã triển khai; local rendered evidence đã tái sinh PASS; signed production vẫn NOT_TESTED |
| “Desktop (>=981px) \| Persistent sidebar with progressive disclosure” — `docs/UX_APP_FIRST_REDESIGN.md:56-59` | Admin hiện chiếu đúng một group active, còn app switcher và command palette giữ các route server cấp: `static/portal/portal.js:9837-9875`; contract current-group-only tại `tests/test_portal_navigation_ux_contracts.py:208-243`, shell contract tại `tests/test_admin_vi_en_shell_001_contracts.py:68-100`. | ⚠️ IA đã đổi so với mô tả gốc |
| “route, drawer, modal, toast and status feedback use the shared 140/220/420ms token family” — `docs/UX_APP_FIRST_REDESIGN.md:31-33` | Admin bị loại khỏi generic workspace enter tại `static/portal/portal.js:34158`; contract khóa hành vi tại `tests/test_motion_webapp_surfaces_001_contracts.py:142-147`. | ⚠️ Admin dùng ngoại lệ tĩnh; customer không thuộc thay đổi này |
| “The generic Users, Payments and Jobs adapters do not publish a server-side search/filter contract.” và “this PR does not add a generic local search” — `docs/superpowers/specs/2026-08-02-aura-erp-data-surfaces-design.md:14-18` | Data View nay có control local trên response đã được server cấp tại `static/portal/portal.js:29132`; search không dấu/status/count được kiểm tại `tests/test_admin_data_views_003_contracts.py:93-140`. | ⚠️ Mở rộng presentation local, không thêm API search |
| “It reports either the exact number of rows supplied in this response, or an explicit unavailable state when `items` is absent/malformed. It never treats missing data as zero.” — `docs/superpowers/specs/2026-08-02-aura-erp-data-surfaces-design.md:20-25` | Controls chỉ xuất hiện cho `items[]` server-granted và tách guarded/unavailable tại `tests/test_admin_data_views_003_contracts.py:56-90`; bảng readiness giữ đủ row tại `tests/test_admin_detail_dashboard_002_contracts.py:142-187`. | ✅ Còn dùng ở source contract |
| “Give signed internal ERP users a compact, server-authorized mobile dock instead of the customer Workspace dock.” — `docs/superpowers/plans/2026-07-29-admin-mobile-navigation.md:5-7` | Mobile Admin vẫn lấy projection từ navigation do server cấp tại `static/portal/portal.js:10201-10216`. | ✅ Còn dùng ở source contract |
| “Localize the fixed Delivery & Runtime area of the signed canonical Admin ERP in Vietnamese (`vi`), English (`en`), and Simplified Chinese (`zh`). The work covers server-authorized navigation chrome, page hero title/description, and server first-paint document title for the exact nine existing routes.” — `docs/superpowers/specs/2026-08-03-admin-delivery-runtime-navigation-locales-design.md:5-19` | Closed route/group map còn tại `static/portal/portal.js:26-39`; VI/EN/zh catalogue nằm tại `static/portal/portal-i18n.js:4961-4978`, `static/portal/portal-i18n.js:5421-5438`, `static/portal/portal-i18n.js:5881-5898`. Data View/Jobs purity mới được kiểm source tại `tests/test_admin_data_views_locale_purity_003_contracts.py:36-120`. | ⚠️ Source gate đạt; local rendered evidence đã tái sinh PASS; signed production vẫn NOT_TESTED |
| “This is a presentation redesign only. It does not alter Bot ownership, Core-Bridge contracts, wallet/PayOS authority, provider calls, CSRF/session rules, private-download checks, or PWA no-cache boundaries.” — `docs/UX_APP_FIRST_REDESIGN.md:88-90` | Data controls chỉ chiếu dữ liệu server-granted tại `static/portal/portal.js:29132`; guarded/unavailable không nhận controls theo `tests/test_admin_data_views_003_contracts.py:56-90`. | ✅ Ranh giới source vẫn giữ |

## Chỗ tài liệu cũ không còn đúng

1. “Desktop (>=981px) | Persistent sidebar with progressive disclosure” — `docs/UX_APP_FIRST_REDESIGN.md:56-59` → hiện tại sidebar chỉ chiếu đúng một group active, app switcher/palette vẫn giữ projection server-issued: `static/portal/portal.js:9837-9875`, `tests/test_portal_navigation_ux_contracts.py:208-243`, `tests/test_admin_vi_en_shell_001_contracts.py:68-100`.
2. “route, drawer, modal, toast and status feedback use the shared 140/220/420ms token family” — `docs/UX_APP_FIRST_REDESIGN.md:31-33` → Admin không chạy generic enter: `static/portal/portal.js:34158`, `tests/test_motion_webapp_surfaces_001_contracts.py:142-147`.
3. “this PR does not add a generic local search” — `docs/superpowers/specs/2026-08-02-aura-erp-data-surfaces-design.md:14-18` → năm Data View hiện có search/status/count local trên visible rows: `static/portal/portal.js:29132`, `tests/test_admin_data_views_003_contracts.py:93-140`.
4. “`adminHome.readiness.table.feature`, `adminHome.readiness.table.status`, `adminHome.readiness.table.adapter`” — `docs/superpowers/plans/2026-07-29-admin-erp-i18n-chrome.md:80` → bảng Chi tiết kết nối đã bổ sung STT 1-based, bỏ truncation, giữ row thứ 10 và render status locale hóa thay vì shared badge rỗng: `static/portal/portal.js:28733-28737`, `tests/test_admin_detail_dashboard_002_contracts.py:142-213`. Local rendered evidence đã tái sinh PASS; signed production vẫn `NOT_TESTED`.

## Rác và giới hạn cần biết

- Runtime vẫn là shared Portal bundle; batch chỉ thay các block Admin tại `static/portal/portal.js:9855`, `static/portal/portal.js:28733-28737` và `static/portal/portal.js:29132`, không refactor bundle.
- Locale gate hiện là source test tại `tests/test_admin_data_views_locale_purity_003_contracts.py:36-120`; local rendered evidence đã tái sinh PASS; signed production vẫn `NOT_TESTED`.
- Dashboard dùng snapshot thật, STT/10 rows và status text locale hóa tại `static/portal/portal.js:28737`, `tests/test_admin_detail_dashboard_002_contracts.py:142-213`; signed production vẫn `NOT_TESTED`.

## Bảng đọc nhanh

### Còn dùng được

- Server-authoritative Admin navigation: `static/portal/portal.js:9837-9875`.
- Exact-row/guarded data-surface contract: `tests/test_admin_data_views_003_contracts.py:56-90`.
- Closed locale route gate: `tests/test_admin_data_views_locale_purity_003_contracts.py:19-120`.

### Không còn đúng, cần bỏ qua

- All-groups sidebar trên desktop; hiện dùng đúng một active group, palette vẫn giữ toàn route server-issued: `tests/test_portal_navigation_ux_contracts.py:208-243`, `tests/test_admin_vi_en_shell_001_contracts.py:68-100`.
- Generic enter motion trên Admin; hiện bị guard: `tests/test_motion_webapp_surfaces_001_contracts.py:142-147`.
- Readiness ba cột/giới hạn cũ; hiện có STT, row thứ 10 và status locale hóa: `static/portal/portal.js:28737`, `tests/test_admin_detail_dashboard_002_contracts.py:142-213`; signed production vẫn `NOT_TESTED`.

### Không có trong tài liệu gốc

- App switcher cấp 1: `static/portal/portal.js:9855`, render tại `static/portal/portal.js:10525`.
- Workload/readiness snapshot, STT và status locale hóa: `static/portal/portal.js:28733-28737`, `tests/test_admin_detail_dashboard_002_contracts.py:142-213`; signed production vẫn `NOT_TESTED`.
- Local accent-insensitive search/status filter: `static/portal/portal.js:29132`, `tests/test_admin_data_views_003_contracts.py:93-140`.
- Whole-surface source purity: `tests/test_admin_data_views_locale_purity_003_contracts.py:19-120`; local rendered evidence đã tái sinh PASS; signed production vẫn `NOT_TESTED`.
