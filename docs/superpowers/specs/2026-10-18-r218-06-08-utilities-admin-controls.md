# R218-06/07/08 — Các sản phẩm còn lại và Admin

Root inventory B21–B34 phải được ánh xạ, kể cả legacy/không hỗ trợ/technical deferred.
Không lược bỏ các sản phẩm này vì chưa là AI tạo media. Chỉ thay UI/copy/local UX.

| ID | Nhóm | Control và trình bày cụ thể | Gate / evidence |
|---|---|---|---|
| UT-01 | Dịch | Text/voice/file, source auto, target search, giữ nguồn/hai chiều, start/stop, copy/export/history | Không nhầm đổi locale UI với target language |
| UT-02 | Content | Brief goal/channel/audience/tone, idea/caption/hashtag/hook/script/CTA, variants/edit/copy/save/version | User data không dịch; draft khác posted |
| UT-03 | Free/Prompt library | Search/filter/category/detail/copy/save, Meta/image/video prompt, publish pack | Nêu giới hạn miễn phí/quota, empty/loading/error |
| UT-04 | QR/avatar/rate/weather/download | Input preview/source, refresh/stale/error, save/download | Không gọi external API trong QA khi chưa phép |
| UT-05 | Notes | List/search/create/detail/edit/version/delete confirmation, reminder/time/repeat | Chỉ dữ liệu người dùng hiện tại; confirmation xóa |
| UT-06 | Documents | File list/order/add/remove, page range/compress choices, preview/confirm/result | Khớp Web validator hiện hành; không chép range Bot vượt contract |
| UT-07 | Assets | Upload status/progress/retry, folders/filter/type/size, preview/tải/quota/expiry | Owner/download readiness, no public URL leak |
| UT-08 | Projects/Workboard | Project list/detail/draft/assets/task dependency/status/assignee/dates/reminder/report | Chỉ nối reference có thật, không fake job |
| AP-01 | AutoPost source | 7 nguồn: topic/URL/affiliate/media/TOAN AAS video/image/plan idea | Picker dùng asset ID, giữ source lineage |
| AP-02 | Content plan/brand | Calendar/agenda, idea→draft→edit/preview→review; brand view/edit/logo/tone | Save feedback + versions/revision |
| AP-03 | Channels | List platform/status/connected/expiry/action, audience/target selection | OAuth/key/publish không mở trong wave UI |
| AP-04 | Queue/history | Draft/approved/scheduled/publishing/published/failed, filters/detail/cancel/review/retry | Đăng thật cần receipt/post link; refresh không submit |
| AP-05 | Affiliate/ads/metrics | Import/list/filter/product selection, budget/status/metrics/guide | Không chi tiền; số thiếu là unknown |
| AC-01 | Profile/security/session | Locale/profile/password controls/session/logout/help | Không làm mất login, stale-account cleanup |
| AC-02 | Packages/price/topup/history | Amount/method→review→QR, pending/admin status/history/detail | Quote/canonical price; approve/ledger/wallet giữ T0 |
| SP-01 | Support/feedback | “Trung tâm hỗ trợ khách hàng”, intake/attachment/context, list/detail/reply/status | Không thêm chữ “web”; link đúng request/job |
| SP-02 | Guide/Chat/community | Search/help theo context, chat mode/usage/stop/history, feedback/handoff | Không fake AI output, provider metadata ẩn |
| AD-01 | Admin nav | Một rail dọc module nhóm rõ, search/filter, badge có ý nghĩa | Owner all; role khác theo manifest/capability |
| AD-02 | Tables/charts | Header/filter/columns/list/cards dọc mobile, detail drawer, legend/labels/empty | Không dùng màu làm nguồn trạng thái duy nhất |
| AD-03 | Customer→Admin | Customer/request/job/asset/report/audit references, status + action errors | Chỉ record thật; thiếu bridge ghi T0 |
| AD-04 | Approval/finance UI | Review/reason/confirm/success/failure, actor/time/reference | Không duyệt tiền thật/đổi luật ví trong wave UI |
| AD-05 | Internal app | Cùng module/quyền/record, bố cục ưu tiên công việc và mobile | Không coi app nội bộ là bản ít quyền thay Web |

