# Checklist tổng WebApp standalone — UI/UX, product parity, locale và motion

**Checklist ID:** `WEBAPP-UIUX-PARITY-20261016`
**Plan:** `docs/superpowers/plans/2026-10-16-webapp-uiux-product-parity-master-plan-r217.md`
**Baseline remote:** `f59eacf63a49534854dc7cde06e5baed6546dc58`
**PR liên quan:** #647 — đã merge `bc0d089`; deploy WebApp `39036918159` đã thành công, live recheck tiếp tục mở
**Ngày cập nhật:** 2026-10-17

## Cách đọc trạng thái

- `[x] CLOSED_WITH_EVIDENCE` — có source/runtime evidence đủ cho đúng phạm vi.
- `[~] SOURCE_GREEN_RUNTIME_OPEN` — source gate xanh nhưng chưa có runtime/live evidence.
- `[~] LIVE_DRIFT_OPEN` — source đã sửa, runtime còn bundle/triển khai cũ hoặc lệch.
- `[ ] TODO` — chưa thực thi.
- `[!] BLOCKED` — thiếu điều kiện bắt buộc; không được giả PASS.
- `[→] DEFERRED` — ghi nhận để không bỏ sót, mở bằng task/Owner gate riêng.

## 0. Hàng rào chung

- [x] Chỉ phạm vi WebApp standalone; Bot/Core là nguồn tham chiếu parity, không sửa trong
      checklist này.
- [x] Giữ màu xanh dương/xanh ngọc và nền tối xanh navy; không dùng đen/tím làm brand.
- [x] Không đổi route, action, field, capability, CSRF, idempotency, revision hoặc dữ liệu
      động trong các wave UI/UX.
- [x] Không provider call, wallet/Xu mutation, PayOS mutation, production data mutation,
      merge hoặc deploy trong lượt lập plan.
- [x] Fixed chrome VI/EN/ZH phải một ngôn ngữ; tên riêng/danh từ được phép giữ nguyên.
- [~] QA runtime cô lập trên máy dev vẫn thiếu dependency; runner CI riêng
      `scripts/ci/run_authenticated_qa_matrix.py` đã chạy thành công với DB SQLite tạm,
      fixture theo locale và không bật provider/wallet. Ma trận R217-11 đã được đóng bằng
      artifact CI; runtime local vẫn giữ mở riêng cho lần đo trace/FPS nếu có môi trường phù hợp.
- [ ] Antigravity handoff chỉ được đánh dấu PASS khi có log thật; không dùng báo cáo giả.

## 1. W0 — Baseline và evidence ledger

- [~] CI run `39005167126` trên `66684e8` dừng tại bước xác minh migration provenance:
      fingerprint ghi nhận `32c98444d7b3`, source hiện tại `3b9657865e57` (`284` tệp).
      Các bước test tiếp theo chưa chạy. Đã chạy chế độ `--refresh-web-evidence` chỉ cho Web
      trên source commit `e44080e`, tạo fingerprint `af3a77086075` khớp inventory/preflight;
      không quét Bot và không thay đổi runtime. Kiểm chứng tiếp trên `646fb0b` phát hiện
      fingerprint đã lệch (`af3a77086075` so với source `7d6f0a4da90c`, `284` tệp); vì vậy
      không đánh dấu provenance đạt. Làm mới lại trên HEAD sạch sau lần cập nhật checklist/state,
      rồi xác minh và chờ CI mới; các bước test sau provenance vẫn chưa chạy.
- [x] Làm mới riêng Web provenance trên `0d96560490288917530b53e69979b0c8b7aa7642`; xác minh
      tại chỗ đạt: audit SHA khớp HEAD, quan hệ `ancestor`, fingerprint
      `de8d38a9fc9c7cf37e41cdb53fc4420becd20d820732695fcb8ca08ac74006aa`, `284` tệp.
- [~] CI trên candidate đã xác minh chưa chạy/chưa có kết quả; chỉ run mới của PR #647 sau push
      mới khép gate. Không dùng run cũ trên `66684e8` làm bằng chứng cho HEAD hiện tại.
- [!] **CI run `39023945997` trên `3e5cd36` — 2026-10-17:** `Verify Web App` dừng ở
      `Verify committed migration evidence` vì provenance ghi fingerprint cũ
      `bf9084e4509b` trong khi 284 tệp Web đủ điều kiện trên HEAD hiện tại cho fingerprint
      `c9bbeab9d557`. Đã làm mới riêng `reports/migration/preflight.json` và
      `reports/migration/web_inventory.json` theo đúng HEAD `3e5cd367a48e8d673a16d5184b2a45946b3275b6`;
      kiểm chứng local trả `ok=true`, audit SHA khớp HEAD, quan hệ `ancestor`, fingerprint
      `c9bbeab9d5578d42e371a96945f805fe4cc2b2b053897becfc7693591dd59491`. Chưa ghi quality
      gate xanh cho đến khi CI mới chạy lại.
- [!] CI run `39005931284` trên `39460ee` đã chạy `288 passed, 1 failed`; lỗi duy nhất là
      `tests/test_p0_05d_tester_workspace.py::test_readiness_json_has_explicit_truth_and_file_metadata`:
      metadata của `KIEM-THU/DANH-SACH-CASE.md` còn `159` dòng/bytes/hash cũ trong khi file sau
      WA-49 có `160` dòng. Đã cập nhật đúng `lines=160`, `bytes=36583`, SHA-256
      `c2dbd8196fa7b2302656a67380ec8b1b9e01875fac666ce2774a1035c5b42cfa`; đã xác minh bằng
      Python read-only. Chờ quality gate mới để đóng lỗi; không thay đổi runtime.
- [!] CI run `39006585798` trên `d9e4fe2` đã dừng ở bước `Verify committed migration evidence`:
      evidence ghi `f590cd8df08a` nhưng source sau cập nhật checklist/state là `b11ca35d3e62`
      (`284` tệp). Đây là provenance drift do tài liệu được cập nhật sau lần refresh, không phải
      lỗi runtime. Đã giữ nguyên chất lượng source; cần chốt tài liệu này, refresh Web-only rồi
      verify lại trước khi tính quality gate xanh.
- [!] CI run `39007466336` trên `964ce47` đã qua provenance nhưng dừng ở
      `tests/test_p0_05d_tester_workspace.py`: metadata của `KIEM-THU/HUONG-DAN-TESTER.md` ghi
      `19269` byte/hash cũ trong khi file thực tế là `202` dòng, `19442` byte chuẩn LF, SHA-256
      `6a7b1df026ee816542e49ea9e1263ea0f265cdb7a952bae9a0d600be324eebaa`. Đã cập nhật metadata
      đúng; chờ quality gate kế tiếp, không đổi runtime.
- [x] CI run `39007843300` trên `1fe321b` đã chạy thành công: `Verify Web App` xanh,
      browser evidence artifact `10.7 MB`, digest `sha256:97607fe14b53f75f25eda7f0159b17996f6384a9e87c3dcbaec33d712f4a5f88`.
      Đây là bằng chứng quality gate của candidate trước batch Voice; warning Node 20 bị ép
      chạy trên Node 24 và Ubuntu runner sắp đổi phiên bản là cảnh báo môi trường, không phải
      lỗi source.
- [x] Đối chiếu remote: local cũ lệch; tạo worktree sạch từ `github/webapp-checklist-r116`.
- [x] Sau quality-gate failure `38958333812`, đã sửa provenance evidence: `284` eligible Web
      files; `preflight.json`, `web_inventory.json` và source hiện cùng fingerprint
      `ef1a6bd2b1400129cadbb10fdbb55884436d99da5c230687dc4166916b93f6e6`. Local Node
      reimplementation của audit verifier trả `match=true`; không sửa runtime source.
- [x] Ghi baseline HEAD `f59eacf63a49534854dc7cde06e5baed6546dc58` và PR #647.
- [x] Ghi rõ source gate gần nhất: full Node 469/469, focused gates xanh, syntax và
      `git diff --check` xanh theo R216.
- [x] Ghi rõ live không phải PASS: R216-H mobile landing drift, R216-L next-route auth
      locale drift, R216-P live icon chưa xác minh.
- [x] Ghi 31 capability/139 customer entrypoints/41 admin surfaces từ master inventory;
      phân biệt UI partial với real-output/bridge gap.
- [x] Chốt protected contracts và safety flags trong state YAML R217.

## 2. W1 — Shell, responsive và visual foundation — Spec R217-01

- [x] Source có skip link → `#portal-main`, `<main tabindex="-1">`.
- [x] Source có boot skeleton, focus-visible, reduced-motion và guard không có
      `transition: all` trong Portal stylesheets.
- [x] Source giữ semantic dark canvas navy/teal và input tokens; không map sang obsidian.
- [~] **LIVE-UI-01 — LIVE_RECHECK_OPEN 2026-10-17:** sau deploy `506d2b9`, landing
      production dùng bundle mới; ảnh live ở `1280×720` không có clipping/overflow. Ma trận
      browser CI đã phủ phone `375/390`, tablet `768` và desktop `1440` ở light/dark, nhưng
      viewport mobile production chưa đo được trong browser hiện có nên chưa khóa hết lỗi H.
