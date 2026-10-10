# Đặc tả — Motion toàn Web App và vòng đời chuyển trang

- **SPEC_ID:** `MOTION-WEBAPP-SURFACES-FINAL-20261010`
- **PLAN_ID:** `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009`
- **STATUS:** `WA35_RCA_OPEN_R40_BROWSER_ENV_BLOCKED_R39_TEMP_PACKAGE_INSTALL_DENIED`
- **BASELINE ĐÃ ĐỌC:** `origin/main=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` (phải refresh trước khi triển khai).

## 1. Mục tiêu

Chẩn đoán và khép motion của Web App dựa trên hành vi trình duyệt có thể tái
lập; xử lý riêng ba vấn đề khác nhau: vòng đời animation/transition, độ khựng
do long task/frame gap, và cảm giác hiệu ứng không rõ. Không kết luận từ việc
`portal-motion.js` tồn tại, source có keyframe, test DOM giả lập hoặc ảnh tĩnh.

Đặc tả này không cho phép đổi brand xanh–teal, sửa route/engine/API/business
logic, gọi provider tính phí, sửa ví, ghi dữ liệu production hoặc deploy.

## 2. Bằng chứng đầu vào và ranh giới

- WA-35 R11 trên candidate cũ là `PARTIAL_MEASUREMENT_NOT_PASS`: `CLS=0`,
  `pageErrors=0`, nhưng 8/8 normal rows thiếu `animationend`; 4/16 row có long
  task trên 200 ms (cao nhất 311 ms), 10/16 row có frame gap trên 200 ms (cao
  nhất 450 ms). Đây chưa phải kết quả current-main.
- Entrance của `#portal-main` và `.portal-hero` từng có `animationstart` nhưng
  không có `animationend`. Thiếu event chưa phân biệt được animation bị huỷ,
  rule/class bị thay, phần tử bị tháo/remount, route đổi, reduced-motion hay
  lỗi đo; phải thu trace trước khi sửa.
- Nhận định “12 lỗi ViewTransition invalid-state” trong tài liệu Owner gửi chưa
  được tái hiện trên current main. Trạng thái là
  `CLAIM_NOT_REPRODUCED_ON_CURRENT_MAIN`, không phải lỗi đã xác minh.
- Worktree đang có thay đổi UI/motion/test và evidence chưa commit. Giữ nguyên;
  không reset/stash/rebase/checkout mù. QA mặc định chỉ ở localhost/fixture.

## 3. Giai đoạn kế tiếp đang dở — WA-35 entrance lifecycle RCA

### Routes và phép đo

1. Trên QA localhost đúng SHA, mở `/dashboard?lang=vi` và `/features?lang=vi`
   với normal motion, viewport desktop; thu trace trong 5 giây đầu sau mount.
2. Bắt capture-phase `animationstart`, `animationend`, `animationcancel` cho
   `#portal-main` và `.portal-hero`; ghi timestamp, animation name, elapsed time.
3. Mỗi mẫu theo nhịp frame ghi `getAnimations()`, `playState`, `currentTime`,
   timing `endTime`/duration, computed animation name/duration/delay, opacity,
   transform và `isConnected`.
4. Theo dõi class, `data-portal-motion`, presentation phase và child-list
   mutation quanh `#portal-main`/shell để phát hiện thay rule, tháo DOM hoặc
   remount.
5. Lưu URL, `CURRENT_SHA`, reduced-motion preference, page errors, console,
   failed/foreign requests, JSON trace và screenshot; không ghi cookie/session.

### Phân loại bắt buộc trước khi code

| Quan sát | Phân loại cần xác minh | Quy tắc xử lý |
|---|---|---|
| `animationcancel` sau khi bắt đầu | Hủy do route/unmount, rule/style update, hoặc thao tác script | Tìm đúng thay đổi gây hủy và có regression test; không chỉ ép event thành `end`. |
| `getAnimations()` mất animation, không có cancel | CSS animation bị thay/gỡ trước khi event quan sát được hoặc target khác | Kiểm selector/DOM identity và mutation trace; không kết luận browser lỗi khi chưa đủ trace. |
| `isConnected=false` hoặc node identity đổi | Component bị tháo/remount trong entrance | Xác định ai đổi lifecycle; entrance không được phát lại ngoài chủ đích. |
| Animation còn chạy sau 680 ms nhưng không có end | Duration/fill/composition/listener/timing sai hoặc probe đo nhầm | So computed timing và event target; chỉ sửa phần được test tái hiện. |
| Không có animationstart | Reduced motion, CSS chưa áp, entrance chưa gắn hoặc đo quá muộn | Xác minh init script, style readiness và thời điểm mount. |
| `animationend` có nhưng phần tử vẫn opacity/transform sai | Fill mode hoặc class cuối không khôi phục trạng thái hiển thị | Regression test kiểm trạng thái cuối, không chỉ event. |