Bot anchors: bot.py:42324..42558,71003,123957..123987,184154..184416,
186004..186090,60020..60528,230617; services/autopost_ui.py:48,87,132..321.

## R218 Utilities/Content/Projects control checkpoint — 18/10/2026

Đã khóa presentation-level cho các surface đã có contract Web-native: Content Studio/detail,
Content Prompt Pack, Free Prompt Gallery, Free Tools, Memory Center/Reminder, Project Center
và Workboard. Content Prompt Pack có form một cột, gợi ý theo loại bản nháp, empty/result/
receipt, ranh giới không chạy engine và catalogue fixed chrome cân bằng VI/EN/ZH; bản VI không
còn các chuỗi giao diện như `Draft composer`, `Execution boundary`, `Provider call` hoặc
`Local deterministic draft`. Dữ liệu chủ đề, nội dung, tag, title, receipt và checklist vẫn
được giữ nguyên như dữ liệu owner/server, không dịch trong trình duyệt.

Evidence local ngày 18/10/2026:

```text
UTILITY_TARGETED=25/25 (Content Prompt Pack/Content Studio/Free/Memory/Project/Workboard)
NODE_CHECK=PASS (static/portal/portal.js, static/portal/portal-i18n.js)
GIT_DIFF_CHECK=PASS
```

Đây chỉ là khóa UI/UX fixed chrome và locale. UT-01/04/06/07, AutoPost, Account, Support,
Admin, runtime dữ liệu thật, browser/AX, provider, publish, wallet và live vẫn mở theo bảng
control ở trên; không suy diễn từ route hoặc HTTP 200.

## Bố cục / action state

Không xây catalogue toàn card rời mà mất “việc đang làm”. Header sản phẩm + hành động
chính + nội dung hiện tại; form một cột, bảng đọc được với sticky heading nếu cần.
Mobile list dọc, chi tiết hiện theo yêu cầu; các filters bổ sung có disclosure.
Mỗi action có loading/retry/forbidden/empty/success và báo cáo tham chiếu nếu có record.

## Kiểm không sót

Từng ID chia nhiều control ledger theo R218-00. Menu Bot và Web không trùng một-một:
cần ghi explicit disposition cho duplicate/legacy/admin-only/technical gap.
Đếm classified source controls và unclassified; chỉ đóng completeness khi unclassified=0
trong inventory đã chốt, không dùng số route làm bằng chứng.

## Verify / scope

### AD-02-THEME — preference + CSS core surfaces

- Allowed source: `static/portal/portal-theme.js`, `static/portal/portal-theme.css`;
  test `tests/portal-admin-theme-preference.test.mjs`; QA driver ngoài repo
  `qa/r218-voice-inventory/admin-probe.cjs --theme`. Không sửa renderer/auth/API,
  route-engine, billing, provider, DB, manifest hay service-worker.
- Policy mặc định Admin Light từ visual-reset cũ được giữ. Lỗi là luôn ép Light
  kể cả khi người dùng chọn Dark/System, không phải bản thân default Light.
- Admin `toan-aas-admin-theme-v2` lưu riêng; customer key không đổi. System preference
  Admin phải lưu được qua reload và nghe media change; explicit Dark/Light không
  bị media change ghi đè. Storage unavailable chỉ mất persistence, không khóa control.
- Dùng nút theme đã có, hiển thị/keyboard/label theo locale; target ≥44×44. Không
  reload hay remount form khi đổi theme. Mọi `meta[name=theme-color]` đồng bộ với
  selected theme, không phụ thuộc media attribute còn lại.