- [~] **LIVE-UI-02 — LIVE_RECHECK_OPEN 2026-10-17:** bundle mới không còn PWA FAB cũ
      trong HTML ở live desktop; PWA CTA dùng readiness `beforeinstallprompt` và CI đã kiểm
      tra, nhưng vị trí mobile production chưa có bằng chứng viewport nên giữ mở cùng H.
- [x] **SOURCE-UI-01:** landing không tạo hoặc giữ banner/FAB khi chưa có
      `beforeinstallprompt`; iOS vẫn dùng hướng dẫn cài đặt riêng. Regression mới nằm ở
      `tests/pwa-landing-install-placement.test.mjs`.
- [x] **SOURCE-UI-02:** cụm điều khiển landing ở ≤420px có `flex-wrap: wrap`, giữ brand
      row và tránh ép locale/theme/CTA thành một hàng. Regression gate header đã cập nhật.
- [x] **SOURCE-UI-03:** modal hướng dẫn cài ứng dụng giữ đúng nền xanh navy/xanh ngọc;
      lớp phủ và thanh chọn tab không còn dùng nền đen. Regression nằm ở
      `tests/install-modal-navy-palette.test.mjs`.
- [x] Source recheck sau W1 và W2 locale: focused PWA/auth/utility/motion `39/39`,
      toàn bộ Node `480/480`, `node --check static/portal/portal-i18n.js`,
      `git diff --check` đạt.
- [!] Python Admin/PWA contract chưa chạy: bundled Python không có module `pytest`; đây
      là blocker công cụ, không ghi PASS giả.
- [~] Live recheck 2026-10-16 lúc `14:52:08 UTC` ở `/welcome?lang=vi`, viewport rộng `327px`
      vẫn nhận fingerprint `local-57e76aa281dcc721fdaa`. `body.scrollWidth=327` và
      `clientWidth=327`, nhưng `.portal-pwa-fab-trigger` vẫn `display:flex`, `position:fixed`,
      `44×44px`, tọa độ khoảng `(12,544)`. Header source fix chưa được đưa lên runtime; giữ
      `LIVE-UI-01/LIVE-UI-02` mở.
- [x] Delivery evidence 2026-10-16: GitHub PR #647 vẫn `Open`; trang PR hiển thị
      `This branch has not been deployed` và `No deployments`. Đây là nguyên nhân xác nhận
      của live drift; không đánh dấu `LIVE_PASS` khi chưa có delivery được Owner cho phép.
- [ ] Đo viewport 320/375/414/768/1024 ở light/dark; ghi `scrollWidth <= clientWidth`.
- [ ] Đo type/spacing/contrast thật; body ≥16px mobile, target ≥44×44px, contrast AA.
- [ ] Xác minh bảng/list chuyển hàng dọc hoặc wrapper có nhãn trên 375/390px.

## 3. W2 — Locale purity — Spec R217-02

- [x] **SOURCE-LOCALE-21 — 2026-10-17:** sau khi bổ sung lối vào Image VI/EN/ZH, chạy lại
      bộ locale Node contracts trên worktree hiện tại, mỗi tệp chạy đúng một lần: `319/319`; full Node suite:
      `521/521`. Đây chỉ là source evidence, không thay thế browser AX tree hoặc live bundle.
- [ ] Browser AX tree/visible DOM trên runtime đã giao vẫn mở; rà soát inventory toàn bộ
      customer/Admin/product lanes và các fallback ngoài test hiện có vẫn chưa khép.

- [x] Source locale R210 Workboard, R211 Memory, R212 Campaign, R213 Gallery/Audio,
      R214 Video có focused tests và catalogue VI/EN/ZH.
- [x] Source auth CTA dùng catalogue, có duplicate-key regression.
- [x] W2 source regression mới: locale/auth catalogue `272/272` Node pass; `portal-i18n.js`
      và `portal-auth.js` syntax pass. Admin fallback copy vừa dọn `Web audit metadata`,
      `Feature/provider readiness` và các nhãn vai trò/quyền hạn generic trong VI.
- [x] **SOURCE-LOCALE-03:** các thẻ cố định của Admin → Quản trị hệ thống đã có bản dịch
      tiếng Việt đầy đủ cho theo dõi tự động hóa, bảo mật, quyền truy cập, tài liệu quản trị,
      kho tài liệu, hệ thống, môi trường chạy và bản sao lưu; regression
      `tests/admin-system-stewardship-locale.test.mjs` đạt `1/1`.
- [x] **SOURCE-LOCALE-04:** fixed chrome Admin còn sót `Maintenance`, `Audit`, `Incident queue`,
      `Job`, `Output`, `Workspace`, tiêu đề bảo mật/quyền truy cập, quản trị hệ thống,
      phản hồi chuyển đổi và tác vụ bị khóa đã được dịch trong catalogue VI; regression
      `tests/admin-generic-fixed-chrome-locale.test.mjs` đạt `1/1`.
- [x] Đã đồng bộ contract route `Postback Readiness`: đây là tên route/proper name được
      reviewed trong bundle contract; regression Admin cũ không còn phủ định giá trị này.
      Full Node sau đồng bộ vẫn `518/518`.
- [x] **SOURCE-LOCALE-05:** nhóm Bảo mật & Quyền truy cập trong Admin đã dịch fixed chrome
      `Security/Access Posture`, `aggregate`, `session`, `role`, `throttle`, `credential`,
      `control plane` và các nhãn trạng thái tương ứng; regression cùng file đạt `2/2`.
- [x] **SOURCE-LOCALE-06:** nhóm Giám sát tự động hóa trong Admin đã dịch fixed chrome
      `scheduler`, `receipt`, `metadata`, `preflight`, `control plane`, `delivery`,
      `payment` và trạng thái biên nhận; regression `tests/admin-generic-fixed-chrome-locale.test.mjs`
      đạt `1/1` và bao phủ 3 nhóm chuỗi.
- [x] **SOURCE-LOCALE-07:** hai màn hình hướng dẫn quản trị đã dịch fixed chrome về bàn giao,
      phân loại tác vụ bị khóa, chuyển cấp, hàng chờ, giao kết quả và tài chính; regression
      `tests/admin-generic-fixed-chrome-locale.test.mjs` đạt `1/1` và bao phủ 2 màn hình.
- [x] **SOURCE-LOCALE-08:** điều hướng Giao nhận & Môi trường vận hành đã dịch fixed chrome
      về công việc, tiến trình xử lý, hàng chờ, giao kết quả, nhà cung cấp và bảo trì; regression
      `tests/admin-generic-fixed-chrome-locale.test.mjs` đạt `1/1`.
- [x] **SOURCE-LOCALE-09:** customer shell navigation đã dịch các nhãn fixed chrome còn lộ
      `Analytics Workspace`, `Memory Center`, `Image Operations Hub`, `Document Workspace`,
      `Audio Workspace`, `Automation Center`, `Operations Center`, `Media Factory`,
      `Creative Flow` và `storyboard`; regression `tests/customer-shell-nav-locale.test.mjs`
      đạt `1/1`.
- [x] **SOURCE-LOCALE-10:** customer `deliveryCenter.*` đã dịch toàn bộ fixed chrome của
      trung tâm tác vụ, thư viện tài sản, trạng thái kết quả/bàn giao, bảng, chi tiết và phiếu
      hỗ trợ; bản VI không còn các thuật ngữ giao diện chung `job`, `output`, `delivery`,
      `workflow`, `runtime`, `metadata`, `download`, `ticket` hoặc `Web-native`. First paint
      `/jobs` và `/assets` cũng đã sạch tiếng Việt. Regression
      `tests/delivery-center-locale-purity.test.mjs` đạt `1/1`; focused nhóm đạt `3/3`, full
      Node suite đạt `477/477`; runtime/live locale vẫn mở.
- [x] **SOURCE-LOCALE-11:** customer `accountCenter.activity.*` và mô tả `/account/activity`
      đã dịch sạch nhật ký, ranh giới dữ liệu, trạng thái theo chủ sở hữu và thông báo làm mới;
      fallback renderer cũng khớp. Regression `tests/account-activity-locale-purity.test.mjs`
      đạt `1/1`; focused account đạt `4/4`, full Node suite đạt `478/478`; runtime/live và
      các cụm hồ sơ/tài khoản còn lại vẫn mở.
- [x] **SOURCE-LOCALE-12:** customer `accountCenter.dataControls.*` và mô tả
      `/account/data-controls` đã dịch sạch fixed chrome về phạm vi dữ liệu, bản xuất, yêu cầu
      rà soát xóa, phiên bản, quyền sở hữu, ranh giới Bot và thông báo thao tác; fallback trong
      `renderAccountDataControls` cũng không còn trộn `review`, `export`, `Web`, `signed`,
      `authoring`, `browser` hoặc `canonical`. Regression `tests/data-controls-locale-purity.test.mjs`
      đạt `2/2`; full Node suite đạt `480/480`, syntax hai file Portal và `git diff --check`
      đều đạt. Runtime/live, hồ sơ/tài khoản còn lại và product-lane scan vẫn mở.
