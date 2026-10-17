# Checklist tổng WebApp standalone — UI/UX, product parity, locale và motion

**Checklist ID:** `WEBAPP-UIUX-PARITY-20261016`
**Plan:** `docs/superpowers/plans/2026-10-16-webapp-uiux-product-parity-master-plan-r217.md`
**Baseline remote:** `f59eacf63a49534854dc7cde06e5baed6546dc58`
**PR liên quan:** #647 — đang mở, chưa merge/deploy
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
- [ ] QA runtime cô lập có URL/lệnh và tài khoản fixture ổn định.
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
- [~] **LIVE-UI-01:** viewport khoảng 327×667 còn clipping cụm header landing; source đã
      có media rule `max-width:420px`, cần delivery rồi chụp lại DOM/screenshot.
- [~] **LIVE-UI-02:** PWA FAB bundle cũ còn nổi che vùng proof; source đã có placement
      inline/readiness gate, cần runtime recheck.
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
- [ ] Đo viewport 320/375/390/414/768/1024/1440 ở light/dark; ghi `scrollWidth <= clientWidth`.
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
- [ ] Kiểm tra fallback locale, duplicate key, option label và aria-label ở VI/EN/ZH.
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
      panel Lồng tiếng và Phụ đề + lồng tiếng; regression SubDub `12/12` và Voice focused
      `47/47` vẫn xanh.
- [!] `SUBDUB_VOICE_LIBRARY_LINK_MISSING` runtime: selector đã có trong UI nhưng chưa nối
      dữ liệu Voice thật; upload/CTA vẫn guarded và target language custom chỉ là input
      presentation chờ server xác minh.
- [x] Source discoverability đã thêm liên kết `Mở Thư viện giọng` tới `/voice-studio` cho cả
      panel Lồng tiếng và Phụ đề + lồng tiếng; selector vẫn guarded, không tạo dữ liệu Voice giả.

### 5.5 Product Video — Spec R217-08

- [ ] Hub dọc liệt kê các lane video hiện có, mỗi lane có mục tiêu, input, output và
      boundary riêng; không gộp tên kỹ thuật vào CTA.
- [ ] `/video/create` và `/video/multiscene` giữ flow bảy bước nhập → plan → quote →
      confirm → progress → result → recovery.
- [ ] Có AI edit và manual edit: scene/timeline, poster, caption/audio handoff, upload/
      reference, version/history và report.
- [ ] Không tuyên bố real MP4/provider output khi parity matrix đang `PARTIAL` hoặc
      `BLOCKED_BY_RUNTIME`; phải link request/job/report thật nếu có.
- [!] `VIDEO_AI_MANUAL_EDIT_UI_MISSING`: AI edit/manual edit/timeline/render MP4/delivery
      chưa có evidence; Video Studio hiện là planning/scene/review/version metadata.

### 5.6 Content, Workboard, Free Tools, Notes, Projects — Spec R217-09A

- [~] Source presentation của Content Studio, Workboard, Free Tools, Notes, Projects,
      Publish Review và Campaign đã có regression focused `28/28`; browser/runtime state
      và dữ liệu ghi thật vẫn mở. Mỗi surface có create/edit/save/archive/restore/version/history
      phù hợp và state
      empty/loading/error/guarded.
- [~] Campaign/Calendar/Approval source chrome có mốc, trạng thái, lịch, review và handoff;
      browser/runtime vẫn mở, server action/CSRF/revision không đổi.
      server action/CSRF/revision.
- [~] Free Tools/Prompt Gallery source có filter, copy/save và tách fixed chrome khỏi prompt
      data; Workboard có board/list/card dọc trên mobile.
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
- [~] Browser motion acceptance còn mở: chưa có trace FPS/CLS/LCP/INP và chưa chứng minh
      scroll reveal không tạo vùng trống trên runtime mới.
- [ ] Kiểm tra micro 150–300ms, exit nhanh hơn entry; auth/customer entrance giữ 680ms theo
      R216/WA-35 và landing cinematic giữ 980ms; không animate
      quá 1–2 nhóm chính mỗi view, không dùng linear cho UI.
- [ ] Kiểm tra route unmount: observer/RAF/timer/listener bị hủy và async hydration không
      ghi vào shell đã thay.