- CSS chỉ thêm nhánh Admin dark, dùng palette navy/teal đã có, không obsidian/đen.
  Light giữ canvas/thẻ/bố cục; CTA và chữ selected nav dùng teal đậm có sẵn cho AA.
- Verify: Node 17/17 + full Node 704/704. Browser localhost 24 route/locale/viewport
  cases, mỗi case kiểm dark/light/system, reload preference, email preservation,
  focus/target, mobile drawer/Escape, headers bảng chẩn đoán, màu nền và contrast.
  375/390/768/1440 × VI/EN/ZH × home/login. Min measured contrast 7,61 dark / 5,24
  light, zero page/console/external/write/unknown API/overflow. Không chứng minh
  backend login, actual role/data, mọi module động hoặc production LIVE.

### AD-01A / AD-03A — Admin overview shortcuts và count truth

- Allowed: `static/portal/portal.js` (`renderAdminOverview`),
  `static/portal/portal-i18n.js` (`adminHome.metrics.unknown`, `diagnostics.summary`),
  `tests/admin-overview-operational-shortcuts.test.mjs`, checklist và tài liệu.
- Không đổi API/RBAC/route-engine/wallet. Mỗi banner/lối tắt dùng exact module
  đã được manifest máy chủ cấp; `/admin/jobs/failed` kế thừa module `/admin/jobs`
  qua helper hiện hành, không tự cấp prefix `/admin/*`.
- Chỉ `counts.pending_topups` là số nguyên không âm mới là total. Null, thiếu,
  boolean, chuỗi, số âm/lẻ → unknown; `0` → known zero. List page không là total.
- Unknown label, diagnostics theo VI/EN/ZH; chữ unknown dùng token Admin và
  contrast ≥4,5:1. Không thêm nút approve/credit hoặc gọi HTTP write.
- Verify: `node --test tests/admin-overview-operational-shortcuts.test.mjs` →
  18/18. Local probe `node ../qa/r218-voice-inventory/admin-probe.cjs --shortcuts`
  → 18 cấu hình × 6 trạng thái, 108 trạng thái; count/route/focus/overflow/locale
  có assertion riêng. Đây không phải backend RBAC/financial/LIVE evidence.

### AD-02-MOBILE-DATA — thẻ dữ liệu dọc trên điện thoại

- Allowed source: `static/portal/portal-theme.css` trong lớp Admin ở `<=560px` và
  `tests/admin-mobile-data-harmony-source.test.mjs`. Không sửa renderer, API/RBAC,
  finance/top-up, route-engine, customer palette, database hoặc capability.
- Desktop/tablet giữ semantic table; điện thoại trình bày mỗi record thành một thẻ dọc,
  giữ nhãn cột từ `thead` trong cây trợ năng, cho badge/trạng thái/action tự xuống dòng,
  bỏ lời nhắc cuộn ngang và vô hiệu hóa sticky cột đầu chỉ trong thẻ Admin.
- Acceptance: VI/EN × sáng/tối × 390/1440px; vùng bảng không vượt viewport trên 390px,
  bảng vẫn có role `table` và đủ heading, lọc/empty/clear/focus, Enter chọn record/mở
  inspector; desktop còn display `table`; không có lỗi console, request ngoài, write hoặc
  API lạ. Dữ liệu là fixture tổng hợp chỉ đọc, không dùng bản ghi khách hàng thật.
- Evidence đã ghi: test nguồn `3/3`, toàn bộ Node `706/706`; browser fixture trước đó
  `8/8`, gồm vùng nội dung bảng `318/318px`; ảnh ở
  `../qa/r218-voice-inventory/admin-data-mobile-qa-{vi,en}-{light,dark}.png`.
  Lượt trong sandbox trước đó không mở được Edge. Rerun mới ngày 19/10 dùng profile Edge
  tạm ngoài sandbox đạt 8/8, headings 8/8 còn trong AX, filter/empty/clear-focus/Enter-
  inspector đạt; page/console/external/write/unknown API đều 0. Artifact mới
  `../qa/r218-voice-inventory/admin-data-reviewed.json`, SHA256
  `8995d3f057bffe687850967652fbc1de7799dc3d1d0068bc3590c87ce2e0c636`.
  Fixture được project sau hydrate vì bridge unavailable phải xóa dữ liệu chưa xác minh.
  Đây vẫn là presentation fixture. CI run `39212998609` xanh
  trên remote SHA `1730ea4`, nhưng không chứa hai tệp source/test còn local.