**Cổng sửa:** cần có trace có thể tái lập + test RED cùng selector/state/SHA.
Sửa ít nhất có thể trong motion layer; không sửa bằng cách suppress console,
nuốt rejection hoặc xóa transition toàn cục để làm xanh kiểm thử.

### Cập nhật RCA R23–R35 — 2026-10-10

- R11 là candidate cũ: 8/8 dòng normal có `animationstart` nhưng không có
  `animationend` khớp. Kết quả đó không phải `current main` và không chứng minh
  animation bị huỷ.
- R23 chạy trên `127.0.0.1:14179` với DB QA cô lập, kiểm tra `/dashboard` và
  `/wallet/topup`. Asset version trong URL là
  `local-8b6e2dea62f4a56a5657`; trace không ghi full `CURRENT_SHA`, vì vậy không
  quy kết kết quả cho một commit đã khóa.
- Trên mỗi route, `#portal-main` có một `animationstart` và một `animationend`,
  không có `animationcancel`; animation vào trang hoàn tất với node còn kết nối,
  opacity `1`, transform `none`. Có một lời gọi `document.startViewTransition`
  mỗi route. Không có page/console error, failed/external request, layout shift
  được ghi nhận hoặc horizontal overflow.
- Probe ghi 16 child-list mutation record ở Dashboard và 12 ở Wallet; đây không
  phải số lần mount. R23 không thu stack cho `TOANAASPortal.mount()` hoặc
  `integration.merge()`, nên chưa biết mutation nào là hydration, render lồng
  hay remount. Không kết luận chúng gây khựng.
- Long task lớn nhất là `99 ms` ở Dashboard và `207 ms` ở Wallet. Chưa có trace
  quy long task này cho animation hoặc caller cụ thể.
- R24 không tạo trace do bind cổng `14179` thất bại (`WinError 10048`); R25
  không có trace artifact. Lần ngắt session `61755` đã được Owner cho phép nhưng
  công cụ trả `Unknown process id`; không có tiến trình khác bị dừng.
- R27/R30/R34/R35 được chạy lại trên QA localhost ở Git HEAD
  `45b84de83ee9b475bb4366c3ddc2af85b82297c4` và working-tree source overlay có
  SHA-256: `portal.js=520978f0f88db73a1b8f8462cbeac7e266561ee5285a7088c2c451e6713b22d6`,
  `integration.js=cfc08d9a3226cc085b895b5f20d672d3cc07a0b83a19102fdf303ace987797c9`,
  `portal-motion.js=8779d4f57a1b560bf817bc07cd2bb01b39885153d49d3cbf4035de590c76c366`,
  `portal-features.js=4e091257625b7f66e25dc8950032f4db6e9a3e1d0973cbc70f7f682d569ed431`.
  Vì có dirty overlay, kết quả không được gán cho `main`, commit hay production.
  QA dùng DB copy và tài khoản mới trong `%TEMP%`, Edge profile tạm, chỉ loopback;
  `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`.
- R27 `/dashboard` hoàn tất một `portal-customer-observable-enter` trên
  `#portal-main`: start/end khớp, elapsed `0.68 s`, không cancel. R30 `/features`
  là surface riêng (`portal-features.js`), với chuỗi
  `hydrateFeatures → renderShell → mountFeatureMotion`; `.portal-hero` cũng
  hoàn tất một entrance `0.68 s`, không cancel. Hai route mẫu không ghi lỗi
  page/console/request, request ngoài localhost, layout shift hay overflow ngang.
- R34/R35 instrument trực tiếp public `window.TOANAASPortal.mount()` và
  `integration.merge()` trên Dashboard. Trong cửa sổ `5.3 s` có 10 mount tổng:
  mount đầu và 9 lần `reason=data-hydration`, khớp 9 merge. Caller stack cho
  thấy nhánh `startInitialHydration → hydrate` và các hydrate con như Projects,
  Admin ERP Navigation, Asset Vault, Workspace Setup và Workspace Drafts. Mỗi
  mount mất `9.7–27.2 ms`, tổng khoảng `146 ms`; 160 mutation records quanh
  vùng quan sát.
