# Checklist tổng — Bot → Web App, UI/UX và motion

- **PLAN_ID:** `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009`
- **CONTROL_SPEC:** `WEBAPP-PRODUCT-CONTROL-BY-CONTROL-UX-20261010`
- **SHARED_SHELL_SPEC:** `WEBAPP_SHARED_SHELL_UI_CLOSEOUT`
- **SHARED_SHELL_SPEC_FILE:** `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`
- **MOTION_SPEC:** `MOTION-WEBAPP-SURFACES-FINAL-20261010`
- **Trạng thái:** `WA35_RCA_OPEN_R40_BROWSER_ENV_BLOCKED_R39_TEMP_PACKAGE_INSTALL_DENIED; WA36_PARTIAL`
- **Current-main đã đọc:** `86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` — chỉ là mốc đã đọc; phải làm mới trước khi bắt đầu code.

> Dấu `[x]` trong phần A xác nhận chỉ việc rà soát/ghi tài liệu. Nó không đóng
> tính năng, không chứng minh runtime và không phải nghiệm thu sản phẩm.

## A. Hoàn tất bộ kế hoạch — dừng sau phần này

- [x] Đối chiếu nội dung Owner gửi với source/evidence đã có; tách dữ kiện xác minh được, nhận định chưa tái hiện và yêu cầu cần điều tra.
- [x] Ghi lại current-main drift sau UI checkpoints, gồm Music #621 và các thay đổi bridge/runtime làm UI snapshot cũ không còn đủ làm bằng chứng.
- [x] Không tuyên bố 12 lỗi ViewTransition là lỗi trên current main khi chưa có trace tái lập.
- [x] Bổ sung spec từng control, tiêu chuẩn trạng thái, bố cục, locale, màu, responsive, accessibility và bằng chứng tối thiểu.
- [x] Tách shared shell thành spec riêng; không để từng sản phẩm tự vá điều hướng, locale, theme hoặc nút nổi.
- [x] Tách checklist này khỏi checklist ERP P0 cũ để không nhầm tiến độ hai luồng.
- [x] Tạo spec motion cuối riêng và ghi rõ việc WA-35 đang dở.
- [x] Kiểm tra độ phủ plan: bổ sung riêng Wallet/nạp thủ công → Admin billing, tách Admin ERP khỏi nhãn parity Bot và thêm cổng tham khảo giao diện có nguồn.
- [x] Tạo spec riêng cho luồng Wallet/Admin; chưa tự điền số phương thức, API, mã hoặc quyền khi nguồn canonical chưa khóa.
- [x] Vòng lập plan trước đã dừng sau kiểm tra tài liệu; sau đó Owner cho phép tiếp tục QA localhost trong `%TEMP%`, không sửa code, không chạy production/provider, không tạo PR/merge/deploy.

## B. Việc tiếp theo: tiếp tục phần WA-35 đang dở

### Bằng chứng QA R23–R35 — đã thấy render churn; chưa đủ đóng WA-35

- Trace: `%TEMP%\toanaas-wa35-r22\wa35-lifecycle-r23.json`; ảnh Dashboard và
  Wallet cùng thư mục. Chỉ số asset là `local-8b6e2dea62f4a56a5657`; trace không
  ghi full `CURRENT_SHA`, nên không đại diện cho một SHA đã khóa.
- `/dashboard`: `#portal-main` có `animationstart=1`, `animationend=1`,
  `animationcancel=0`; một lần gọi View Transition; cuối cùng node còn kết nối,
  opacity `1`, transform `none`; 16 child-list mutation record và long task lớn
  nhất `99 ms`.
- `/wallet/topup`: cùng trạng thái hiệu ứng cuối và số sự kiện `1/1/0`; một lần
  gọi View Transition; 12 child-list mutation record và long task lớn nhất
  `207 ms`.
- Cả hai route: không có page/console error, request lỗi hoặc request ngoài
  localhost; không có layout shift được ghi nhận và không tràn ngang.
- Mutation record không đồng nghĩa với số lần `TOANAASPortal.mount()`; R23 không
  có caller stack cho `mount()`/`merge()`, nên chưa chứng minh nguồn churn hay
  nguyên nhân khựng. `CURRENT_SHA` chưa được ghi; không sửa code từ trace này.
- R24 không tạo trace vì cổng `14179` bind lỗi `WinError 10048`; R25 không có
  trace artifact. Lần gửi ngắt đúng session `61755` đã được Owner cho phép nhưng
  công cụ trả `Unknown process id`; không dừng tiến trình nào khác.
- R27/R30/R34/R35 chạy lại trên QA localhost ở HEAD
  `45b84de83ee9b475bb4366c3ddc2af85b82297c4` cùng dirty source overlay. SHA-256
  overlay: `portal.js=520978f0…3b22d6`,
  `integration.js=cfc08d9a…797c9`, `portal-motion.js=8779d4f5…c366c`,
  `portal-features.js=4e091257…ed431`. Mỗi lần dùng bản sao DB QA ở `%TEMP%`,
  tài khoản QA mới, Edge riêng trong `%TEMP%`, và chặn yêu cầu không phải
  localhost; `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`.