- Giới hạn: không đóng AD-02 tổng; fixture không chứng minh module/role/RBAC, records
  thật, charts, approval, backend hay LIVE. Các phần đó giữ mở theo checklist.

### AD-02-STATE-LOCALE — nhãn trạng thái chung

Rerun trên xác minh `failed_no_charge` dùng fallback VI trong bản EN. Mapping chung
thiếu 14 state; bảng nhãn và RED/GREEN gate nằm tại
`2026-10-19-r218-admin-state-locale.md`. Thứ tự: mobile presentation → state locale →
role/module coverage. Chỉ thêm mapping/catalogue/test; giữ enum/payload/API/CSS.

Spec state locale đã được Codex nghiệm thu local ngày 19/10: RED pass1/fail6 → GREEN7/7,
full Node713/713, browser12/12 với state đúng locale. Không đổi enum/function hay
backend/integration/workflow. CI/deploy/LIVE và các module/role khác vẫn mở.

### AD-02-DYNAMIC-CHART-PROJECTION — biểu đồ/chú giải từ dữ liệu máy chủ

Mục tiêu của lát này là bổ sung cách trình bày biểu đồ tùy chọn trong Admin Generic mà
không biến dữ liệu thiếu thành số liệu giả và không mở quyền ghi. `data.chart` là một
projection do máy chủ cấp trong cùng read model với `items`; nếu response bị
`compatibility_guarded`, chart malformed hoặc vượt giới hạn thì renderer không hiển thị
chart. Projection nhận 1–12 điểm, mỗi điểm có nhãn và số không âm trong giới hạn an toàn;
legend tối đa 6 mục và chỉ dùng các tone `primary/success/warning/danger/muted`. Chiều
rộng thanh được tính từ cực đại của chính các điểm đã cấp, không gọi API và không lấy số
từ các trường khác.

`renderAdminDataChart()` tạo figure có tên/mô tả, danh sách điểm có giá trị văn bản và
`role="img"`/`aria-label` cho từng thanh, cùng chú giải văn bản; `renderAdminDataSurface()`
chỉ chèn figure khi projection hợp lệ. CSS dùng token palette xanh hiện có, không thêm
transition/animation/gradient. Catalogue `adminDataView.chartKicker/chartLegend` phải
cân bằng VI/EN/ZH.

Gate local: `tests/admin-data-chart-source.test.mjs` 3/3; focused Admin 14/14; full
Node 728/728; hai `node --check` và `git diff --check` đạt. Browser fixture chưa chạy
được trong sandbox do Playwright không tạo thư mục tạm; vì vậy chỉ đánh dấu lát source/
presentation local, không đóng AD-02 tổng, role/RBAC, records thật, approval, backend,
CI, production hoặc LIVE.

### AD-03-RECORD-REFERENCES — liên kết hồ sơ chỉ đọc trong Inspector

Lát này chỉ hoàn thiện cách trình bày liên kết giữa một record Admin và hồ sơ liên quan;
không tạo bridge nghiệp vụ mới. Renderer chỉ đọc trường tùy chọn
`admin_record_references` trong record đã được máy chủ cấp. Projection fail-closed khi
không phải mảng, giới hạn tối đa 6 phần tử, loại chỉ nhận `request`, `job`, `asset`,
`report`, `audit`, ID chỉ nhận ký tự an toàn trong giới hạn, còn `label` bị giới hạn độ
dài. Mỗi reference phải trỏ tới path nội bộ hợp lệ theo allowlist `/admin`, `/jobs`,
`/assets`, `/reports`, `/audit`; URL ngoài, scheme, `//`, `\\`, dot-segment (`..`/`%2e`), path rỗng hoặc path
không khớp đều bị loại.