- [ ] Kiểm tra `prefers-reduced-motion` trước và khi đang chạy; nội dung vẫn hiển thị.
- [ ] Chụp Performance trace đại diện desktop/mobile; ghi CLS <0.10, LCP ≤2.5s, INP ≤200ms
      hoặc ghi blocker nếu runtime không đo được.

## 8. W7 — Authenticated QA matrix — Spec R217-11

- [!] QA runtime cô lập chưa được cung cấp ổn định; không tự động tạo tài khoản production.
- [ ] Tạo fixture `customer_qa` và `canonical_admin_qa` chỉ trong DB QA cô lập, không ví,
      không provider, không bridge mutation.
- [ ] Ma trận route × locale (VI/EN/ZH) × theme (light/dark) × viewport
      (375/390/768/1440) cho customer và Admin.
- [ ] Mỗi route kiểm tra DOM title/heading/CTA/field, AX labels, focus, screenshot,
      console error/warning, network request và persistence sau reload.
- [ ] Các lane Image/Voice/Music/SubDub/Video phải có evidence từng state; nếu engine chưa
      có, evidence phải chứng minh guarded boundary chứ không gọi output PASS.

## 9. W8 — Live read-only recheck — Spec R217-12

- [~] Recheck R216-L `/features → /login?next=/features`: redirect đã xác nhận ở VI/EN/ZH,
      `main#portal-main` có `tabindex=-1`; bundle cũ vẫn chứa hidden VI text
      `📲Tải & Cài đặt App TOAN AAS`, chưa đóng cho tới khi fingerprint mới được giao.
- [~] Recheck R216-H landing 327×667: header clipping và PWA FAB bundle cũ từng còn;
      cần DOM/screenshot mới.
- [~] Recheck R216-P direct login/next-route: không có install CTA trong AX/visible DOM vì
      vùng auth install đang `display:none`; hidden legacy button vẫn tồn tại trong bundle cũ,
      cần xác nhận lại sau delivery fingerprint mới.
- [~] Ghi asset fingerprint, runtime SHA nếu có, viewport, URL, timestamp, DOM/AX và
      computed style; evidence mới vẫn lệch source SHA (`local-57e76aa281dcc721fdaa`), nên
      chưa đóng live.
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

## 11. Tổng trạng thái tại ngày 2026-10-17

| Nhóm | Đã có bằng chứng | Đang mở | Bị chặn/hoãn |
|---|---:|---:|---:|
| Source UI/UX/locale/static motion | W2 locale `319/319`; Image source `40/40`; full Node `521/521` | product-lane source acceptance còn mở; runtime/AX chưa đo | 2 source-matrix AI lanes thiếu entitlement (Transform/Upscale) |
| Responsive/PWA live | source fix đã có; CI evidence gần nhất `cb1fab6` | 2 drift (R216-H/R216-P) + ma trận viewport | QA runtime |
| Customer product parity UI | shell/partial nhiều lane | 6 lane acceptance | real-output bridge |
| Admin/customer wiring UI | source contracts rải rác | 1 master surface audit | backend/permission mutation |
| Authenticated QA | 0 | toàn ma trận | fixture/runtime |
| Technical parity/real output | 0 cho bridge AI | 0 trong wave UI | W9 deferred |

## 12. Quy tắc cập nhật bắt buộc

Mỗi lần làm một spec phải cập nhật ngay bảng này với `status`, `date`, `HEAD_SHA`, lệnh
verify, số pass/fail, screenshot/DOM evidence và blocker. Không xóa item đã đóng; nếu
phát hiện lỗi mới, thêm một dòng ở đúng wave và ghi `OPEN`. Checklist này là ledger duy
nhất để quyết định wave tiếp theo.

```ini
STATUS=ACTIVE_SOURCE_EXECUTION
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
NEXT_ACTION=R217-06 Music — Voice source presentation đã có lane rail xanh/navy và test Voice 126/126 xanh; runtime TTS/clone/preview/output và Voice Library handoff vẫn guarded. Giữ R217-04/R217-05 runtime mở, chuyển Music theo thứ tự trước SubDub và Video.
```