- [x] **SOURCE-LOCALE-13:** customer `supportTicket.*` fixed chrome và fallback của tư vấn,
      bằng chứng, yêu cầu, chi tiết, đánh giá và phân loại vận hành đã được làm sạch tiếng Việt;
      tên riêng/mã kỹ thuật cần thiết được giữ nguyên. Regression
      `tests/support-ticket-locale-purity.test.mjs` đạt `2/2`, catalogue VI đủ `295` mục,
      renderer có ít nhất `210` fallback, full Node suite `482/482`, syntax hai tệp Portal và
      `git diff --check` đều đạt; contract tạo/trả lời/liên kết bằng chứng vẫn còn. Runtime/live,
      browser AX tree, hồ sơ/tài khoản còn lại và product-lane scan vẫn mở.
- [x] **SOURCE-LOCALE-14:** customer `accountCenter.profile.*` và fixed chrome/fallback của
      `/account` đã được làm sạch tiếng Việt: phiên đã xác thực, máy chủ, nguồn chuẩn, nhà cung
      cấp, siêu dữ liệu, quy trình, trình duyệt, tài khoản, ví, tác vụ, tài sản, bàn giao và
      Trung tâm bảo mật. Regression `tests/account-profile-locale-purity.test.mjs` đạt `2/2`,
      catalogue VI đủ `101` mục; giữ nguyên route, action, field, capability, CSRF, idempotency,
      revision, provider labels, URL ảnh và dữ liệu hồ sơ. Full Node suite `484/484`, syntax hai
      tệp Portal và `git diff --check` đều đạt. Runtime/live, browser AX tree và product-lane
      scan vẫn mở.
- [x] **SOURCE-LOCALE-15:** fixed chrome Image Studio và Image Hub đã dùng catalogue
      `imageStudioUi.*` cân bằng VI/EN/ZH cho guard, giới thiệu, bảng thiết kế, ranh giới
      biên tập, ý định, định dạng, trạng thái và bộ lọc; bản VI không còn generic English
      UI. Regression `tests/image-studio-locale-purity.test.mjs` đạt `2/2`, focused Image
      đạt `45/45`, full Node suite `486/486`, `node --check` hai tệp Portal và
      `git diff --check` đều đạt. Route/action/field/capability/CSRF/idempotency/revision
      và dữ liệu động không đổi; Python contract `NOT_RUN` vì thiếu `python`/`py`.
      Runtime/live, AX tree và Image reference/detail/Resize/Enhance/Brand Overlay/
      Storyboard còn mở.
- [x] **SOURCE-LOCALE-16:** fixed chrome thư viện tham chiếu, thư viện bảng thiết kế, thẻ
      bảng thiết kế, tổng quan Image Hub, bước tiếp theo và bảng rà soát định hướng đã dùng
      catalogue `imageStudioLibraryUi.*` có `67` mục cân bằng VI/EN/ZH. Regression
      `tests/image-studio-library-locale-purity.test.mjs` đạt `2/2`, focused Image `49/49`,
      full Node `488/488`, syntax hai tệp Portal và `git diff --check` đều đạt. Giữ nguyên
      route/action/offset phân trang/capability và dữ liệu động; Python contract `NOT_RUN`
      vì thiếu `python`/`py`. Chi tiết artboard/direction/estimate/history và Image
      Resize/Enhance/Brand Overlay/Storyboard vẫn mở.
- [x] **SOURCE-LOCALE-17:** fixed chrome chi tiết Image Studio/Hub — estimate, direction card,
      trạng thái, lịch sử, activity, tiện ích và nút xác nhận — đã dùng catalogue
      `imageStudioDetailUi.*` có `91` mục cân bằng VI/EN/ZH. Regression
      `tests/image-studio-detail-locale-purity.test.mjs` đạt `2/2`, focused Image `51/51`,
      full Node `490/490`, syntax hai tệp Portal và `git diff --check` đều đạt. Giữ nguyên
      route/action/field/capability/CSRF/idempotency/revision, dữ liệu động và ranh giới
      không tạo ảnh; Python contract `NOT_RUN` vì thiếu `python`/`py`. Runtime/live, AX tree
      và Image Resize/Enhance/Brand Overlay/Storyboard vẫn mở.
- [~] **LIVE-I18N-01:** next-route `/features → /login?next=/features` từng lộ
      `Tải & Cài đặt App TOAN AAS` trong bundle cũ; phải recheck đúng URL sau delivery.
- [~] Đã khóa các cụm fixed chrome Admin, customer và Image theo SOURCE-LOCALE-04→17; vẫn còn phải quét tiếp
      toàn customer/Admin/product lanes và lập danh sách chuỗi English lọt trong VI cùng
      Vietnamese lọt trong EN/ZH; không sửa server data/ID/URL.
- [x] **SOURCE-LOCALE-22 — 2026-10-17:** Ma trận source locale gồm `59` file Node hiện hành
      đạt `320/320`; các contract fallback, duplicate key, option label và aria-label ở
      VI/EN/ZH đều pass trong phạm vi source. Browser AX theo locale vẫn mở ở R217-11.
- [ ] Evidence: `node --test tests/auth-locale-copy-purity.test.mjs tests/*locale*.test.mjs`
      và browser AX tree theo locale.

## 4. W3 — Auth lifecycle, first paint và accessibility — Spec R217-03

- [x] Source auth entry giữ entry→settled lifecycle; provider reservation tránh layout shift.
- [x] Source Telegram giữ user gesture, PWA prompt chỉ gọi khi readiness thật.
- [x] Skip link, labels, autocomplete, aria-busy, password cleanup và reduced-motion guards
      đã có regression theo R216.
- [x] Auth source contract: intro bắt đầu ở đầu bố cục khi provider card cao
      (`align-items/align-content:start`, `padding-top:68px`); responsive auth header
      kiểm tra đúng ba hàng brand/locale/actions. Direct source checks của hai contract đạt.
- [x] Auth/customer/motion source regression bổ sung `31/31` pass; auth focused `16/16`
      pass. Python pytest vẫn không có trong runtime nên không đánh dấu pytest PASS.
- [ ] QA unauthenticated route matrix: `/dashboard`, `/features`, `/image/create`,
      `/subdub`, `/music`, `/voice`, `/admin` đều fail-closed đúng next path.
- [ ] QA authenticated first paint: skeleton → shell → data; không chớp trang hoặc render
      panel rỗng trước redirect.
- [ ] Keyboard: Tab order theo thứ tự thị giác, focus visible, Escape/Back cho modal/drawer,
      lỗi nằm cạnh field và không có focus trap.
- [ ] Evidence DOM/AX/screenshot/console/network; không login production nếu không có fixture.

## 5. W4 — Product lanes lấy flow Bot làm tham chiếu

Mọi lane dưới đây phải có một workspace chính và cùng state contract:
`input → options → preflight → confirm → progress → result/recovery`. UI không được
hiển thị thành công giả khi engine/bridge chưa có.

### 5.1 Image — Spec R217-04

- [x] Source presentation focused `188/188` cho Image/Voice/Music/SubDub/Video; UI giữ
      guarded boundary và không tạo output giả.

- [ ] Một entry `/image/create` có tạo ảnh AI và chỉnh sửa ảnh; không buộc người dùng mò
      route khác để upload/reference.
- [ ] Có prompt, tỉ lệ, style/preset, image reference/upload, biến thể, preview và lịch sử.
- [ ] Có trạng thái draft/guarded/processing/completed/failed; output gallery chỉ cho tải
      khi asset thật, không dùng `output available` giả.
- [ ] Nút chính, disclosure nâng cao, helper/error và mobile stacking được khóa bằng test.
- [ ] Phân biệt source UI green với `REAL_OUTPUT` chưa có bridge; evidence phải ghi rõ.
- [!] Image AI edit/reference upload/preview/delivery thật chưa có evidence; `/image/edit`
      hiện là Image Enhance deterministic và `/image-studio` là planning metadata.

- [x] **SOURCE-IMAGE-01 — 2026-10-17:** `/image/create` có danh sách dọc để chọn Tạo ảnh /
      Chỉnh sửa ảnh, đánh dấu rõ trang hiện tại, nhãn truy cập được và copy VI/EN/ZH; đường
      chỉnh ảnh mô tả đúng công cụ tăng chất lượng hiện có, đồng thời nói rõ AI edit chưa khả
      dụng. Không đổi route/action/field/capability và không thêm upload/preview/output giả.
      Focused Image `40/40`, locale contracts `319/319`, full Node `521/521`; `node --check`
      hai tệp Portal và `git diff --check` đạt. Browser render/AX chưa chạy; toàn bộ yêu cầu
      workspace thống nhất, reference/upload, preview, variants và lịch sử vẫn còn mở.