`renderRowsTable()` giữ metadata `data-admin-record-references` trên dòng. Inspector
hiển thị một vùng “Liên kết hồ sơ” khi projection hợp lệ; link được tạo bằng DOM API,
không dùng HTML string và không thêm nút ghi, approve, credit, publish hay download.
Nhãn loại reference lấy từ catalogue VI/EN/ZH, không dịch ID, mã kỹ thuật hoặc tên riêng.
Không có `fetch`, mutation, provider call, capability grant hay thay đổi route/RBAC.

Allowed files của slice này:

- `static/portal/portal.js` — sanitize/allowlist và render projection.
- `static/portal/portal-theme.css` — bố cục vùng reference theo token Admin hiện có.
- `static/portal/portal-i18n.js` — nhãn loại reference VI/EN/ZH.
- `tests/admin-data-reference-source.test.mjs` — source contract 2/2.
- checklist/state và tài liệu này.

Gate local: source test `2/2`; focused Admin regression sau reference slice `16/16`;
full `node --test` `730/730`; `node --check static/portal/portal.js`,
`node --check static/portal/portal-i18n.js` và `git diff --check` đạt. Browser fixture
chưa chạy được vì Playwright không tạo được thư mục tạm (`mkdtemp ENOENT`), nên không
đánh dấu browser/CI/production/LIVE. Đây chỉ là local read-only presentation; AD-03
tổng vẫn cần role/module fixture, record thật và bridge request→job→asset→report→audit
do server cấp trước khi có thể đóng.

### AD-03-ROLE-MODULE — projection manifest theo quyền máy chủ

Lát này khóa lớp trình bày nhóm/phân hệ Admin từ manifest đã được máy chủ cấp; không
phải là bộ suy quyền nằm trong browser. Renderer chỉ xử lý khi `read_state=ready` và
chỉ nhận các module có route `/admin` hoặc `/admin/...`. Ngoài route gốc, route trùng,
`//` nội bộ, `\\` và dot-segment thường/mã hóa (`..`/`%2e`) đều bị loại trước khi
đưa vào `routes`, sidebar, mobile dock hoặc command palette. Mỗi module chỉ nhận
trạng thái trong allowlist; `available`, `canonical_read` và `web_native` được trình
bày như `read_only`, còn trạng thái lạ chuyển thành `guarded`.

Không dùng `context.isAdmin`, browser role, ID nhóm, capability hoặc prefix
`/admin/*` để cấp thêm quyền; không mở route mới, không fetch, không ghi, không gọi
provider và không thay đổi RBAC/backend. Route đích vẫn tự kiểm tra signed session và
authority ở nơi riêng. Khi manifest không ở `ready`, projection trả nhóm/routing
rỗng và các cờ authority presentation về trạng thái fail-closed.

Allowed files của slice này:

- `static/portal/portal.js` — route fence riêng cho Admin role/module projection.
- `tests/admin-erp-navigation-projection.test.mjs` — hai test manifest `ready` và
  fail-closed `loading` (`2/2`).
- checklist/state và tài liệu này.

Gate local: projection `2/2`, focused Admin `18/18`, full `node --test` `732/732`,
`node --check static/portal/portal.js`, `node --check static/portal/portal-i18n.js`
và `git diff --check` đạt. Browser fixture vẫn bị chặn bởi Playwright
`mkdtemp ENOENT`; vì vậy chưa đánh dấu browser/CI/production/LIVE. Đây chỉ là
projection UI chỉ đọc; AD-03 tổng vẫn cần role/RBAC thật, record thật và bridge
request→job→asset→report→audit do server cấp.

### AD-03-RECORD-CHAIN — chuỗi hồ sơ chỉ đọc trong Inspector