- R27 `/dashboard`: HTTP 200, một lần vào trang `portal-customer-observable-enter`
  và một lần kết thúc sau `0.68 s`, không cancel; không lỗi JS/console/request,
  không yêu cầu ngoài localhost, không layout shift hoặc tràn ngang.
- R30 `/features` được xác minh là luồng riêng: chỉ tải
  `portal-features.js`, `hydrateFeatures → renderShell → mountFeatureMotion`;
  entrance trên `.portal-hero` kết thúc sau `0.68 s`, không cancel. Long task lớn
  nhất `216 ms`; không lỗi, layout shift, request ngoài localhost hoặc tràn ngang.
- R34/R35 Dashboard đã bọc trực tiếp `window.TOANAASPortal.mount()` để đo caller
  và thời lượng. Trong khoảng quan sát `5.3 s`: **10 mount tổng** gồm mount đầu
  và **9 mount `reason=data-hydration`**, khớp **9 `integration.merge()`**.
  Stack merge bắt đầu ở `startInitialHydration → hydrate`, sau đó gồm các nhánh
  `hydrate`, `hydrateProjects`, `hydrateAdminErpNavigation`, `hydrateAssetVault`,
  `hydrateWorkspaceSetup` và `hydrateWorkspaceDrafts`. Mỗi mount mất `9.7–27.2
  ms` (R35), tổng khoảng `146 ms`.
- Dù có nhiều merge/mount, R35 chỉ ghi **một** animation entrance cho
  `#portal-main`, hoàn thành sau `0.68 s`, không cancel; 160 mutation records
  quanh vùng theo dõi. R34 không ghi lỗi JS/console/request, layout shift hoặc
  tràn ngang. Điều này xác nhận hydration làm remount nhiều lần nhưng chưa chứng
  minh animation bị phát lại.
- R35 đo long task `223`, `198`, `252 ms` và frame gap `700 ms` cùng một số gap
  `50–150 ms`; các thời lượng mount riêng ngắn hơn nhiều, nên **chưa kết luận**
  chúng là nguyên nhân đầy đủ của các long task/frame gap. R31 CPU profiler có
  `program` không gắn URL/function đủ để quy kết. Response cold local chưa nén
  lớn: `portal.js≈4.09 MB`, `integration.js≈2.44 MB`, `portal-i18n.js≈1.22 MB`,
  `portal.css≈0.74 MB`, `portal-theme.css≈0.78 MB`; đây là kích thước response
  trên harness localhost, không đại diện kích thước truyền production.