- [x] **SOURCE-IMAGE-02 — 2026-10-17:** audit chỉ-đọc xác nhận `/image/create` có server job API
      nhưng form Web không có trường reference; `/image/transform` và `/image/upscale` có bridge
      riêng nhưng source matrix ghi `BLOCKED_PROVIDER_ENTITLEMENT`, chưa phải kiểm tra quyền live.
      `/image/edit` là Image Enhance Web-native xác định, không phải chỉnh sửa AI. Không gọi nhà
      cung cấp hoặc thay quyền; ghi blocker thay vì bật chức năng. R217-04 vẫn `TODO` cho workspace
      thống nhất, upload/reference, variants, preview/history và đầu ra đã xác minh.

### 5.2 Voice — Spec R217-05

- [ ] Một workspace có giọng mặc định, giọng tự thêm/tải file, voice library, preview,
      lưu/xóa có guard và chọn giọng cho sản phẩm khác.
- [x] **SOURCE-VOICE-01 — 2026-10-17:** Voice Studio có thanh chọn lane dọc với đúng 3
      lối vào `/voice/tts`, `/voice/saved`, `/voice/clone`; mỗi thẻ nêu rõ mục đích, CTA
      và trạng thái được bảo vệ. VI/EN/ZH lấy cùng catalogue `customerVoiceStudio`;
      không thêm upload, audio, provider hoặc output giả.
- [x] **SOURCE-VOICE-02 — 2026-10-17:** bề mặt Voice Studio/Voice Vault dùng lại hệ xanh
      dương–xanh ngọc và nền xanh navy của portal, có focus ring, hover nhẹ và mobile
      stacking một cột; không còn dùng nền cam/nâu riêng cho khu vực này.
- [~] Presentation đã nối selector giọng của SubDub tới `/voice-studio` ở cả hai panel lồng
      tiếng/combo; dữ liệu Voice thật và Music handoff vẫn chờ server capability.
      hoặc gọi provider trong QA.
- [ ] Có text/language/rate/pitch/volume, preview loading, result/download/recovery,
      báo cáo request/job/output thật.
- [ ] Tách rõ `voice_tts` source pass với `voice_clone` runtime blocked.
- [!] Voice TTS/clone/preview/output runtime vẫn guarded; Voice Library chưa nối dữ liệu thật
      vào SubDub bằng evidence runtime xác thực.

### 5.3 Music — Spec R217-06

- [ ] Một hub có hai mode rõ: tạo nhạc nền và tạo nhạc có lời; mode switch không làm mất
      input đã nhập.
- [ ] Nhạc nền: mood/style/duration/instrument/volume; nhạc có lời: lyrics/topic/language
      và vocal/instrumental; preset và preview dùng cùng hệ component.
- [ ] Có progress/result/history/export và cảnh báo boundary nếu generation bridge chưa có.
- [ ] Mobile mode switch/card/list theo hàng dọc; không trộn thuật ngữ English trong VI.
- [x] **SOURCE-MUSIC-01 — 2026-10-17:** Music hub có journey ba bước, đặt hai hướng chính
      nhạc nền/bài hát có lời trước nhánh SFX; card giữ đúng sáu route hiện hữu, thêm
      `data-music-mode`/`data-music-role` và mô tả cho trình đọc màn hình.
- [x] **SOURCE-MUSIC-02 — 2026-10-17:** UI dùng token xanh/navy chung, desktop tối đa hai cột,
      mobile `max-width: 820px` xếp một cột; VI/EN/ZH có catalogue cân bằng, không tạo output
      hoặc trạng thái hoàn tất giả.
- [x] Regression Music hub/library `16/16`; `node --check` Portal `2/2`; `git diff --check`
      đạt. Đây là source presentation evidence, chưa phải browser/live/runtime evidence.
- [!] Hai hướng nhạc nền/nhạc có lời có entry/catalogue nhưng generation/export thật vẫn
      guarded; không có provider/output evidence.

### 5.4 SubDub — Spec R217-07

- [ ] Chỉ một giao diện cho phụ đề gốc, dịch phụ đề, lồng tiếng và combo; không chia route
      khiến người dùng đoán luồng.
- [ ] Chọn mode bằng segmented control/radio có nhãn: `Phụ đề gốc`, `Dịch phụ đề`,
      `Lồng tiếng`, `Phụ đề + lồng tiếng`.
- [ ] Có Smart Multi auto-detect: một giọng, hai giọng hoặc nhiều giọng; hiển thị mapping
      vai/giọng và cho phép override trước confirm.
- [ ] Voice selector lấy giọng mặc định/giọng đã lưu/giọng upload từ Voice library; có
      preview, volume giọng gốc/giọng lồng tiếng, subtitle style và target language.
- [ ] Ngôn ngữ dùng catalog đầy đủ theo năng lực Bot; mặc định tự nhận diện → tiếng Việt,
      sau đó EN/ZH và các target khác, không hard-code danh sách hẹp ở UI.
- [ ] Kết quả phải có video/track/subtitle artifact thật hoặc trạng thái bị chặn cụ thể;
      không dùng card “xong” cho draft.
- [x] Source presentation bổ sung Smart Multi guarded: lựa chọn tự động/một/hai/nhiều
      giọng, mapping placeholder, selector Voice Library và mã ngôn ngữ ISO mở rộng;
      SubDub vẫn không gọi engine và không tạo output giả.
- [x] Source presentation thêm liên kết rõ `Mở Thư viện giọng` tới `/voice-studio` cho cả
      panel Lồng tiếng và Phụ đề + lồng tiếng; regression SubDub `11/11` và Voice focused
      `47/47` vẫn xanh.
- [!] `SUBDUB_VOICE_LIBRARY_LINK_MISSING` runtime: selector đã có trong UI nhưng chưa nối
      dữ liệu Voice thật; upload/CTA vẫn guarded và target language custom chỉ là input
      presentation chờ server xác minh.
- [x] Source discoverability đã thêm liên kết `Mở Thư viện giọng` tới `/voice-studio` cho cả
      panel Lồng tiếng và Phụ đề + lồng tiếng; selector vẫn guarded, không tạo dữ liệu Voice giả.
- [x] **SOURCE-SUBDUB-01 — 2026-10-17:** một màn hình `/subdub` giữ đủ bốn mode, tab có
      keyboard navigation và cập nhật query không rời hub; draft panel không bị tách thành
      route mới.
- [x] **SOURCE-SUBDUB-02 — 2026-10-17:** panel lồng tiếng/combo có volume âm thanh gốc và
      giọng lồng tiếng riêng; Smart Multi, Voice Library và ISO language input hiển thị đúng
      trạng thái guarded; regression `11/11` focused xanh.

### 5.5 Product Video — Spec R217-08

- [x] **SOURCE-VIDEO-01 — 2026-10-17:** Hub dọc chia `10` route duy nhất thành bốn lane
      lập kế hoạch, tạo video, biên tập/ghép và kiểm tra/bàn giao; mỗi lane có đầu vào,
      đầu ra và trạng thái `ready`/`guarded` rõ ràng, CTA không lộ jargon kỹ thuật.
- [x] **SOURCE-VIDEO-02 — 2026-10-17:** Hub trình bày flow bảy bước nhập → plan → quote →
      confirm → progress → result → recovery; form `/video/create` và `/video/multiscene`
      giữ nguyên contract bảy bước hiện hữu.
- [~] **SOURCE-VIDEO-03 — 2026-10-17:** Boundary AI/manual đã có trên hub, đồng thời giữ
      handoff scene/timeline, poster, audio, reference, version/history và report ở các
      màn hình chuyên trách. Render MP4, upload và delivery thật vẫn chưa có runtime evidence.
- [x] **SOURCE-VIDEO-04 — 2026-10-17:** Không tuyên bố real MP4/provider output; card guarded
      chỉ nêu điều kiện xử lý và CTA xem khả năng, không tạo job, charge, provider hay wallet.
- [!] `VIDEO_AI_MANUAL_EDIT_UI_MISSING`: AI edit/manual edit/timeline/render MP4/delivery
      chưa có evidence; Video Studio hiện là planning/scene/review/version metadata.
- [x] **SOURCE-VIDEO-05 — 2026-10-17:** Khóa CTA chính của Bắt đầu nhanh bằng thuộc tính
      tường minh trên `/video/finishing`, không suy ra theo vị trí mảng. `/video-studio` và
      `/video/text-to-video` vẫn là lối phụ; browser gate không còn đọc nhầm planning thành
      CTA vận hành. Regression Video Hub `11/11`, full Node `523/523`, node-check và
      `git diff --check` đạt; chưa có runtime/provider/output evidence.

Evidence closeout R217-08: `HEAD_SHA=59afdf7a8367a0126c6078f40c75dbce019966ae`; focused
`node --test tests/video-uiux-locale-presentation.test.mjs` đạt `11/11`, full
`node --test tests/*.test.mjs` đạt `523/523`, `node --check` hai tệp Portal đạt `2/2`,
`git diff --check` đạt. CI run `39018249838` đã chạy thành công provenance, critical contracts,
browser verification gate và browser runtime gate; kiểm đủ `6/6` hub, tạo `18` screenshot và
upload evidence. Authenticated QA/performance trace, upload/render/delivery và real artifact
vẫn `OPEN`, không đánh dấu `LIVE_PASS`.