- Dù có các lần mount lặp, R35 chỉ ghi một entrance trên `#portal-main`, bắt
  đầu `3169 ms`, kết thúc `3827 ms`, elapsed `0.68 s`, không cancel. Điều này
  chứng minh có hydration-driven render churn, nhưng chưa chứng minh animation
  bị replay hoặc churn là nguyên nhân duy nhất của cảm nhận khựng.
- R35 ghi long task `223`, `198`, `252 ms`, frame gap lớn nhất `700 ms`, không
  có layout shift. Thời lượng từng mount ngắn hơn long task; R31 CPU profile có
  mẫu `(program)` không gắn được với script/function. Chưa quy kết long-task/frame
  gap cho từng mount hoặc CSS motion. R31 cold localhost ghi response chưa nén:
  `portal.js≈4.09 MB`, `integration.js≈2.44 MB`, `portal-i18n.js≈1.22 MB`,
  `portal.css≈0.74 MB`, `portal-theme.css≈0.78 MB`; không dùng số đó đại diện
  production transfer size.
- Raw JSON và ảnh R27/R30/R31/R34/R35 được giữ ngoài repo tại
  `%TEMP%\toanaas-wa35-r26\` (`wa35-lifecycle-r27.json`,
  `wa35-lifecycle-r30-features.json`, `wa35-cpu-profile-r31.json`,
  `wa35-lifecycle-r34-dashboard.json`, `wa35-lifecycle-r35-dashboard.json`).
- Tại thời điểm R35, WA-35 vẫn mở vì chưa có reduced-motion hoặc ma trận route;
  R36 đã bổ sung một ma trận mẫu nhưng chưa đóng các yêu cầu full-site,
  cold/warm, rapid navigation, Back/Forward hoặc attribution đầy đủ.
- Chưa sửa mã sản phẩm. Regression harness hiện có trong
  `tests/test_motion_webapp_lifecycle_001_contracts.py` so sánh baseline
  `896d3761…` (hydration replay) với source hiện tại (hydration settled); kết
  hợp kiểm tra fallback trong `tests/test_wa35_motion_entry_fallback_contracts.py`.
  Chạy lại trên dirty source overlay đã ghi: **7 passed, exit 0**. Harness tạo
  hai lần hydration cùng route; nó không đo long task/frame gap thật hoặc tái
  tạo đủ chín merge của trace R35.
- Vì vậy chưa cần tạo test trùng cho lifecycle transition. Ở thời điểm ghi R36,
  bước tiếp theo là capture attribution cho workload thực trên QA localhost cô
  lập; R37 đã thực hiện một phần và được ghi ở mục kế tiếp. Chỉ sửa sau khi có
  regression RED gắn với đúng nguyên nhân; không gộp tối ưu bundle rộng vào
  nhánh motion.

### R36 — ma trận motion và attribution một phần / 2026-10-10

- Môi trường: Chrome qua Playwright trên `127.0.0.1:14283`, DB/tài khoản QA cô
  lập trong `%TEMP%`, chặn mọi request không phải localhost; Browser plugin
  không có trong phiên nên dùng fallback Playwright đã được Owner cho phép.
  Git HEAD `45b84de83ee9b475bb4366c3ddc2af85b82297c4`, cộng dirty source overlay
  có fingerprint R27–R35 ở trên. Đây không phải current `main`, production hay
  bằng chứng LIVE.
- Ma trận 16/16 lượt: `/features`, `/dashboard`, `/studio`, `/wallet/topup` ×
  desktop `1440x900` / mobile `390x667` × normal / reduced motion. Cả 16 lượt
  render nội dung, không có page/console error, failed request, request ngoài
  localhost, CLS hoặc tràn ngang.
- Normal motion: cả 8/8 lượt ghi đúng một entrance trên hero/main start/end khớp
  thời lượng `0.68s`; reduced motion: 0/8 lượt có entrance hero/main. `/features`
  ghi đủ 12 nhóm reveal ở cả normal và reduced; các mục có diện tích hiển thị
  đã được reveal và không còn `is-pending`.
- Ngoại lệ cần phân loại: ở `/dashboard` normal, `.portal-dashboard-assurance`
  vẫn `is-pending` và có chiều cao 0 sau khi probe scroll qua các target. CSS
  hiện chủ động ẩn vùng assurance kỹ thuật khỏi giao diện khách. Ảnh không cho
  thấy nội dung khách bị che; đây chưa phải bằng chứng về nội dung hiển thị bị
  kẹt, nhưng selector motion đang giữ một node ẩn và cần test/loại trừ có chủ
  đích thay vì bỏ qua lặng lẽ.
- **Hiệu năng FAIL, không được gọi là “đã mượt”:** 11/16 lượt ghi long task
  `>200ms`; cả 16/16 có frame gap `>200ms`. Các điểm cao nhất:

  | Route/cấu hình | Long task lớn nhất | Frame gap lớn nhất |
  |---|---:|---:|
  | Wallet desktop, normal | `761ms` | `866.7ms` |
  | Dashboard desktop, normal | `275ms` | `749.8ms` |
  | Wallet mobile, normal | `541ms` | `716.5ms` |
  | Wallet mobile, reduced | `582ms` | `666.7ms` |

- LoAF tệ nhất trên Wallet desktop/normal dài `874.7ms`, blocking `749.7ms`.
  Trace ghi script entry `integration.js` `273.4ms`, `portal.js` `6.4ms`,
  `portal-motion.js` `20.3ms` (forced style/layout `18.2ms`,
  `sourceCharPosition=5945` ≈ line 138, `Promise.resolve` invoker) và thêm callback
  `integration.js` `35.7ms`. Đây là attribution một phần theo script, chưa gắn
  hết blocking vào hàm/causal chain, không chứng minh motion là nguyên nhân duy
  nhất. Reduced-motion cũng còn task `582ms` và gap `666.7ms`, nên không thể quy
  toàn bộ khựng cho animation.
- Artifact: `C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\outputs\wa35-r36-attributed-20261010\matrix.json` và
  16 ảnh/JSON theo route, viewport, chế độ. Runner tạm đã được xóa sau khi chạy;
  kết quả là
  `FOCUSED_HYDRATED_MOTION_PASS`, exit `0`; phép PASS này chỉ áp dụng cho các
  assertion motion/console/network/layout trong bốn route mẫu, không phải
  performance PASS hoặc full-site acceptance. Regression lifecycle/fallback
  hiện có: `7 passed, exit 0`; không tạo test trùng.
- Mọi thao tác dùng DB QA: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `COMMIT=NO`, `PUSH=NO`, `DEPLOY=NO`,
  `LIVE_PASS=NO`.
- Việc tiếp theo: lần dấu vết long task/LoAF ở cùng fixture và so sánh normal vs
  reduced + cold/warm. Chỉ sửa motion khi có RED tái lập cho phần thuộc
  `portal-motion.js`; nếu blocking chủ yếu thuộc integration/route bundles thì
  ghi rõ owner/phạm vi, không sửa lấn lane khác. Sau đó hoàn thiện route/auth,
  rapid navigation, Back/Forward và scroll-reveal còn thiếu.

### R37 — đo cold-load, reload cùng phiên và một scroll reveal / 2026-10-10

- Môi trường: Chrome/Playwright trên `127.0.0.1:14283`, một tài khoản dùng một
  lần trong DB QA cục bộ cô lập; chỉ cho request loopback. Git HEAD
  `45b84de83ee9b475bb4366c3ddc2af85b82297c4` cùng dirty source overlay có bốn
  fingerprint như mục R27–R35; hash trước/sau bằng nhau (`sourceStable=true`).
  Kết quả chỉ thuộc fixture local này, không đại diện `main`, production hay
  trạng thái LIVE.
- Phạm vi: `/wallet/topup`, `/dashboard`, `/features` ở desktop `1440x900`,
  normal/reduced motion, một lượt điều hướng đầu và một lần `reload()` cùng
  BrowserContext cho mỗi cặp route/chế độ (12 hàng), cộng một phép cuộn/reveal
  trên `/features` (13 case). Không phủ mobile, route auth-chưa-đăng-nhập, điều
  hướng nhanh hoặc Back/Forward.
- Vòng đời entrance: các target main/sidebar trong normal có cặp start/end khớp
  ở `6/6` hàng; reduced không có main entrance ở `6/6`. Runner R37 không ghi
  `animationcancel`; do đó không tuyên bố số lần cancel bằng 0. Không có page
  error, console error, request lỗi, request ngoài localhost hay CLS trong các
  case đã thu. Runner không đo horizontal overflow.
- Một phép scroll-reveal của `/features`: ghi `72` nhịp khung hình, gap tối đa
  `17.1ms`, không có gap `>50ms`; các event reveal trong mẫu có end và target
  được cuộn tới không còn `is-pending`. Đây chỉ là một mẫu của một target/route,
  không chứng nhận toàn bộ trang hay mọi reveal.
- **Hiệu năng cold-load vẫn FAIL.** Các hàng cold có long task tối đa `563ms`,
  LoAF tối đa `610ms` với `517ms` blocking và khoảng khung hình tối đa `999.9ms`.
  Điểm đáng chú ý: Wallet normal `563ms`; Dashboard normal `213ms`; Features
  normal `201ms`; Wallet reduced ghi các task `381ms` và `244ms`, gap tối đa
  `466.5ms`. Điều này cho thấy khựng không biến mất khi tắt motion, nhưng chưa
  đủ để kết luận nguyên nhân duy nhất là bundle hay hydration.
- Attribution của LoAF có entry từ `portal.js` và `integration.js`, nhưng chỉ
  một phần thời lượng được gắn với script/invoker; chưa xác lập quan hệ nhân quả
  với CSS animation. Không dùng kết quả này để sửa route/engine/shared integration
  trong spec motion; chuyển đúng phần việc nếu RCA sau đó chứng minh thuộc lane
  khác.
- Sáu lượt `reload()` cùng phiên không ghi long task `>200ms`; gap khung hình
  tối đa `100ms`. Tuy nhiên `transferSize` của `portal.js` và `integration.js`
  giữ nguyên như lượt đầu, vì thế phép đo không chứng minh cache hit hoặc warm
  cache thật. Không gọi đây là warm-cache PASS.
- Trên `/dashboard` normal, cả cold và reload đều còn một node
  `.portal-dashboard-assurance.portal-dashboard-motion-target.is-pending`; probe
  xác định node không có hình học/không hiển thị vì CSS `display:none`. Đây là
  node kỹ thuật ẩn, không phải nội dung khách nhìn thấy bị che, nhưng vẫn phải
  được loại trừ có chủ đích hoặc xử lý trong observer contract trước khi đóng
  lỗi pending.
- Bằng chứng: `C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\outputs\wa35-r37-measurement-20261010\browser\r37.json`;
  ảnh lượt cold ở cùng thư mục. File JSON xác nhận `providerCalls=0`,
  `walletMutations=0`, `productionDataMutations=0`, `externalOrigins=[]`.
  Browser evidence được ghi đầy đủ, nhưng wrapper dừng server với
  `SERVER_EXIT=-1` và mã thoát `1`; đây không phải runner clean-exit PASS.
- Sau phép đo, xác nhận cổng `14283` không còn lắng nghe, xóa hai thư mục DB QA
  tạm được tạo cho lượt R37 và giữ nguyên JSON/ảnh bằng chứng.
- Kết luận: R37 xác nhận entrance và scroll reveal chạy trong các mẫu đã đo,
  đồng thời tái hiện lỗi khựng ở cold-load, kể cả reduced motion. Chưa có RED
  chứng minh defect thuộc motion layer nên `product code change = none`; WA-35/36
  tiếp tục mở. Bước kế tiếp là lặp trace attribution trên cùng fixture, tách
  phần của `portal.js`/`integration.js` khỏi motion-owned work; đồng thời bổ sung
  instrumentation cancel/overflow và mở rộng route/auth/mobile/rapid navigation/
  Back-Forward. Giữ nguyên toàn bộ worktree dirty; không chạm production,
  provider, ví, dữ liệu production, Git remote hay deploy.

### R38c — rà lại target ẩn và giới hạn của probe / 2026-10-10

- Artifact đọc lại từ Chrome/Playwright 1.63 trên localhost `127.0.0.1:18905`,
  route `/dashboard`, DB và một tài khoản QA cô lập; mọi request ngoài localhost
  được cấu hình chặn. Không ghi nhận request ngoài hoặc lỗi response cục bộ.
  `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, không có production data. Artifact
  không ghi `HEAD_SHA`/source fingerprint, nên không quy kết cho clean SHA, main
  hay production.