- Raw evidence nằm ngoài repo ở `%TEMP%\toanaas-wa35-r26\`: `wa35-lifecycle-r27.json`,
  `wa35-lifecycle-r30-features.json`, `wa35-cpu-profile-r31.json`,
  `wa35-lifecycle-r34-dashboard.json`, `wa35-lifecycle-r35-dashboard.json` và
  các ảnh cùng tiền tố `wa35-r27-*`, `wa35-r30-*`, `wa35-r34-*`, `wa35-r35-*`.
  Không lưu mật khẩu, cookie value hay session vào evidence.

### Bằng chứng QA R36 — đã phủ ma trận mẫu; hiệu năng và full-site vẫn mở

- [x] Chạy Chrome/Playwright trên localhost `127.0.0.1:14283`, dùng DB/tài khoản
  QA cô lập trong `%TEMP%`, chỉ cho request loopback; không dùng production,
  provider, ví hoặc dữ liệu production.
- [x] Hoàn tất 16/16 ô: `/features`, `/dashboard`, `/studio`, `/wallet/topup` ×
  `1440x900` / `390x667` × normal / reduced motion. Page/console error, request
  lỗi, request ngoài localhost, CLS và tràn ngang đều bằng `0`.
- [x] Normal: 8/8 lượt có đúng 1 entrance hero/main start/end `0.68s`; reduced:
  0/8 entrance hero/main. Features reveal đủ 12 nhóm ở cả normal/reduced.
- [ ] WA-35/36 chưa PASS: 11/16 lượt có long task `>200ms`, 16/16 có frame gap
  `>200ms`; cao nhất lần lượt `761ms` và `866.7ms`. LoAF tệ nhất `874.7ms`,
  blocking `749.7ms`; script attribution mới một phần.
- [ ] Dashboard normal giữ `.portal-dashboard-assurance` ở trạng thái
  `is-pending`, chiều cao `0`; CSS chủ động ẩn vùng assurance kỹ thuật. Xác định
  rõ target ẩn có nên bị loại khỏi motion observer/contract hay không, không
  tính đây là nội dung khách đã nhìn thấy và không bỏ qua trong kiểm thử.
- [ ] Mở rộng route/auth, cold/warm, rapid navigation, Back/Forward và scroll
  reveal; lặp attribution theo cùng fixture để phân biệt nguồn motion với bundle
  dùng chung. Không sửa code chỉ từ tương quan tên script.
- Artifact: `C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\outputs\wa35-r36-attributed-20261010\matrix.json` và 16 ảnh/JSON
  theo từng lượt (nằm ngoài repo); runner kết thúc `FOCUSED_HYDRATED_MOTION_PASS`,
  exit `0`. Đây không phải hiệu năng PASS.
- Regression harness cũ: lifecycle/fallback `7 passed, exit 0`; không tạo test
  trùng. Git HEAD `45b84de83ee9b475bb4366c3ddc2af85b82297c4` + dirty source overlay;
  không gán cho main/production.
- Trạng thái an toàn: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `COMMIT=NO`, `PUSH=NO`, `DEPLOY=NO`,
  `LIVE_PASS=NO`.

### Bằng chứng QA R37 — entrance/reveal có mẫu mượt; cold-load vẫn khựng

- [x] Chạy Chrome/Playwright trên localhost `127.0.0.1:14283` với một tài khoản
  dùng một lần và DB QA cô lập; request chỉ tới loopback. Git HEAD
  `45b84de83ee9b475bb4366c3ddc2af85b82297c4`; bốn source hash trước/sau không đổi.
- [x] Thu 12 hàng `/wallet/topup`, `/dashboard`, `/features` ở desktop `1440x900`,
  normal/reduced, điều hướng đầu và reload cùng BrowserContext; thêm một hàng
  scroll-reveal trên `/features` (13 case tổng). Chưa có mobile, anonymous,
  rapid navigation hoặc Back/Forward.
- [x] Normal: main/sidebar entrance có cặp start/end khớp ở 6/6 lượt. Reduced:
  không có main entrance ở 6/6 lượt. Một mẫu scroll-reveal `/features` có 72 nhịp,
  gap tối đa `17.1ms`, không gap nào `>50ms`; target được cuộn tới đã hết
  `is-pending`.
- [x] Page/console error, failed request, external origin và CLS đều bằng `0` ở
  các case đã ghi. Không coi đây là kết quả về horizontal overflow hoặc
  `animationcancel`: runner R37 không instrument hai tín hiệu đó.
- [ ] **Cold-load performance còn lỗi:** long task lớn nhất `563ms`, LoAF lớn
  nhất `610ms` với `517ms` blocking, gap khung hình lớn nhất `999.9ms`. Wallet
  reduced cold vẫn có task `381ms`/`244ms` và gap `466.5ms`; không kết luận tắt
  motion đã xử lý khựng.
- [ ] Sáu lượt reload cùng phiên không có long task `>200ms`, gap tối đa `100ms`,
  nhưng `transferSize` của `portal.js`/`integration.js` không giảm; chưa chứng
  minh cache hit nên không gọi đây là warm-cache PASS.
- [ ] Dashboard normal vẫn có một `.portal-dashboard-assurance...is-pending`
  bị CSS `display:none`, không có hình học. Không phải nội dung khách bị che;
  vẫn cần loại trừ có chủ đích hoặc điều chỉnh observer contract trước khi đóng.
- [ ] Attribution LoAF mới gắn một phần tới `portal.js`/`integration.js`, chưa
  chứng minh nguyên nhân nằm ở motion. Không sửa sản phẩm nếu chưa có RED gắn
  đúng motion layer; nếu nguyên nhân thuộc bundle dùng chung thì ghi chủ sở hữu
  và mở đúng lane, không lấn route/engine.
- Bằng chứng: `C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\outputs\wa35-r37-measurement-20261010\browser\r37.json`;
  ảnh cold ở cùng thư mục. JSON ghi `providerCalls=0`, `walletMutations=0`,
  `productionDataMutations=0`, `externalOrigins=[]`. Browser JSON đã được tạo,
  nhưng wrapper dừng server với `SERVER_EXIT=-1`/exit `1`; không ghi runner clean
  exit. Cổng `14283` hiện không lắng nghe; đã xóa đúng hai thư mục DB QA của
  lượt này, giữ nguyên JSON/ảnh. Chưa sửa mã sản phẩm; chưa production/live test.

### Bằng chứng QA R38c/R38d — harness lỗi, browser runner bị chặn

- [x] Đọc lại artifact R38c: `/dashboard` thực sự có title, customer shell và
  `#portal-main`; `dashboard_rendered=false` là predicate sai của harness.
- [x] Target Dashboard cuộn tới chuyển sang `is-visible`, animation CSS
  `portal-customer-observable-enter` có duration `0.68s`. Target assurance kỹ
  thuật là `display:none`, `0×0`, không `is-pending` và không được observe ở
  trạng thái cuối; không xem nó là nội dung khách bị che.
- [x] Đối chiếu R38c cho desktop `1440x900`, mobile `390x844` và mobile reduced:
  reduced motion được nhận diện, không tràn ngang; console error và response
  lỗi cục bộ đều `0`. Harness cấu hình chặn request ngoài localhost và không ghi
  nhận request ngoài. Artifact không gắn `HEAD_SHA`/source fingerprint.
- [ ] R38c **không đóng lifecycle**: hai lỗi instrumentation do gọi
  `MutationObserver.observe()` trước khi `document.documentElement` tồn tại;
  `classHistory`, `animationend`, `animationcancel` rỗng/không đáng tin.
- [ ] R38d runner dùng đúng `document` observer nhưng Chrome không khởi động:
  `chrome.log` ghi Crashpad không mở metadata rồi tự thoát; không có
  `r38d.json`. Không diễn giải đây là lỗi motion của sản phẩm.