### 5.6 Content, Workboard, Free Tools, Notes, Projects — Spec R217-09A

- [x] **SOURCE-CONTENT-01 — 2026-10-17:** Content Studio, Workboard, Free Tools, Notes,
      Projects, Publish Review và Campaign có renderer/helper, locale VI/EN/ZH và source
      contract cho create/edit/save/archive/restore/version/history cùng các trạng thái
      empty/loading/error/guarded. Focused set hiện đo được `26/26`.
- [x] **SOURCE-CONTENT-02 — 2026-10-17:** Campaign/Calendar/Approval có mốc, trạng thái,
      lịch, review và handoff; server action/CSRF/revision không đổi.
- [x] **SOURCE-CONTENT-03 — 2026-10-17:** Free Tools/Prompt Gallery có filter, copy/save và
      tách fixed chrome khỏi prompt data; Workboard có board/list/card dọc trên mobile.
- [~] Browser/runtime, keyboard/AX viewport và dữ liệu ghi thật của các surface này vẫn mở;
      không suy diễn source `26/26` thành live PASS.
- [x] Ghi nhận những phần chỉ là planning/draft; không gọi là sản phẩm đã tạo.

## 6. W5 — Admin và liên kết customer — Spec R217-09

- [x] Source Admin fallback locale đã dọn các nhãn kỹ thuật generic; focused Admin tab +
      motion suite `29/29` pass.
- [x] Admin module navigation đã chuyển thành danh sách dọc, `min-height:44px`, không còn
      `overflow-x:auto`/`min-width:max-content` trong scoped tab layer.

- [ ] Admin shell/menu/operations/billing/jobs/assets/customer/support/audit/reliability/
      ERP trình bày theo hàng dọc, nhóm rõ, không lẫn tiếng Anh trong VI.
- [x] **SOURCE-ADMIN-01:** fixed chrome của bảng Provider dùng catalogue `adminProviderUi.*`
      cân bằng VI/EN/ZH cho cột, badge cấu hình/khả dụng/sức khỏe/điều phối, empty state và
      nút chi tiết; không đổi provider ID, capability data, route hoặc thao tác provider.
- [x] **SOURCE-ADMIN-02:** fixed chrome duyệt/từ chối nạp thủ công dùng catalogue
      `adminManualTopup.approval.*`, giữ nguyên draft/confirmation action và không mở ledger
      mutation trong batch.
- [x] Regression Admin Provider + Manual Topup `4/4`; full Node suite sau batch đạt `506/506`,
      `NEW_FAILURES=0`; provider table vẫn read-only và manual top-up approval vẫn là draft/
      confirmation presentation, chưa mở wallet/ledger mutation.
- [x] **SOURCE-ADMIN-03:** `/admin/publishing` domain center dùng catalogue
      `adminDomainUi.publishing.*` cho title/description, 4 stream, 3 boundary và common
      permission/read-only chrome; giữ nguyên 4 route và server authorization filter.
- [x] Regression Admin domain/provider/topup `7/7`; full Node suite `509/509`, syntax và
      `git diff --check` đạt.
- [x] **SOURCE-ADMIN-04:** `/admin/growth` và `/admin/trends` dùng catalogue
      `adminDomainUi.growth.*` và `adminDomainUi.trends.*` cho title, description, stream,
      boundary và common permission/read-only chrome; route allowlist không đổi.
- [x] **SOURCE-ADMIN-05:** Customer 360 và safety modal đã chuyển toàn bộ fixed chrome còn sót
      (an toàn tài khoản, trạng thái phiên, ví/tài chính, tác vụ/tệp, hỗ trợ, nhật ký,
      nút khóa/mở khóa, cảnh báo, nhãn lý do và nút đóng/hủy) sang catalogue
      `adminCustomer360.*` cân bằng VI/EN/ZH. Dữ liệu động, mã tài khoản, role/status server,
      `admin-customer-*` actions, wallet/ledger truth và safety boundary không đổi. HEAD sau
      batch: `a0069fa866a866dc319bcea91e5c2da867433c94`; nhánh PR đã push.
- [x] Regression mới `tests/admin-customer-360-locale-purity.test.mjs`: `3/3`; full Node
      suite sau batch: `512/512`, `NEW_FAILURES=0`; `node --check static/portal/portal.js`,
      `node --check static/portal/portal-i18n.js` và `git diff --check` đạt.
- [x] Contract comparator với HEAD trước batch giữ nguyên `data-portal-action 771→771`,
      `data-portal-route 630→630`, `field names 439→439`, `removed=[]`, `added=[]`.
- [!] `python -m pytest tests/test_p0_webapp_v2_05_admin_customer_360.py -q` chưa chạy được:
      môi trường hiện không có lệnh `py`/`pytest`; không ghi PASS giả. Browser/runtime,
      canonical-admin fixture và ledger mutation vẫn mở/deferred đúng phạm vi.
- [x] **SOURCE-ADMIN-06:** Admin shell boundary badges đã chuyển 4 nhãn cố định còn trộn
      ngôn ngữ (`Job Bridge Sẵn sàng`, `Kế hoạch & Bản nháp Web`, `AI Generator`,
      `Bộ tạo AI (Chờ Adapter)`) sang `adminHome.boundary.*` cân bằng VI/EN/ZH. Giữ nguyên
      `canonical_bridge`, `web_planning`, `runtime_generator`, trạng thái ready/guarded,
      route, action và dữ liệu server.
- [x] Regression `tests/admin-shell-boundary-locale.test.mjs`: `5/5` khi chạy cùng Customer
      360 focused; syntax Portal `2/2` đạt. Full Node suite và comparator sẽ là cổng closeout.
- [x] **SOURCE-ADMIN-07:** fallback fixed chrome của `renderAdminSystemStewardship` đã
      được làm sạch tiếng Việt cho thẻ Automation/Security/Access/Governance/Archive/System/
      Runtime/Backups, marker thẩm quyền, manifest, tiêu đề phân khu và ranh giới vận hành.
      Catalogue `adminGeneric.systemStewardship.*`, route/action, manifest filter, authority
      state và dữ liệu server giữ nguyên.
- [x] Regression `tests/admin-system-stewardship-fallback-locale.test.mjs` cùng catalogue
      stewardship đạt `4/4`; syntax Portal `2/2` đạt. Full Node suite là cổng closeout.
- [x] **SOURCE-ADMIN-08:** fallback fixed chrome của `adminFinanceDomain` đã được làm sạch
      tiếng Việt cho trung tâm tài chính, 7 luồng thanh toán/nạp Xu/doanh thu/hoàn tiền/giá,
      kế hoạch tài chính và kế toán-thuế; giữ nguyên route, authority, boundary và helper
      `adminFinance.*`.
- [x] Regression `tests/admin-finance-domain-fallback-locale.test.mjs`: `2/2`; full Node
      suite sau batch: `516/516`, `NEW_FAILURES=0`; syntax Portal `2/2` đạt.
- [x] **SOURCE-ADMIN-09:** fallback fixed chrome của ba domain center Publishing/Growth/
      Trends đã chuyển từ tiêu đề tiếng Anh sang tiếng Việt (trung tâm, chiến dịch, lịch,
      phê duyệt, phân tích, khách hàng tiềm năng, bàn giao, brief và mức sẵn sàng); giữ nguyên
      domain route, stream route, manifest filter, authority và catalogue locale.
- [x] Regression `tests/admin-domain-center-fallback-locale.test.mjs`: `2/2`; full Node
      suite sau batch: `517/517`, `NEW_FAILURES=0`; syntax Portal `2/2` đạt.
- [x] **SOURCE-ADMIN-10:** CSS harmony cho bảng dữ liệu Admin mobile đã được khóa ở lớp
      source: selector scoped dưới signed Admin shell, breakpoint `700px`, theme token xanh/
      navy, scroll hint và first-column affordance; không có API/action/provider/wallet trong
      layer. Regression Node `tests/admin-mobile-data-harmony-source.test.mjs`: `1/1`.
- [~] Runtime/browser mobile matrix của bảng/inspector vẫn mở; Python contract tương ứng chưa
      chạy do môi trường thiếu `py`/`pytest`, không đánh dấu live PASS.
- [x] **SOURCE-ADMIN-10 closeout:** regression source mobile harmony đạt `1/1`; full Node suite
      sau batch: `518/518`, `NEW_FAILURES=0`; syntax Portal `2/2` đạt.
- [x] **SOURCE-ADMIN-11 recheck — 2026-10-17:** chạy lại toàn bộ `tests/admin-*.test.mjs`
      đạt `21/21`; full Node suite hiện hành đạt `522/522`, không có source regression mới.
      Fixed chrome, vertical navigation, locale, mobile harmony, Customer 360, Provider,
      manual top-up và domain center presentation đã có evidence source.
- [ ] Owner thấy toàn bộ; role khác chỉ thấy module/action theo policy hiển thị. UI phải
      nói rõ quyền bị thiếu thay vì nút chết.