- Trang thật có title `Tổng quan · TOAN AAS`, shell `customer` và
  `#portal-main.portal-main`. Vì vậy `dashboard_rendered=false` là predicate sai
  của harness, không phải bằng chứng trang không render.
- `.portal-dashboard-assurance` có `display:none`, kích thước `0×0`, không còn
  `is-pending` và không được theo dõi ở trạng thái cuối. Target cuộn tới chuyển
  sang `is-visible`, với `portal-customer-observable-enter` `0.68s`. Reduced
  motion được nhận diện; desktop `1440px`, mobile `390px` và mobile reduced
  không tràn ngang.
- **Kết quả vẫn PARTIAL:** init script gọi `MutationObserver.observe()` khi
  `document.documentElement` chưa tồn tại. Có hai lỗi instrumentation giống
  nhau; `classHistory`, `animationend` và `animationcancel` không được ghi. Vì
  vậy chưa phân loại được vòng đời animation và không sửa motion sản phẩm.
  Không có console error hoặc response lỗi cục bộ trong artifact.
- Bằng chứng: `%TEMP%\toanaas-wa35-r38-bf30f5f560734ebb911f2f29e0262f2f\browser-r38c-20261010\evidence\r38.json`
  cùng bốn ảnh Dashboard desktop, sau cuộn, mobile và mobile reduced.