- [ ] Temp runtime mới không dựng xong trong sandbox: venv `ensurepip` lỗi,
  pip không ghi được thư mục unpack tạm; auto-review từ chối escalated execution.
  Không thử vòng qua sandbox. Browser acceptance vẫn chưa chạy được.
- [x] Dùng lại gói pytest đã có trong TEMP để chạy hai contract suite
  `test_wa35_motion_entry_fallback_contracts.py` và
  `test_motion_webapp_dashboard_stability_001_contracts.py`: **8 passed, exit 0**.
  Đây chỉ là kiểm thử hợp đồng tĩnh, không thay thế browser trace.
- [x] Kiểm cú pháp JS `node --check static/portal/portal-motion.js`: exit `0`;
  đây chỉ là syntax check, không phải browser acceptance.
- Artifact R38c:
  `C:\Users\toann\AppData\Local\Temp\toanaas-wa35-r38-bf30f5f560734ebb911f2f29e0262f2f\browser-r38c-20261010\evidence\r38.json`
  và bốn ảnh Dashboard. Log R38d:
  `C:\Users\toann\AppData\Local\Temp\toanaas-wa35-r38-bf30f5f560734ebb911f2f29e0262f2f\browser-r38d5-evidence-20261010\chrome.log`;
  chưa có trace JSON hợp lệ.
- [ ] Giữ WA-35/WA-36 mở; chưa có lỗi motion được tái hiện đủ để sửa code.
  Bước kế tiếp là chạy probe R38d trong runtime QA browser-enabled có quyền,
  đo đúng start/end/cancel/class history rồi mới quyết định có sửa không.
- Trạng thái an toàn: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `COMMIT=NO`, `PUSH=NO`, `DEPLOY=NO`,
  `LIVE_PASS=NO`.

### R39 — đã được Owner cấp quyền nhưng runtime pip vẫn bị chặn

- [x] Owner cho phép tạo môi trường Python QA tạm trong `%TEMP%`; quyền thư mục
  tạm riêng và mạng đã được cấp trong lượt này. Không sửa dependency của repo.
- [x] Xác nhận Python tích hợp hiện không có `fastapi`, `uvicorn` hoặc `starlette`;
  Playwright không dùng được từ runtime Node đóng gói hiện tại.
- [ ] Hai lần cài phụ thuộc server vào target TEMP không thành công: pip không ghi
  được `pip-unpack-...` trong AppContainer temp của từng tiến trình, kể cả khi
  `TEMP`/`TMP` được trỏ về đúng thư mục con đã cấp. Không package nào được cài;
  không khởi chạy server, không mở browser và không có trace R39.
- [x] SHA nguồn motion hiện tại là
  `C70752BAE488EB8D91069173B6F7D9E41F09C73A2F6985526BACF41FB0159326`, khác SHA
  overlay từng ghi `8779D4F57A1B560BF817BC07CD2BB01B39885153D49D3CBF4035DE590C76C366`.
  `portal-motion.js` đã bẩn từ đầu lượt; lượt này không sửa file. Diff đang có
  40 thêm/15 xóa, gồm clear delay `760 → 1200 ms` và thay đổi phân loại target
  IntersectionObserver; thời điểm/nguồn thay đổi chưa xác định. Không gán trace
  R38 cho source SHA hiện tại.
- [ ] Không lặp lại cài pip, nâng quyền, tải/giải nén package bằng đường khác hoặc
  thay sandbox để né chặn. Tiếp tục khi có runtime QA browser-enabled sẵn dùng và
  được phép mà không vượt sandbox; blocker này không phải lỗi motion của sản phẩm.
- [ ] Giữ WA-35/WA-36 mở; R38c còn partial, R38d/R39 không có browser acceptance;
  phải rebaseline source SHA hiện tại trước trace mới. Cold-load performance và
  ma trận route/state vẫn chưa đạt.

- [ ] Giữ nguyên worktree bẩn và mọi thay đổi hiện có; không reset, stash, checkout, rebase hoặc ghi đè mù.
- [x] R23 xác nhận localhost/TEMP/DB QA cô lập; trace ghi `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0`.
- [x] Chạy probe `/dashboard` và `/features` trong cửa sổ entrance, ghi `animationstart`, `animationend`, `animationcancel` trên QA localhost normal-motion.
- [ ] Bổ sung trace mẫu đủ `getAnimations()`, `currentTime/endTime`, computed opacity/transform/duration, identity node, attribute trước/sau và caller stack cho từng route/state; các trace hiện có không ghi đủ giá trị attribute trước/sau.
- [x] Phân loại event entrance cho hai route mẫu: mỗi entrance kết thúc đúng `0.68 s`, không cancel; đã phát hiện luồng Dashboard có 9 lần hydration merge gây 9 mount bổ sung. Chưa quy frame-gap/long-task cho nguyên nhân duy nhất.
- [x] Tái sử dụng regression harness đã có: baseline `896d3761…` tái hiện replay, source hiện tại giữ hydration cùng route ở trạng thái settled; hai test lifecycle/fallback chạy **7 passed, exit 0** trên dirty source overlay đã ghi.
- [x] Đã bổ sung trace trình duyệt R36 và attribution script một phần; harness vẫn chỉ mô phỏng hai merge hydration, không tái tạo đủ chín merge của R35. Không tạo test trùng.
- [ ] Sửa đúng nguyên nhân entrance trong allowlist sau khi RCA; giữ nguyên màu xanh–teal và logic nghiệp vụ/route/engine.
- [ ] Dùng trace cùng fixture để giải thích long task `>200 ms` ở 11/16 hàng và frame gap `>200 ms` ở 16/16 hàng; R36 chỉ quy một phần script và chưa chứng minh lỗi nằm riêng ở animation/mount.
- [x] Chạy ma trận mẫu WA-35/36 normal/reduced: 16 hàng, `FOCUSED_HYDRATED_MOTION_PASS`, exit `0`; chưa đủ route/auth/state để đóng WA-35/36.
- [ ] Chạy các protected comparators UI/motion bị ảnh hưởng; chỉ đóng defect có evidence mới.