- [ ] Mỗi customer action có request/job/asset/report reference và trạng thái audit trên
      Admin; không tự bịa record nếu backend chưa nối.
- [ ] Manual top-up UI có amount/method/reference/status/approve/reject/reason và audit
      trail; phần mutation/ledger vẫn `DEFERRED` nếu chưa có Owner gate.
- [ ] Admin data tables ở mobile chuyển card dọc hoặc wrapper có tiêu đề cột; chart có
      legend/label không dùng màu đơn độc.
- [ ] Evidence source dùng các test `tests/test_admin_*`, browser QA cần canonical_admin
      fixture cô lập; không gọi production wallet.
- [!] Manual top-up có draft/confirm receipt/idempotency ở source nhưng chưa có canonical
      admin fixture/runtime evidence chứng minh duyệt và ghi ledger; giữ mutation deferred.

## 7. W6 — Motion và perceived performance — Spec R217-10

- [x] Source auth double-render, provider reservation, `left` transition, stale observer/
      RAF, reduced-motion listener, blanket will-change và PWA gesture đã có regression
      theo R216.
- [x] Current source motion/admin focused suite `29/29`, auth/landing lifecycle/compositor
      suite `42/42`, product presentation suite `188/188` pass; runtime FPS/CLS/LCP/INP vẫn mở.
- [x] **R217-10 source timing closeout — 2026-10-17:** `--portal-motion-fast` đã khóa ở
      `160ms` (micro `150–300ms`), thấp hơn entry `220ms`; auth `680ms` và landing hero
      `980ms` giữ nguyên. Regression timing mới nằm trong focused motion/auth/PWA `43/43`;
      full Node `523/523`; `node --check` Auth/Motion `2/2`; `git diff --check` đạt;
      `HEAD_SHA=2d756b8db62f74cb331065c3b9ec74691f06a8cd` đã push lên nhánh PR #647.
- [x] Ba Python motion contracts còn giữ literal cũ `140ms` đã đồng bộ sang `160ms`;
      chưa chạy được `python/py/pytest` vì runtime hiện không có Python, không ghi PASS giả.
- [x] **R217-10 provenance repair — 2026-10-17:** CI run `39015089989` đã dừng ở
      `Verify committed migration evidence` vì `preflight.json`/`web_inventory.json`
      còn fingerprint cũ `4dbdf2…`, trong khi 284 file source đủ điều kiện hiện tại là
      `8ee8c9130c1fb121ff73c0d9ad6cd2fa35877f69c67449d7b3ffcaa9de3f424e`. Đã làm mới
      bằng chứng static-only theo HEAD `fe146c191ffd7abc2d6d4d8a679e3630ccea1a0e`;
      chưa đổi route, engine, runtime hay dữ liệu.
- [~] Browser motion acceptance còn mở: chưa có trace FPS/CLS/LCP/INP và chưa chứng minh
      scroll reveal không tạo vùng trống trên runtime mới.
- [x] Kiểm tra source micro `160ms`, exit nhanh hơn entry `220ms`; auth/customer entrance giữ
      `680ms` theo R216/WA-35 và landing cinematic giữ `980ms`; không animate quá 1–2 nhóm
      chính mỗi view, không dùng linear cho UI.
- [x] Kiểm tra source route unmount: observer/RAF/timer/listener bị hủy và async hydration
      không ghi vào shell đã thay; regression lifecycle `42/42`.
- [x] Kiểm tra source `prefers-reduced-motion` trước và khi đang chạy; nội dung vẫn hiển thị;
      regression reduced-motion nằm trong `43/43` focused gate.
- [ ] Chụp Performance trace đại diện desktop/mobile; ghi CLS <0.10, LCP ≤2.5s, INP ≤200ms
      hoặc ghi blocker nếu runtime không đo được.

## 8. W7 — Authenticated QA matrix — Spec R217-11

- [~] Runtime QA cục bộ chưa có dependency; không tự động tạo tài khoản production.
- [!] **QA-R217-11-01 — 2026-10-17:** Đã thử dựng runtime tạm ngoài repo bằng bundled
      Python `3.12.14` và `pip install -r requirements-dev.txt`; môi trường thiếu
      `fastapi`, `uvicorn`, `pytest`, `websockets`, còn PyPI không phân giải được DNS
      (`NameResolutionError: pypi.org`). Vì vậy chưa khởi động được server QA và chưa tạo
      fixture; không chuyển sang production để thay thế bằng chứng QA.
- [x] **SOURCE-R217-11-03 — 2026-10-17:** Runner CI riêng
      `scripts/ci/run_authenticated_qa_matrix.py` tạo DB SQLite tạm, 6 fixture account
      theo VI/EN/ZH, chạy customer + Admin trên 19 route × 3 locale × 2 theme × 4 viewport
      (456 bản ghi), ghi requested/resolved route, title/heading/CTA/field, AX tree, focus,
      screenshot, console, network và reload persistence. Job `authenticated-qa` trong
      `.github/workflows/webapp-quality.yml` cài dependency trong runner CI và upload artifact;
      contract route/count/safety `tests/test_r21711_authenticated_qa_runner_contract.py` được
      đưa vào critical WebApp contracts.
- [x] **RUNTIME-R217-11-01 — CLOSED_WITH_EVIDENCE — 2026-10-17:** CI run `39027760496`
      (job `117382539076`) trên HEAD `a311caf1913e7ab40361727a771a09d6eaf5ff5b`
      tạo artifact thật `webapp-authenticated-qa-a311caf1913e7ab40361727a771a09d6eaf5ff5b`.
      JSON ghi `records_expected=456`, `records_completed=456`, `records_passed=456`,
      `records_failed=0`, `provider_calls=0`, `wallet_mutations=0`,
      `production_data_mutations=0`. Đối soát 456 record: HTTP/route/locale/theme mismatch
      đều `0`; console errors/warnings, page errors, failed requests, external requests và
      forbidden mutations đều `0`; reload route/locale/theme mismatch `0`. Predicate PASS
      của runner bao gồm `horizontal_overflow=false`, nên `456/456` pass tương đương `0`
      overflow failure. Artifact ZIP local có SHA-256
      `334858235c9bb9ed67f4a5e3e093e1796bb8ce17ce32ca3bbc80f5cfc4911f38`, khớp digest
      GitHub; browser evidence artifact digest là
      `sha256:6e57d73522e244001908c88214484b8518380741ba70821e81c7871dba624d21`.
- [x] **RUNTIME-R217-11-02 — CLOSED_WITH_EVIDENCE — 2026-10-17:** Rerun trên HEAD
      `0001c11` tại workflow `39029971691` hoàn tất `Success` trong `6m 43s`; `Verify Web App`
      job `117388290081` xanh trong `2m 38s`, `Authenticated WebApp QA` job `117388767101`
      xanh trong `4m 01s`. Artifact `webapp-authenticated-qa-0001c110baa69d92885acf53293b3193856aff7c`
      có digest `sha256:328dd0d2d777d3d7c8907b9e0edc6ec85568e5cb745041b67b9383ed6fe147b3`;
      browser evidence digest `sha256:f3283ecc640acd428458286e1dfaef1f2e42bda339c9cdbacef3c86062bb3c55`.
      Rerun giữ nguyên ma trận `456/456` và safety predicate; chỉ còn warning môi trường Node 20/
      Ubuntu image, không có source/test failure. R217-11 vẫn đóng; không nâng thành LIVE.
- [x] **RUNTIME-R217-11-03 — CLOSED_WITH_EVIDENCE — 2026-10-17:** Rerun mới nhất trên HEAD
      `6c70cb0171244e5c817af1e9ff75c098b76f50fc` tại workflow `39030607461` hoàn tất
      `Success` trong `7m20s`; `Verify Web App` job `117390119739` xanh trong `3m04s`,
      `Authenticated WebApp QA` job `117390664800` xanh trong `4m09s`. Artifact authenticated
      QA có digest `sha256:db6af37ce65e260ec16990aef1204756b8196dc25b7e5c16749b27ae3ec88888`;
      browser evidence có digest `sha256:a3da16bc97c3ed371194beb322a0dd87951f2483ddaa7bb2a1c4a44cb8457a8e`.
      Ma trận giữ `456/456` bản ghi hoàn tất và đạt, mọi mismatch/lỗi console/page/request,
      reload, tràn ngang, request ngoài origin và mutation bị cấm đều `0`; `provider_calls=0`,
      `wallet_mutations=0`, `production_data_mutations=0`. Warning Node 20/Ubuntu là cảnh báo
      môi trường đã biết. R217-11 tiếp tục đóng bằng chứng; R217-12 vẫn `LIVE_DRIFT_OPEN` và
      `LIVE_PASS=NO` vì production chưa nhận bundle mới.