### R38d — probe đã sửa nhưng browser runtime không khởi động / 2026-10-10

- Runner tạm đã đổi observer sang `document` để chạy trước khi có
  `document.documentElement`, nhưng không tạo được `r38d.json`; Chrome tự thoát
  trước khi có trace. Log `browser-r38d5-evidence-20261010\chrome.log` ghi
  Crashpad không mở được file metadata rồi tự kết thúc.
- Thử dựng runtime trong TEMP riêng: `venv` thiếu `ensurepip`; cài `--target`
  bị sandbox từ chối ghi thư mục unpack tạm của pip. Yêu cầu chạy escalated đã
  bị auto-review từ chối; không tìm cách vòng qua chốt này. Chưa chạy lại browser
  bằng lệnh khác. Dùng lại gói pytest đã có trong TEMP trước đó để chạy hai bộ
  contract tĩnh: `tests/test_wa35_motion_entry_fallback_contracts.py` và
  `tests/test_motion_webapp_dashboard_stability_001_contracts.py` — **8 passed,
  exit 0**. Đây không phải browser acceptance.
- `node --check static/portal/portal-motion.js`: exit `0`. Không thay đổi mã sản
  phẩm. R38d vẫn là blocker môi trường, không phải kết quả PASS/FAIL của motion
  trên ứng dụng.