## C. Rebaseline và khóa nguồn trước khi mở sản phẩm

- [ ] Sau khi WA-35 đang dở khép tại một điểm dừng an toàn, cập nhật SHA `origin/main`; nếu source đã tiến, làm lại source-touch matrix.
- [ ] Tách Bot Git HEAD, dirty overlay, ma trận lịch sử và Web main thành các nguồn riêng; không nhập chung fingerprint.
- [ ] Khóa Bot source canonical/deployed bằng SHA có provenance; nếu chưa xác nhận được, ghi blocker và không kết luận parity.
- [ ] Quét inventory bằng cách đọc source an toàn; không import/chạy Bot, không đọc secret/data/attachment, không gọi Telegram/provider.
- [ ] Dựng action ledger Bot đầy đủ command/callback/template/handler/Admin action; record nguồn phải khớp tổng auditor.
- [ ] Dựng `WEBAPP-PRODUCT-UI-ACTION-LEDGER.md` và `.json` từ source + DOM thực tế; mỗi route/action/control/state-dependent action là một dòng.
- [ ] Đạt `UNKNOWN/UNREVIEWED=0` trong phạm vi snapshot đã khóa; các mục Telegram-only/Admin-only/read-only/backend gap phải có lý do và disposition.
- [ ] Chưa cho builder làm capability nào khi control/action tương ứng còn `UNKNOWN`, thiếu quyền, payload, quote, state hoặc output contract.

## D. Checklist nghiệm thu chung cho từng action/control

Dùng thêm toàn bộ trường bắt buộc trong
`docs/superpowers/specs/2026-10-10-webapp-product-control-by-control-ux.md`.

- [ ] Source SHA, path/line, route, auth state, selector ổn định và DOM/evidence đúng trạng thái.
- [ ] Nhãn, aria/help VI/EN/ZH khớp; tiếng Việt tự nhiên, tiếng Anh thuần Anh, không trộn ngôn ngữ cố định.
- [ ] Mục đích control, nhóm dọc, thứ tự thao tác, primary/secondary hierarchy và trạng thái được mô tả.
- [ ] Điều kiện hiện/bật/tắt, role, owner, validation và disabled reason khớp server contract.
- [ ] Request/payload, canonical quote/cost, idempotency/duplicate behavior và state transition có nguồn kiểm chứng.
- [ ] Success chỉ báo sau kết quả thật; lỗi/permission/offline có hướng phục hồi và giữ input.
- [ ] Báo cáo Admin/khách nối đúng actor, request/job, trạng thái và artifact; ID/job không bị gọi nhầm là đầu ra.
- [ ] Giữ brand xanh–teal; giao diện tối xanh đậm/chữ sáng, không đổi nền thành đen.
- [ ] Form/list theo cột dọc; ngoại lệ bố cục ngang chỉ dành cho canvas/timeline/editor khi cần thiết thật.
- [ ] Đo tương phản WCAG AA, focus bằng Tab, touch target ≥44×44 px, tiếng Việt không cắt dấu.
- [ ] Kiểm 360/375/768/1440 px; không tràn ngang, crop logo/control, mất input khi bàn phím mở.
- [ ] Có trạng thái rỗng, tải, đang chạy, thành công, validation, quyền, lỗi server/network và đường phục hồi.
- [ ] Có hành vi reduced motion; animation không mang nghĩa duy nhất, không animate layout.
- [ ] Có một lệnh verify chạy được, kết quả mong đợi, ảnh/JSON hoặc artifact và reviewer độc lập.
- [ ] File sửa được/cấm sửa và protected comparators được ghi trong phiếu; không sửa engine/route/giá/ví ngoài scope được Owner duyệt.

## E. Trình tự sản phẩm — không nhảy thứ tự

### E0 — Landing và shared shell