- [x] **RUNTIME-R217-11-04 — CLOSED_WITH_EVIDENCE — 2026-10-17:** Sau khi push provenance
      `bf290c4`, workflow `39033202368` trên HEAD `bf290c4` hoàn tất `Success`; `Verify Web App`
      job `117397736360` và `Authenticated WebApp QA` job `117398289631` đều xanh. Job
      authenticated hoàn tất trong `5m07s`; ma trận vẫn `456/456` bản ghi đạt, không phát sinh
      provider call, wallet mutation hoặc production-data mutation. Cảnh báo duy nhất vẫn là
      deprecation Node 20/Ubuntu runner; đây là cảnh báo môi trường, không phải lỗi source.
      R217-11 được khóa lại bằng bằng chứng CI mới nhất; R217-12 vẫn `LIVE_DRIFT_OPEN` và
      `LIVE_PASS=NO` vì production chưa nhận bundle mới.
- [x] **RUNTIME-R217-11-05 — CLOSED_WITH_EVIDENCE — 2026-10-17:** Workflow mới nhất trên HEAD
      `404d0b8` là `39034247997`, hoàn tất `Success` trong `8m10s`; `Verify Web App` job
      `117400767233` xanh trong `3m03s`, `Authenticated WebApp QA` job `117401357659` xanh
      trong `5m03s`. Ma trận tiếp tục `456/456` bản ghi đạt và không có provider call, wallet
      mutation hoặc production-data mutation. Artifact authenticated digest
      `sha256:bb1cf1a931426a150ab9b7f22db7eb9b8761e1be62a10cb22e85a197fd2861bb`; browser
      evidence digest `sha256:11ba1f0bd6fe9e4ee0ec55eeef93b39c30a2f0908c1eea3bd7e058a717a0921a`.
      Warning Node 20/Ubuntu vẫn là cảnh báo môi trường; R217-12 vẫn `LIVE_DRIFT_OPEN` và
      `LIVE_PASS=NO` vì production chưa nhận bundle mới.
- [x] **RUNTIME-R217-11-06 — CLOSED_WITH_EVIDENCE — 2026-10-17:** Sau khi khóa provenance
      cuối ở HEAD `7942548`, workflow `39034978224` hoàn tất `Success` trong `8m19s`; `Verify
      Web App` job `117402852575` xanh trong `3m02s`, `Authenticated WebApp QA` job
      `117403448516` xanh trong `5m12s`. Artifact authenticated giữ `456/456` đạt, digest
      `sha256:5ca1ad0448bcd3388695ffee032a4c99b3493fa59774b66e0725b385ef824d37`; browser
      evidence digest `sha256:d61a2372b3683c658c6ad1c606943198bfe558454151305df7d5b3d9af592ef7`.
      Provider call, wallet mutation, production-data mutation đều `0`; cảnh báo còn lại chỉ
      là Node 20/Ubuntu runner. R217-12 vẫn `LIVE_DRIFT_OPEN` và `LIVE_PASS=NO` vì production
      chưa nhận bundle mới.
- [!] **CI run `39024899449` — 2026-10-17:** quality gate nền đã xanh nhưng runner R217-11
      dừng khi tạo fixture tại `_set_fixture_locale`: schema thực tế lưu locale ở
      `web_account_profiles`, không phải `web_accounts`, nên job báo
      `sqlite3.OperationalError: no such column: locale` và chưa sinh artifact.
- [x] **SOURCE-R217-11-04 — 2026-10-17:** Sửa đúng runner: cập nhật role/canonical trên
      `web_accounts` theo `id`, upsert locale vào `web_account_profiles` với schema hiện tại,
      giữ DB SQLite tạm và không mở thêm mutation. Đã thêm contract cấm quay lại câu lệnh
      `UPDATE web_accounts SET locale`.
- [ ] Các lane Image/Voice/Music/SubDub/Video phải có evidence từng state; nếu engine chưa
      có, evidence phải chứng minh guarded boundary chứ không gọi output PASS.
- [x] **SOURCE-R217-11-02 — 2026-10-17:** Đã thêm fixture test DB tạm với
      `role_cache='admin'` và `canonical_user_id='canonical-admin'`, kiểm tra shell HTML của
      `/admin/operations`, `/admin/payments`, `/admin/customers`, `/admin/audit` và
      `/admin/support`. `py_compile` đạt; CI run `39021192324` passed. Đây là source auth
      evidence, chưa thay thế browser DOM/AX matrix. `/admin/billing` được ghi nhận là
      legacy name, không dùng trong canonical acceptance matrix.

## 9. W8 — Live read-only recheck — Spec R217-12

- [!] **R217-12 post-delivery 2026-10-17 13:35 UTC — locale redirect còn lỗi:** deploy
      workflow `39036918159` đã đưa `bc0d089055df7a52c1ee9e3e76a5cbc57beacce4` lên VPS,
      health check trên `toanaas-web.service` đạt, asset fingerprint đổi khỏi bundle cũ.
      Tuy nhiên `/features?lang=en` và `/features?lang=zh` vẫn về `/login?next=/features`,
      làm rơi locale; nguyên nhân gốc là nhánh redirect chưa đưa query `lang` vào return target.
      Đã khoanh đúng một nhánh trong `app.py`, thêm regression cho `vi/en/zh`; chờ PR sửa
      tiếp theo và lặp lại live matrix trước khi đóng `R216-L`.

- [~] **R217-12 fresh 2026-10-17 11:40:28 UTC — R216-L:** `/features?lang=vi|en|zh`
      vẫn kết thúc ở `/login?next=/features` và làm mất locale query. `main#portal-main`
      vẫn có `tabindex=-1`, nhưng các lần `en`/`zh` rơi về document `vi`/`Đăng nhập ·
      TOAN AAS`; bundle vẫn là `local-57e76aa281dcc721fdaa`.
- [~] **R217-12 fresh — R216-H:** viewport đang đo được là `1280×720`, không có
      overflow (`body/root=1280`, `client=1280`) và console không có warning/error; nav vẫn
      `flex-wrap:nowrap`. Mobile `327×668` drift đã có bằng chứng trước đó.
- [~] **R217-12 viewport-capable recheck — 2026-10-17 12:29:53 UTC:** tại `390×844`,
      `body/root/client=390` nhưng `.portal-landing-nav` có `scrollWidth=356` so với
      `clientWidth=343`, `.portal-landing-nav-actions` vẫn `flex-wrap:nowrap`, và PWA FAB cũ
      vẫn `hidden=false`, `display:flex`, `position:fixed`, `44×44px` ở khoảng `(12,720)`.
      Tại `1440×900`, `body/root/client=1440`, nhưng PWA FAB cũ vẫn `display:flex`,
      `position:fixed`, `171.95×41.10px` ở khoảng `(1023.05,834.90)`. Cả hai viewport dùng
      fingerprint `local-57e76aa281dcc721fdaa`; console warning/error `0`. Bằng chứng đã đủ,
      nhưng lỗi vẫn mở vì production chưa nhận source mobile-wrap/readiness-gated placement.
- [~] **R217-12 fresh — R216-P/LIVE-UI-02:** PWA FAB cũ vẫn hiện với
      `data-portal-pwa-fab="true"`, `display:flex`, `position:fixed`, `171.95×41.10px` ở
      desktop và asset fingerprint cũ; chưa nhận source placement/readiness fix.
- [~] **R217-12 fresh — auth install copy:** `/login?lang=vi|en|zh` đều có nút cài ứng
      dụng visible; production vẫn lộ `📲Tải & Cài đặt App TOAN AAS`, `📲Install TOAN AAS App`,
      `📲安装 TOAN AAS App` tương ứng. Source branch đã dùng icon SVG/copy mới nhưng chưa
      delivery; chưa đóng R216-P.
- [~] Ghi asset fingerprint, runtime SHA nếu có, viewport, URL, timestamp, DOM/AX và
      computed style; evidence mới tiếp tục lệch source SHA (`local-57e76aa281dcc721fdaa`),
      nên R217-12 vẫn `LIVE_DRIFT_OPEN`.
- [ ] Không bấm CTA tạo job, không đăng nhập production, không deploy/merge trong wave này.

## 10. W9 — Deferred technical register — Spec R217-13

- [→] Web-to-Bot adapter cho Product Video/Image/Voice/Music/SubDub và job polling/output
      MP4/PNG/audio/subtitle.
- [→] Smart Multi backend auto-detect, voice mapping và catalog ngôn ngữ thực thi.
- [→] Autopost channel token bridge, publish queue thực tế và support ticket bridge.
- [→] Admin cross-bridge trace, customer task report và permission enforcement server-side.
- [→] Manual top-up approval → ledger/Xu mutation; chỉ mở sau Owner gate wallet/PayOS.
- [→] Các mục deferred phải có request ID/job ID/provider task ID, idempotency, audit,
      fail-closed và provider/wallet safety proof trước khi code.

## 10.1. SOURCE-LOCALE-18 — Image operation chrome — Spec R217-02

- [x] Catalogue `imageOperationUi.*` cân bằng VI/EN/ZH cho picker tài sản, phân trang,
      guard/loading/failed, biểu mẫu, option, boundary, empty/result, lịch sử và xác nhận.
- [x] Brand Overlay: bỏ `Owner-scoped` cố định, thêm bản dịch `brand.guard.publicPreview`,
      chuyển notice cuối trang và nút lưu/bàn giao/tiếp tục qua helper locale.