Lát này biến danh sách reference đã được server cấp thành một chuỗi đọc dễ theo dõi
theo thứ tự cố định `request → job → asset → report → audit`. Không tự suy ra record
không có trong payload: mắt xích thiếu thì không được tạo placeholder hoặc số liệu;
trùng loại chỉ giữ reference đầu tiên sau projection. Trước khi render Inspector,
JSON trên dòng được chiếu lại qua `adminDataReferenceProjection()` để giữ cùng
allowlist kind, ID, nhãn và path, bao gồm chặn URL ngoài, `//`, `\\` và dot-segment.

Chuỗi được tạo bằng DOM API trong một danh sách dọc, dùng nhãn kind từ catalogue
VI/EN/ZH và chỉ liên kết tới path nội bộ đã qua projection. Không có fetch, mutation,
approve, credit, publish, download, provider call, capability grant hoặc bridge
nghiệp vụ mới; phần này chỉ làm rõ record liên quan đã được máy chủ cấp.

Allowed files của slice này:

- `static/portal/portal.js` — projection thứ tự chuỗi và Inspector DOM.
- `static/portal/portal-theme.css` — danh sách chuỗi dọc theo token Admin hiện có.
- `static/portal/portal-i18n.js` — nhãn “chuỗi hồ sơ” VI/EN/ZH.
- `tests/admin-data-reference-source.test.mjs` — projection/Inspector source contract
  và thứ tự chuỗi trong test `2/2`.
- checklist/state và tài liệu này.

Gate local sau slice: reference `2/2`, focused Admin `18/18`, full `node --test`
`732/732`, hai `node --check` và `git diff --check` đạt. Browser fixture vẫn
`NOT_RUN` vì Playwright `mkdtemp ENOENT`; record thật, bridge request→job→asset→
report→audit, CI, production và LIVE chưa được xác minh.

Focused renderer/action tests giữ route/action/revision/CSRF/ownership contract.
Browser fixture customer/admin/department denied; VI/EN/ZH, light/dark, 375/768/1440.
Không submit nạp/approval/publish/ads production. Các actions đó T0 sau UI/motion và lệnh riêng.

### AD-03-RECORD-BRIDGE — allowlist reference từ server tới Web Inspector

Lát cầu nối này chỉ mở đúng trường `admin_record_references` trên payload Admin
đã qua `admin_read=True` và role Admin do server kiểm tra. `copyfast_api.py` chỉ
giữ tối đa 6 reference thuộc `request`, `job`, `asset`, `report`, `audit`; ID và
nhãn bị giới hạn; path chỉ nhận các họ route nội bộ `/admin`, `/jobs`, `/assets`,
`/reports`, `/audit`. Path ngoài, `//`, `\\` hoặc dot-segment thường/mã hóa bị
giữ metadata với path rỗng; kind/ID sai hoặc payload vượt giới hạn bị loại toàn
bộ. Mục này không tạo reference từ ID khác, không ghép request/job,
không gọi thêm bridge và không cấp capability.

Reference cấp ở record đơn và từng `items[]` đều được chuyển qua cùng allowlist;
payload của account không phải Admin không nhận trường này. Frontend vẫn chiếu lại
allowlist trước khi tạo DOM link và chuỗi `request → job → asset → report → audit`.

Allowed files của slice này:

- `copyfast_api.py` — server-side read-only projection.
- `tests/test_copyfast_bridge.py` — allow/deny/path-hardening contract.
- checklist/state và tài liệu này.

Gate local: `python -m py_compile copyfast_api.py tests/test_copyfast_bridge.py`,
targeted `test_copyfast_bridge.py`, source reference `2/2`, `node --check` hai
Portal JS và `git diff --check`. CI phải chạy lại trên đúng HEAD; browser fixture
record thật, production và LIVE chưa được đánh dấu. AD-03 tổng vẫn mở cho tới khi
server cấp record thật và có evidence role/RBAC + bridge request→job→asset→report→audit.