- [ ] Trước khi thiết kế UI mỗi nhóm, hoàn tất `UI-REF-00`: tối đa 2 nguồn tham khảo có URL/ngày truy cập; ghi rõ mẫu tương tác/bố cục học được và điều không sao chép. Bot/current API vẫn là nguồn quyết định nghiệp vụ; giữ màu xanh–teal/blue.
- [ ] Landing/trang chào mừng có một H1 rõ, luận điểm chính dùng đậm/màu brand có tiết chế, một CTA nổi bật; không có số liệu/chứng thực giả.
- [ ] Phân cấp chữ dùng type scale hiện hữu; H1 32–48px linh hoạt, H2 24–36px, H3 20–24px, body 16px, label 14px, tối đa 6 cỡ/màn; đo current token trước khi sửa.
- [ ] Đo line-height và hiển thị dấu tiếng Việt ở các weight/viewport; chữ body ≥1.625, heading ≥1.25.
- [ ] Chốt route/DOM nguồn trên current main cho điều hướng, drawer/sidebar, locale, theme, account/auth, trợ lý/cài ứng dụng, Back/Forward và focus order.
- [ ] Kiểm anonymous/authenticated, VI/EN/ZH, sáng/tối, desktop/tablet/mobile.
- [ ] Đạt locale fixed-copy sạch, không tràn ngang, không điều khiển nổi trùng, focus trap hoặc layout shift bất ngờ.
- [ ] Nếu hỗ trợ PWA: kiểm manifest/install/icon/start URL/scope, standalone có đường quay lại, safe-area/bàn phím/zoom 200%, offline và phản hồi thao tác ghi, service-worker cập nhật; mục không hỗ trợ phải có bằng chứng `NOT_APPLICABLE`.
- [ ] Shared shell chạy riêng theo `docs/superpowers/specs/2026-10-10-webapp-shared-shell-ui-closeout.md`; chỉ dùng selector/route có trong inventory current-main, không suy đoán.

### E1 — Voice

- [ ] Tách giọng mặc định/preset, dùng giọng đã lưu, tạo/nhân bản giọng và quản lý profile; chỉ giữ action Bot đã xác nhận.
- [ ] Mỗi nút có readiness/consent/permission/report; profile tồn tại không đồng nghĩa giọng dùng được.
- [ ] Kiểm chứng audio bytes/MIME/duration ở gate được duyệt; local test không gọi provider trả phí.

### E2 — Music

- [ ] Tách tạo nhạc nền và tạo bài hát có lời.
- [ ] Đối chiếu từng tier, giọng, lời, độ dài, estimate/quote/confirm với contract current main; UI không là nguồn giá.
- [ ] Thư viện, SFX, upload/tệp âm thanh có action ledger riêng.
- [ ] Đầu ra audio hoặc lỗi cụ thể; không coi draft/job ID là thành công.

### E3 — SubDub

- [ ] Một giao diện; bốn mode theo capability Bot: phụ đề nguồn, chỉ lồng tiếng, phụ đề, phụ đề + lồng tiếng.
- [ ] Mỗi mode có trường, disabled reason, payload, request, trạng thái và báo cáo riêng.
- [ ] Thanh âm lượng chỉ được xác nhận hoạt động khi payload và file cuối cùng chứng minh.
- [ ] Kiểm report Admin/khách và artifact thực ở môi trường được duyệt.

### E4 — Image

- [ ] Tách tạo ảnh AI, sửa ảnh AI từ ảnh thuộc owner, chỉnh thủ công/deterministic.
- [ ] Không gắn nhãn AI cho thao tác deterministic; preview không giả; kiểm quyền, MIME/kích thước và tải đúng owner.

### E5 — Mọi nhóm không phải Video

#### Nhánh ưu tiên cao: nạp tiền khách hàng và duyệt thanh toán trong Admin

- [ ] Theo spec `docs/superpowers/specs/2026-10-10-webapp-wallet-admin-ui-closeout.md`; xác minh route/selector/API hiện hành trước khi thiết kế lại, không dùng ảnh cũ làm bằng chứng hiện trạng.
- [ ] Luồng khách đi theo cột dọc: chọn phương thức được nguồn xác nhận → nhập số tiền → xem lại/xác nhận → chỉ lúc đó mới hiện đúng mã/QR/hướng dẫn; trạng thái đầu không lộ mã/QR/nội dung thanh toán.
- [ ] Mã chuyển khoản, tài khoản nhận, số tiền, phí/giới hạn và phương thức lấy từ contract có thẩm quyền; không tự đoán hoặc thêm Binance/phương thức khác nếu API/Bot không xác nhận.
- [ ] Gửi yêu cầu chỉ tạo trạng thái đang chờ duyệt; hiện rõ mã yêu cầu, người dùng, số tiền, phương thức và bước tiếp theo; không thông báo đã nạp/chưa cộng tiền thành đã cộng.
- [ ] Admin có danh sách chờ và chi tiết đối soát đủ người dùng/ID, tiền, phương thức, nội dung giao dịch/chứng từ; duyệt hoặc từ chối có lý do, quyền, audit và chặn bấm lặp theo server contract.
- [ ] Test hành vi trong DB QA cô lập; `WALLET_MUTATIONS=0`, `PROVIDER_CALLS=0`, `PRODUCTION_DATA_MUTATIONS=0`; không tạo pending/live payment production trong wave này.