- [x] Storyboard Grid: chuyển guard, loading, retry, lý do khóa, giới thiệu, form, boundary,
      kết quả, cell và notice sang helper; không đổi route/action/field/capability.
- [x] Image history/result cards: nhãn loại, nguồn, PNG đầu ra, khung/lớp thương hiệu/hồ sơ,
      fallback và thông báo tải xuống dùng catalogue; không hiển thị dữ liệu động thay thế.
- [x] Khóa điều kiện delivery: chỉ có download/export khi `state=completed` và
      `download_ready=true`; giữ nguyên path `/api/v1/image-operations/...` và
      `/api/v1/storyboard-grid/...`.
- [x] Regression `tests/image-operation-locale-purity.test.mjs`: `3/3`; focused Image/media
      `54/54`; full Node `493/493`; baseline `490/490`, `NEW_FAILURES=0`; syntax và
      `git diff --check` đạt.
- [ ] Browser/AX/live recheck chưa chạy; Python contract `NOT_RUN` do thiếu `python`/`py`.
- [ ] Không provider call, wallet mutation, production data, merge hoặc deploy trong batch.

- [x] **SOURCE-LOCALE-19:** Channel Strategy đã nối renderer vào catalogue
      `channelStrategyUi.*` cân bằng VI/EN/ZH, bao phủ guard/list/filter/pagination/create/
      detail/lifecycle/preview/history/activity, field label/placeholder/help và aria text.
      Workboard residual cũng đã khóa: nhãn bảng Kanban dùng `workboard.board.kicker`, guarded
      recovery dùng `workboard.recovery.guarded` thay vì fallback tiếng Việt thiếu key. Route,
      action, field, capability, revision, CSRF, idempotency và dữ liệu động giữ nguyên.
- [x] Regression `tests/channel-strategy-locale-presentation.test.mjs` đạt `2/2`, Workboard
      locale đạt `4/4`; focused Content/Workboard/Free/Memory/Project/Publish/Campaign đạt
      `28/28`; focused Image/media đạt `54/54`; full Node suite đạt `496/496`; baseline trước
      batch `493/493`, `NEW_FAILURES=0`; syntax và `git diff --check` đạt.
- [ ] Browser/AX/live locale recheck và Python contract vẫn chưa chạy; không đánh dấu runtime.
- [x] `HEAD_SHA=80e43861b6be4c92b9c9a4cbcb7fc19dd2841218` đã push lên nhánh
      `webapp-checklist-r116`; PR chưa merge, chưa deploy, `LIVE_PASS=NO`.
- [x] **SOURCE-LOCALE-20A:** Music Prompt Composer đã dùng catalogue
      `musicPromptComposerUi.*` cân bằng VI/EN/ZH cho trang lập kế hoạch, form, boundary,
      kết quả, ghi chú, biên nhận và phạm vi; giữ nguyên route/action/field/capability/CSRF/
      idempotency và không tạo âm thanh/tác vụ/thanh toán.
- [x] Regression Music Prompt Composer `2/2`; focused Channel/Workboard/Music `8/8`, focused
      Image/media `54/54`, full Node `498/498`, baseline `496/496`, `NEW_FAILURES=0`; syntax
      và `git diff --check` đạt. Direction Presets và SFX Cue Sheet còn là batch sau.
- [x] **SOURCE-LOCALE-20B:** Music Direction Presets đã dùng catalogue `musicDirectionUi.*`
      cân bằng VI/EN/ZH cho preset card, form, receipt, boundary, checklist và scope; giữ
      nguyên ID preset, route/action/field/capability/CSRF/idempotency và không tạo âm thanh.
- [x] Regression Music Direction `2/2`; focused Composer/Direction/Voice/Media `33/33`;
      full Node suite `500/500`, syntax và `git diff --check` đạt. SFX Cue Sheet còn là batch sau.
- [x] **SOURCE-LOCALE-20C:** SFX Cue Sheet đã dùng catalogue `sfxCueSheetUi.*` cân bằng
      VI/EN/ZH cho preset card, form, placement, receipt, cue list, boundary và scope; giữ
      nguyên preset/cue/placement ID, route/action/field/capability/CSRF/idempotency và không
      tạo SFX/audio/provider/job/payment.
- [x] Regression SFX Cue Sheet `2/2`; focused Composer/Direction/SFX/Voice/Media `33/33`;
      full Node suite `502/502`, baseline `500/500`, `NEW_FAILURES=0`; syntax và
      `git diff --check` đạt.

## 10.2. R217-12 closeout sau delivery — 2026-10-17 14:04 UTC

- [x] **R216-L — CLOSED_WITH_EVIDENCE:** `GET /features?lang=vi|en|zh` lần lượt trả `307`
      tới `/login?next=/features%3Flang%3Dvi`, `/login?next=/features%3Flang%3Den` và
      `/login?next=/features%3Flang%3Dzh`; query ngoài allowlist không được mang theo.
- [~] **R216-H — LIVE_RECHECK_OPEN:** landing production sau deploy dùng fingerprint
      `local-00d9a64e11a5031705e6`; `body/client` không overflow ở live desktop và browser
      gate đã chạy đủ 456/456 cấu hình QA ở phone/tablet/desktop, light/dark. Cần một lần
      đo production `390×844` hoặc tương đương để xác nhận header/PWA không clipping trên máy thật.
- [x] **R216-P — CLOSED_WITH_EVIDENCE:** `/login?lang=vi|en|zh` có tiêu đề tương ứng
      (`Đăng nhập · TOAN AAS`, `Sign in · TOAN AAS`, `登录 · TOAN AAS`) và không còn ba
      chuỗi cài ứng dụng cũ `📲Tải & Cài đặt App TOAN AAS`, `📲Install TOAN AAS App`,
      `📲安装 TOAN AAS App`.
- [x] **Delivery evidence:** PR #648 đã merge thành `506d2b9`; deploy workflow
      `39039077676` báo forward-only guard, backup, `toanaas-web.service`, `nginx.service`
      và `/health` `TOAN AAS Web App/app.py` đều đạt. Backup:
      `/opt/toanaas/webapp/delete/deploy-506d2b9fd494993a17d01ab783095db85a6a6f5e-20261017140326`.
- [x] **Safety:** live probe chỉ GET/navigation/screenshot; `PROVIDER_CALLS=0`,
      `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0`; không đăng nhập production,
      không gửi form, không upload và không tạo tác vụ.

## 11. Tổng trạng thái tại ngày 2026-10-17

| Nhóm | Đã có bằng chứng | Đang mở | Bị chặn/hoãn |
|---|---:|---:|---:|
| Source UI/UX/locale/static motion | R217-10 motion `43/43`; full Node `523/523`; Auth/Motion syntax `2/2` | product-lane runtime/AX chưa đo; FPS/CLS/LCP/INP trace chưa có | 2 source-matrix AI lanes thiếu entitlement (Transform/Upscale) |
| Responsive/PWA live | R216-L/R216-P `CLOSED_WITH_EVIDENCE`; bundle `local-00d9a64e11a5031705e6`; live desktop pass | R216-H + mobile production viewport/PWA placement | QA runtime/trace riêng |
| Customer product parity UI | shell/partial nhiều lane | 6 lane acceptance | real-output bridge |
| Admin/customer wiring UI | source contracts rải rác | 1 master surface audit | backend/permission mutation |
| Authenticated QA | source runner + Admin fixture; CI `39030607461` và artifact `456/456` | local runtime/trace riêng | bundled local dependency thiếu; production không thay thế QA |
| Technical parity/real output | 0 cho bridge AI | 0 trong wave UI | W9 deferred |

## 12. Quy tắc cập nhật bắt buộc

Mỗi lần làm một spec phải cập nhật ngay bảng này với `status`, `date`, `HEAD_SHA`, lệnh
verify, số pass/fail, screenshot/DOM evidence và blocker. Không xóa item đã đóng; nếu
phát hiện lỗi mới, thêm một dòng ở đúng wave và ghi `OPEN`. Checklist này là ledger duy
nhất để quyết định wave tiếp theo.

```ini
STATUS=VERIFIED_LIVE_PARTIAL
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
MERGE=PR_648_MERGED_506d2b9
DEPLOY=WORKFLOW_39039077676_SUCCESS_RUNTIME_506d2b9
LIVE_PASS=PARTIAL_R217_12_READ_ONLY
NEXT_ACTION=Giữ R216-H/LIVE-UI-01/LIVE-UI-02 mở cho một lần đo production mobile `390×844`
hoặc tương đương; R216-L/R216-P đã khóa. Giữ các lane sản phẩm/bridge/real-output và W9
deferred theo checklist hiện hành, không suy diễn 456/456 QA thành real provider output.
PROVIDER_CALLS=0, WALLET_MUTATIONS=0, PRODUCTION_DATA_MUTATIONS=0,
DEPLOY=WORKFLOW_39039077676_SUCCESS_RUNTIME_506d2b9, MERGE=PR_648_MERGED_506d2b9,
LIVE_PASS=PARTIAL_R217_12_READ_ONLY.
```