- Trạng thái an toàn lượt này: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`,
  `PRODUCTION_DATA_MUTATIONS=0`, `COMMIT=NO`, `PUSH=NO`, `DEPLOY=NO`.

### R39 — quyền TEMP được cấp nhưng pip bị remap sandbox / 2026-10-10

- Owner cho phép tạo runtime QA tạm trong `%TEMP%`; quyền ghi thư mục con và
  mạng đã được cấp theo đúng phạm vi. Python tích hợp thiếu FastAPI/Uvicorn.
- Hai lần cài các phụ thuộc server vào thư mục TEMP riêng đều dừng trước khi cài
  package: pip báo `Permission denied` khi ghi `pip-unpack-...`. Lần hai đã đặt
  `TEMP`/`TMP` về thư mục được cấp nhưng tiến trình Python vẫn nhận một thư mục
  AppContainer `%TEMP%` khác theo từng lần chạy. Không có package server nào được
  cài; không có server hoặc browser trace R39.
- Đây là blocker quyền ghi thư mục tạm của tiến trình, không phải lỗi sản phẩm.
  Không thử nâng quyền, cài thủ công/bypass sandbox hay chạy lại pip theo đường
  khác. Chưa sửa mã sản phẩm; không có provider, ví, dữ liệu production hoặc deploy.
- Đối chiếu mã nguồn phát hiện `static/portal/portal-motion.js` hiện có SHA256
  `C70752BAE488EB8D91069173B6F7D9E41F09C73A2F6985526BACF41FB0159326`, khác SHA
  đã lưu cho overlay trước là `8779D4F57A1B560BF817BC07CD2BB01B39885153D49D3CBF4035DE590C76C366`.
  File đã bẩn từ đầu lượt; tôi không sửa file này. Thời điểm/nguồn thay đổi chưa
  được xác định. Diff hiện tại có 40 thêm/15 xóa, gồm đổi clear delay khách hàng
  `760 → 1200 ms` và thay đổi phân loại target IntersectionObserver; vì vậy không
  dùng R38 hoặc trace cũ làm bằng chứng cho overlay hiện tại. Phải rebaseline SHA
  hiện tại trước mọi probe mới.

- **Kết luận:** WA-35/WA-36 tiếp tục mở. Không có trace vòng đời hợp lệ mới và
  chưa có regression RED thuộc `portal-motion.js`; bước kế tiếp là chạy probe
  đã sửa sau khi runtime QA browser-enabled có sẵn và SHA overlay được khóa lại,
  rồi chỉ sửa nếu cùng selector/state/SHA tái hiện lỗi. Không chuyển sang sản
  phẩm khác để né blocker.

## 4. RCA hiệu năng — tách khỏi vòng đời transition

- Long task >200 ms và frame gap >200 ms phải được gắn với timestamp, route,
  event/animation đang diễn ra và nguồn blocking nếu trace hỗ trợ.
- So sánh normal motion với reduced motion và route/control không có animation.
- Không quy tất cả frame gap cho CSS motion: ghi riêng main-thread task, browser
  scheduling/background throttling, test-runner contention hoặc nguyên nhân chưa rõ.
- Chỉ sửa motion nếu có bằng chứng liên hệ; không đưa tối ưu hoá JS/engine không
  liên quan vào spec này.

## 5. Kịch bản nghiệm thu cuối

Thực hiện trên một `CURRENT_MAIN_SHA` cố định và ghi lại environment/viewport:

| Kịch bản | Cấu hình tối thiểu | Điều phải xác nhận |
|---|---|---|
| Lần tải đầu | `/dashboard`, cold và warm, anonymous/authenticated phù hợp | Shell hiển thị; entrance nếu được phép chỉ chạy một lần; không có nội dung kẹt ẩn. |
| Chuyển route thường | route đã đăng nhập → route đã đăng nhập | Không chồng transition; focus/scroll không bị giật hoặc mất ngoài hợp đồng. |
| Chuyển nhanh liên tiếp | ít nhất 3 route nhanh trong một nhịp thao tác | Không có invalid state, stale node, unhandled rejection hoặc transition treo. |
| Back/Forward | history navigation 3 bước | URL, nội dung, focus/scroll và motion đồng bộ; không replay hydration entrance. |
| Auth transition | login → signed route; signed → signed | Không flash/nháy locale, nội dung protected không lộ trước auth. |
| Route/render failure | route bị từ chối hoặc response lỗi trong fixture | Error state dùng được; transition đóng/hủy có kiểm soát; không báo success. |
| Hydration/remount | cold load và mount lại nếu test harness hỗ trợ | Entrance không chạy lặp ngoài chủ đích; node lifecycle ghi nhận được. |
| Scroll reveal | `/features` và trang có section dưới fold | Mỗi section hiện một lần khi vào vùng; không hijack scroll; giảm chuyển động vẫn thấy nội dung. |
| Reduced motion | `prefers-reduced-motion: reduce` | Không có animation gây cản trở; opacity 1/transform none; toàn bộ nội dung hiện; điều hướng hoạt động. |
| Viewport | 1440×900, 768×1024, 390×844, 360px width | Không overflow/crop/layout jump do motion; nút vẫn thao tác được. |

### Điều kiện WA-35 (normal motion)

- Không có uncaught ViewTransition invalid-state, uncaught runtime error hoặc
  unhandled rejection.
- Không có failed request hoặc request ra ngoài QA/localhost.
- Không có overflow ngang, `CLS` vượt ngưỡng dự án, hydration replay hoặc nội dung
  còn ẩn sau khi entrance/reveal kết thúc.
- Entrance được kỳ vọng phải quan sát được ở route/state được chỉ định; nếu bắt
  đầu thì phải kết thúc hoặc có cancel với nguyên nhân hợp lệ đã ghi. Không được
  coi thiếu `animationend` là pass.
- Giữ `680ms`, `20px`, opacity `0.12 → 1` làm comparator lịch sử WA-35 nếu đó là
  contract đang chốt; nếu current main khác, ghi phép đo thực tế và xin duyệt
  đổi contract, không tự nới ngưỡng.
- Scroll reveal chạy đúng một lần và không tạo layout shift ngoài ngưỡng.

### Điều kiện WA-36 (reduced motion)

- `animation-name=none` (hoặc không có animation đang chạy), `opacity=1`,
  `transform=none` cho nội dung cần hiển thị; section ẩn chờ reveal = 0.
- Không có lỗi điều hướng/runtime; mọi primary/secondary control vẫn dùng được.
- Không bỏ qua nội dung/state chỉ vì animation đã bị tắt.

## 6. Bộ bằng chứng và trạng thái

Mỗi lần chạy lưu dưới thư mục evidence riêng theo SHA, với `summary.md`,
`trace.json`, console/network JSON và ảnh đại diện. Không chứa credential,
cookie, PII hoặc dữ liệu production.

Báo cáo tối thiểu:

```ini
SPEC_ID=MOTION-WEBAPP-SURFACES-FINAL-20261010
BASE_SHA=
HEAD_SHA=
ROUTES_AND_VIEWPORTS=
NORMAL_MOTION=
REDUCED_MOTION=
ANIMATION_START_END_CANCEL=
UNCAUGHT_VIEWTRANSITION_ERRORS=
RUNTIME_ERRORS=
UNHANDLED_REJECTIONS=
FAILED_REQUESTS=
FOREIGN_REQUESTS=
OVERFLOW=
CLS=
LONG_TASKS=
FRAME_GAPS=
BASELINE_FAILURES=
BRANCH_FAILURES=
NEW_FAILURES=
PROTECTED_COMPARATORS=
EVIDENCE_PATHS=
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NO
```

`WA-35 PASS`/`WA-36 PASS` chỉ áp dụng cho SHA, routes, viewports và cấu hình đã
chạy. `WHOLE_SITE_MOTION_PASS` chỉ được ghi khi toàn bộ ma trận cuối trên current
main và tester độc lập đạt. Merge, deploy, HTTP 200, screenshot đẹp hoặc kết quả
R11 trên candidate cũ không thay thế các cổng này.

## 7. File và phạm vi

- Candidate code allowlist sau RCA: `static/portal/portal-motion.js`; chỉ mở
  `static/portal/portal.css`, `static/portal/portal-theme.css` hoặc
  `templates/portal_shell.html` nếu trace chứng minh đúng file đó là nguyên nhân.
- Test/evidence được thêm chỉ cho kịch bản vừa chứng minh lỗi; giữ nguyên test
  hiện có và chạy comparator bảo vệ shell, locale, reduced motion và scroll.
- Cấm trong spec này: sửa route, API, engine, provider, quote, wallet, auth policy,
  dữ liệu người dùng, Admin workflow, feature semantics hoặc deploy.

## 8. Thứ tự và điểm dừng

1. Tiếp tục RCA WA-35 entrance đang dở; không mở sản phẩm mới.
2. Có trace → test RED → sửa nguyên nhân → chạy WA-35/36 và comparators.
3. Nếu môi trường QA/browser không khởi chạy, sửa đúng điều kiện môi trường an
   toàn hoặc ghi blocker có bằng chứng; không đoán từ lần chạy cũ.
4. Chỉ sau khi các bề mặt sản phẩm và shared shell đóng theo plan mới chạy chứng
   nhận whole-site motion cuối.

## 9. Cập nhật QA R40 — 2026-10-10

- Giữ nguyên `HEAD=45b84de83ee9b475bb4366c3ddc2af85b82297c4` và dirty overlay có
  sẵn; SHA256 hiện tại của `static/portal/portal-motion.js` là
  `C70752BAE488EB8D91069173B6F7D9E41F09C73A2F6985526BACF41FB0159326`.
- Lần thử Playwright với Edge cài sẵn kết thúc bằng `TargetClosedError`,
  `exitCode=13` và lỗi Crashpad/remote-debugging pipe; không có trace/ảnh hợp lệ.
- Runtime Node REPL hiện có không phân giải được `playwright`/`playwright-core`
  qua CommonJS; dynamic import cũng lỗi export `default`. Không có Playwright
  dùng được sẵn để chuyển sang chạy test.
- Codex In-app Browser mở URL QA `http://127.0.0.1:4178/portal-motion.js` nhưng
  trả `net::ERR_CONNECTION_TIMED_OUT`; đây không phải bằng chứng về hành vi UI.
- Session QA `30036` được ngắt bằng Ctrl-C; lệnh kết thúc với exit 1 và cổng
  `4178` được xác nhận không còn listener. Không còn server QA chạy.
- R39 đã ghi nhận cài gói tạm bị Windows sandbox từ chối khi bung gói; không có
  package nào được cài. Lượt này không lặp lại cài đặt hoặc đổi sandbox.
- `node --check static/portal/portal-motion.js` hiện chạy exit 0; đây chỉ là
  kiểm tra cú pháp JavaScript, không xác nhận animation trong trình duyệt.
- Không sửa mã sản phẩm. `WA-35`/`WA-36` vẫn `OPEN`; không kế thừa trace R38
  vì source SHA hiện tại khác SHA đã ghi lúc đó. Cần một runtime QA/browser đã
  được provision hợp lệ để tạo trace mới trước khi quyết định có lỗi motion cần
  sửa hay không.