- [ ] Mỗi tiện ích Free Tool có input/action/output và quota/miễn phí thật.
- [ ] Notes/Memory/reminder: create/list/search/update/delete/priority theo Bot source; ghi `OWNER_NEW_REQUIREMENT` nếu chức năng chỉ mới yêu cầu.
- [ ] Documents/PDF/OCR/translation: upload/inspect/process/export/download/retry tách riêng; xác thực artifact cuối.
- [ ] Content/prompt tools: compose/save/copy/apply/export phân biệt draft với output.
- [ ] Channels/Auto-post: kết nối, soạn, duyệt, lịch, đăng, receipt, retry/idempotency; không báo đăng khi chưa có receipt.
- [ ] Projects/Workboard có action ledger riêng; không trộn task với job.
- [ ] Assets/Downloads có action ledger riêng; kiểm owner, readiness và artifact thật.
- [ ] Jobs/History có action ledger riêng; retry/cancel chỉ khi server hỗ trợ.
- [ ] Support/Tickets có action ledger riêng; giữ nội dung khi lỗi và kiểm trạng thái.
- [ ] Members có action ledger quyền/thành viên riêng; kiểm role, owner và audit.
- [ ] Rewards có action ledger điểm/quyền lợi/lịch sử riêng; không gộp với Members.
- [ ] Community/Referral có disposition/action riêng theo nguồn và quyền.
- [ ] Admin ERP ngoài billing có action ledger riêng; kiểm role, record, audit, confirm/undo và report. Không mặc định action quản trị nào cũng có counterpart Bot; nếu không có thì phân loại `ADMIN_ONLY`/`OWNER_NEW_REQUIREMENT`.
- [ ] Từng hành động ghi có role, audit/report và record owner; không coi route/nút hiện diện là server authorization.

### E6 — Video (sau cùng trong nhóm sản phẩm)

- [ ] Tạo inventory từng sản phẩm/entry Video từ Bot canonical source, không dùng bucket chung “Video còn lại”.
- [ ] Tách self-shot, trend, storyboard/script-to-screen, video dài/nhiều cảnh, import, render/export/history và các capability khác được nguồn xác nhận.
- [ ] Tách AI editor và manual/timeline editor thành spec/AC riêng.
- [ ] Kiểm output cuối bằng container/stream/duration/dimensions/ownership; planner/preview không là video đã xuất.

## F. Motion toàn site và chứng nhận cuối

- [ ] Khép motion đang dở và mọi surface sản phẩm ổn định trước final motion pass.
- [ ] Dùng ma trận trong `docs/superpowers/specs/2026-10-10-motion-webapp-surfaces-final.md`, không dùng pass một trang thay whole-site pass.
- [ ] WA-35 normal: route mẫu, trạng thái đăng nhập, desktop/mobile, cold/warm, scroll reveal, rapid navigation, Back/Forward.
- [ ] WA-36 reduced: không transition/transform/opacity ẩn nội dung; mọi control/nội dung hiện và điều hướng vẫn dùng được.
- [ ] Uncaught transition/runtime error, failed request, foreign request, overflow, duplicate control, hydration replay và hidden/pending content đều bằng 0 theo gate.
- [ ] Mỗi hiệu ứng được mong đợi có start/end hợp lệ hoặc cancel có nguyên nhân được chấp nhận; không còn trạng thái chờ vô hạn.
- [ ] Kiểm screenshot/JSON/trace/console/network và SHA; performance long-task/frame-gap quy nguyên nhân riêng, không chỉ ghi một con số tổng.
- [ ] Tester đọc độc lập; `MERGED != DEPLOYED != LIVE`; không có provider/wallet/production data mutation trong test mặc định.

## G. Đóng sổ mỗi spec

- [ ] Cập nhật dòng tương ứng trong checklist này và master plan trước khi giao spec kế.
- [ ] Ghi `SPEC_ID`, `BASE_SHA`, `HEAD_SHA`, files changed, exact test commands/output, failure delta, protected comparators, evidence path, provider/wallet/data mutation, deploy/live status.
- [ ] Nếu lỗi: mở lại đúng `SPEC_ID`, gắn evidence mới và sửa checklist; không nhảy sang spec khác để né.
- [ ] Không dùng `DONE`, `PASS`, `LIVE` nếu bằng chứng chỉ là code tồn tại, test renderer, HTTP 200 hoặc merge.

## Trạng thái tại điểm dừng này

```ini
PLAN_AND_CHECKLIST=READY
CONTROL_SPEC=READY; CONTROL_LEDGER=NOT_CREATED
MOTION_FINAL_SPEC=ACTIVE; WA35=OPEN_RCA_R38C_PARTIAL_R38D_BLOCKED_BROWSER_ENVIRONMENT_AND_INCOMPLETE_COVERAGE
WA35_LATEST_EVIDENCE=R38C_PARTIAL; ROUTE=/dashboard; VIEWPORTS=1440x900,390x844; MODES=NORMAL,REDUCED; CURRENT_LOCAL_HEAD=45b84de83ee9b475bb4366c3ddc2af85b82297c4_PLUS_DIRTY_OVERLAY; R38C_HEAD_BINDING=NOT_RECORDED
WA35_MAIN_ANIMATION_EACH_ROUTE=START_1,END_1,CANCEL_0; VIEW_TRANSITION_CALLS=1
WA35_CHILD_MUTATIONS=DASHBOARD_16,WALLET_TOPUP_12; NOT_MOUNT_COUNTS
WA35_R36=16_ROWS; PAGE_CONSOLE_FAILED_EXTERNAL_CLS_OVERFLOW=0; NORMAL_ENTRANCE_8_OF_8_0_68S; REDUCED_ENTRANCE_0_OF_8
WA35_R36_PERFORMANCE=LONG_TASK_GT_200MS_11_OF_16_MAX_761MS; FRAME_GAP_GT_200MS_16_OF_16_MAX_866_7MS; WORST_LOAF_874_7MS_BLOCKING_749_7MS_PARTIAL_ATTRIBUTION
WA35_R36_HIDDEN_TARGET=DASHBOARD_ASSURANCE_ZERO_HEIGHT_IS_PENDING_NORMAL_CSS_HIDDEN
WA35_R37=13_CASES_3_ROUTES_DESKTOP; NORMAL_MAIN_SIDEBAR_START_END_6_OF_6; REDUCED_NO_MAIN_ENTRANCE_6_OF_6; CANCEL_NOT_INSTRUMENTED
WA35_R37_SCROLL=FEATURES_1_TARGET_72_FRAMES_MAX_GAP_17_1MS_OVER50_0_TARGET_NOT_PENDING
WA35_R37_ERRORS_LAYOUT=PAGE_CONSOLE_FAILED_EXTERNAL_CLS=0; OVERFLOW_NOT_INSTRUMENTED
WA35_R37_PERFORMANCE=COLD_LONG_TASK_MAX_563MS_LOAF_MAX_610MS_BLOCKING_517MS_RAF_GAP_MAX_999_9MS; WALLET_REDUCED_TASKS_381_244MS_GAP_466_5MS
WA35_R37_RELOAD=NO_LONG_TASK_GT_200MS_IN_6_ROWS; RAF_GAP_MAX_100MS; CACHE_HIT_UNPROVEN
WA35_R37_HIDDEN_TARGET=DASHBOARD_ASSURANCE_ZERO_GEOMETRY_CSS_HIDDEN_IS_PENDING_NORMAL
WA35_R38C=PARTIAL; ROUTE_TITLE_SHELL_MAIN_PRESENT; DASHBOARD_RENDER_PREDICATE_FALSE_NEGATIVE; ASSURANCE_HIDDEN_ZERO_GEOMETRY_NOT_PENDING_NOT_OBSERVED; OFFSCREEN_TARGET_VISIBLE_CSS_ANIMATION_680MS
WA35_R38C_TRACE=2_INSTRUMENTATION_ERRORS_DOCUMENTELEMENT_UNAVAILABLE; CLASS_HISTORY_ANIMATIONEND_ANIMATIONCANCEL=NOT_CAPTURED; CONSOLE_ERRORS=0; LOCAL_FAILED_RESPONSES=0; FOREIGN_REQUESTS=0; BLOCK_POLICY_ENABLED
WA35_R38D=NO_VALID_JSON; CHROME_CRASHPAD_SELF_TERMINATED; TEMP_INSTALL_BLOCKED_BY_SANDBOX; ESCALATION_REJECTED; FOCUSED_CONTRACT_TESTS=8_PASS; BROWSER_ACCEPTANCE=OPEN
WA35_R39=FOCUSED_STATIC_CONTRACTS_8_PASS_5.87S; NODE_SYNTAX_EXIT_0; TEMP_PIP_UNPACK_DENIED; NO_PACKAGE_INSTALLED
WA35_R40=PLAYWRIGHT_EDGE_TARGETCLOSED_EXIT_13_CRASHPAD_PIPE; NODE_REPL_PLAYWRIGHT_NOT_AVAILABLE; IAB_LOCALHOST_4178_TIMEOUT; NO_VALID_BROWSER_TRACE; NODE_SYNTAX_EXIT_0
WA35_R40_QA_CLEANUP=SESSION_30036_CTRL_C_EXIT_1; PORT_4178_NO_LISTENER
WA35_SOURCE=HEAD_45B84DE83EE9B475BB4366C3DDC2AF85B82297C4_PLUS_DIRTY_OVERLAY; PORTAL_MOTION_SHA256_C70752BAE488EB8D91069173B6F7D9E41F09C73A2F6985526BACF41FB0159326
WA35_CODE_FIX=NONE; BROWSER_ACCEPTANCE=OPEN; NEXT=PROVISION_OR_RESTORE_QA_BROWSER_RUNTIME_THEN_RECAPTURE_TRACE_ON_CURRENT_SHA; DO_NOT_PATCH_WITHOUT_REPRO
WALLET_ADMIN_SPEC=READY_FOR_REBASELINE; CURRENT_UI_STATUS=NEEDS_REVALIDATION
UI_REFERENCE_GATE=PLANNED_BEFORE_SURFACE_DESIGN; NOT_RUN
WA36=PARTIAL_SAMPLE_MATRIX; FULL_SITE_AND_PERFORMANCE_OPEN
BOT_CANONICAL_SHA=NOT_LOCKED
UNKNOWN_COUNT=NOT_MEASURED
PRODUCT_IMPLEMENTATION_IN_THIS_TASK=NO
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
COMMIT=NO
PUSH=NO
MERGE=NO
DEPLOY=NO
LIVE_PASS=NO
NEXT=CONTINUE_WA35_RCA_WITH_VALID_CURRENT_SHA_BROWSER_TRACE; DO_NOT_CLAIM_MOTION_OR_PERFORMANCE_COMPLETE; NO_QA_SERVER_LEFT_RUNNING
```
