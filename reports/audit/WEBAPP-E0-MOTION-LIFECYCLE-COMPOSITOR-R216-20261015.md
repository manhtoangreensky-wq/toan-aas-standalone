# R216 — Motion lifecycle, compositor và readiness

Ngày: 2026-10-15
Phạm vi: Web App standalone presentation/source contract; không đụng Bot/Core,
engine, provider, ví/Xu, PayOS, dữ liệu production, VPS hoặc deploy.

## Kết quả

- Auth entry không còn bị lần hydrate provider cắt giữa animation: render async
  chỉ thay vùng provider, còn phase `entry` được giữ đến hết hai `requestAnimationFrame`
  và timer 680ms.
- Vùng provider giữ chỗ tối thiểu 86px để Google/Apple xuất hiện muộn không đẩy
  form.
- Scroll-driven layer dùng `transform`/`opacity` compositor; không còn
  `transition: left` hoặc transition transform theo biến scroll scrub.
- Telegram giữ user gesture bằng cách mở `about:blank` trước `await`; deep link
  vẫn fail-closed và popup lỗi được đóng.
- PWA chỉ gọi native prompt khi có `beforeinstallprompt`; nếu chưa sẵn sàng thì
  hiển thị hướng dẫn cài đặt theo thiết bị, không báo cài đặt giả.
- `prefers-reduced-motion` tắt animation/transition trang trí và giữ nội dung
  đọc được.
- Renderer gói nạp không còn inline `transition: all`; các chuyển động thẻ gói
  chỉ dùng thuộc tính visual đã định danh trong stylesheet.
- Thẻ trong template Dashboard cũ chỉ transition `transform` và `border-color`;
  bỏ shorthand `transition:.2s` để thay đổi kích thước/nội dung không bị kéo theo.
- Catalogue auth VI/EN/ZH không còn khai báo trùng khóa `pwaFallback`; regression
  guard mới bắt lỗi duplicate key trước khi bundle được dùng.
- Features hydration async giữ đúng phần tử `portal-main` và route `/features`;
  phản hồi đến muộn bị bỏ qua nếu shell đã được thay bởi route khác, tránh dựng
  lại nội dung cũ vào DOM mới. Dấu `/` cuối được chuẩn hóa nên `/features` và
  `/features/` dùng cùng acceptance.

## Addendum R216-I — stale Features hydration

- **Nguyên nhân:** `hydrateFeatures()` chờ đồng thời `/catalog` và `/auth/me`,
  sau đó trước đây luôn ghi state và gọi `renderShell()` mà không xác nhận phần tử
  đích còn là `portal-main` ban đầu hoặc đường dẫn còn là `/features`.
- **Đã sửa:** `featuresHydrationIsCurrent()` kiểm tra danh tính shell hiện tại và
  pathname trước khi ghi `window.__TOAN_AAS_PORTAL__` hoặc thay DOM. Khi route đã
  rời đi, kết quả async được bỏ qua và không chạm shell mới.
- **Phạm vi:** chỉ `static/portal/portal-features.js` và regression source; không
  đổi route, action, field, API, quyền, dữ liệu hay trạng thái server.
- **Bằng chứng:** `tests/feature-catalog-route-presentation.test.mjs` đạt 6/6;
  focused motion/static/features đạt 26/26; toàn bộ Node đạt 469/469; JS syntax
  4/4; `git diff --check` đạt.

## Follow-up R216-L — locale drift ở nút cài ứng dụng trên trang đăng nhập

- **Phát hiện runtime:** bản đang chạy tại `https://app.toanaas.vn/login` vẫn
  hiển thị `Tải & Cài đặt App TOAN AAS` ở VI, `Install TOAN AAS App` ở EN và
  `安装 TOAN AAS App` ở ZH. AX snapshot và screenshot đã ghi nhận trực tiếp.
- **Nguyên nhân nguồn:** một nhánh `renderAuth()` trong `static/portal/portal.js`
  còn hard-code chuỗi cũ, tách khỏi catalogue locale; đồng thời runtime đang
  phục vụ auth bundle cũ.
- **Đã sửa nguồn:** cả nhánh CTA trong `portal.js` và auth renderer hiện tại
  `portal-auth.js` đều dùng catalogue locale (`installGuide.title`/`text.install`),
  giữ nguyên `data-portal-action="pwa-install-prompt"` và route/action contract.
- **Regression gate:** `tests/auth-pwa-install-control.test.mjs` khóa việc không
  quay lại chuỗi cũ và bắt buộc dùng key `installGuide.title`;
  `tests/auth-locale-copy-purity.test.mjs` khóa catalogue auth không có duplicate
  key.
- **Trạng thái live:** vẫn **OPEN — deployment drift**; runtime chưa nhận source
  patch. Không deploy trong checkpoint này nên không được tuyên bố `LIVE_PASS`.

Runtime read-only evidence: `/login?lang=vi` có title `Đăng nhập · TOAN AAS`,
DOM có skip link đúng `#portal-main`, form không blank và console warning/error
không có; script thực tế là `portal-auth.js?v=local-57e76aa281dcc721fdaa`.
AX tree vẫn trả về nút `📲 Tải & Cài đặt App TOAN AAS`; EN/ZH cũng giữ hậu tố
`App`. Đây là bằng chứng auth bundle live cũ, không phải lỗi còn trong source
hiện tại.

## Revalidation live — Codex In-app Browser, read-only

- VI: AX vẫn trả `📲 Tải & Cài đặt App TOAN AAS`; ảnh chụp cho thấy shell
  navy/xanh ngọc, form và heading hiển thị đầy đủ, không blank.
- EN: AX vẫn trả `📲 Install TOAN AAS App`.
- ZH: AX vẫn trả `📲 安装 TOAN AAS App`.
- Skip link ở cả ba locale vẫn trỏ `#portal-main`; không có thao tác đăng nhập,
  gửi form, tạo job, gọi provider hoặc mutation dữ liệu.
- Kết luận của lần đọc thứ nhất: source patch đã xanh nhưng runtime khi đó còn
  phục vụ bundle cũ; R216-L và `LIVE_PASS` vẫn mở ở thời điểm đó.

## Revalidation live lần 2 — 2026-10-15

Đã đọc lại trực tiếp bằng Codex In-app Browser ở cùng phiên, chỉ đọc, không
đăng nhập, không gửi biểu mẫu và không tạo dữ liệu:

- VI `/login?lang=vi`: tiêu đề `Đăng nhập · TOAN AAS`; skip link `#portal-main`;
  nhãn, trường biểu mẫu, nút đăng nhập và nút Telegram đều là tiếng Việt.
- EN `/login?lang=en`: tiêu đề `Sign in · TOAN AAS`; toàn bộ fixed chrome là
  tiếng Anh; không còn hậu tố `App` trong CTA cài đặt (CTA không xuất hiện khi
  trình duyệt chưa phát tín hiệu cài đặt).
- ZH `/login?lang=zh`: tiêu đề `登录 · TOAN AAS`; toàn bộ fixed chrome là tiếng
  Trung; không còn hậu tố `App` xen trong vùng hiển thị.
- Ảnh chụp VI ở viewport hẹp cho thấy nền navy/xanh ngọc, card form nằm dọc,
  không clipping nội dung và CTA chính có tương phản rõ.

Kết luận của lần kiểm tra thứ hai: auth locale drift không còn quan sát thấy trên
các URL đăng nhập trực tiếp đó. Kết quả này trước đây được ghi là
`LIVE_RECHECK_GREEN`, nhưng không được suy rộng thành nghiệm thu toàn app hoặc
mọi next-route auth. Browser matrix các route, keyboard/focus và CLS/LCP/INP/FPS
vẫn mở; lần recheck thứ ba dưới đây đã mở lại R216-L.

### Recheck live lần 3 — next-route auth còn dùng copy cũ

Lần kiểm tra read-only tiếp theo mở `/features`; runtime chuyển hướng tới
`/login?next=/features`. AX tree của trang đích lại hiển thị nút
`Tải & Cài đặt App TOAN AAS` — chuỗi đã được loại khỏi source locale hiện tại.
Source `portal.js` và `portal-auth.js` vẫn dùng catalogue `installGuide.title` /
`text.install`, và các regression source vẫn khóa hành vi đó. Bằng chứng này
cho thấy lần recheck xanh trước chỉ áp dụng cho các URL `/login?lang=vi|en|zh`,
không chứng minh mọi auth renderer/next-route đã được cập nhật.

- Quan sát: `/features` → `/login?next=/features`; AX còn chuỗi CTA cũ.
- Source: locale catalogue vẫn là nguồn của CTA ở cả hai renderer.
- Kết luận: deployment/bundle drift còn trên next-route auth; không kết luận sai
  rằng source hiện tại vẫn chứa chuỗi cũ.
- An toàn: không đăng nhập, không gửi biểu mẫu, không tạo dữ liệu, không gọi
  provider và không mutation.
- Trạng thái: `R216-L=SOURCE_GREEN_LIVE_DRIFT_OPEN`; `LIVE_PASS=NO`.

### Recheck live lần 4 — Codex In-app Browser, 2026-10-15

- URL đang mở: `https://app.toanaas.vn/login?next=/features`.
- AX snapshot vẫn có nút `📲 Tải & Cài đặt App TOAN AAS`; ảnh chụp cùng phiên
  xác nhận form đăng nhập và nền navy/xanh ngọc đang hiển thị, nhưng CTA còn
  bundle cũ.
- Không đăng nhập, không nhập dữ liệu, không gửi biểu mẫu, không gọi provider
  và không tạo mutation.
- Kết luận: `R216-L` tiếp tục `SOURCE_GREEN_LIVE_DRIFT_OPEN`; cần delivery hợp lệ
  rồi đọc lại đúng next-route này trước khi đóng.

### Recheck live lần 5 — current DOM probe

Đã mở lại `https://app.toanaas.vn/features` bằng Codex In-app Browser, chỉ đọc.
Runtime tiếp tục chuyển tới `/login?next=/features`; `main#portal-main` vẫn có
`tabindex="-1"`, nền thực tế là navy/xanh ngọc (`rgb(6, 32, 38)`) và chữ sáng.
Bundle hiện tại vẫn là `portal-auth.js?v=local-57e76aa281dcc721fdaa`. Probe DOM
thấy chuỗi `📲Tải & Cài đặt App TOAN AAS` còn trong nút cài đặt ẩn
(`visible=false`). Đây tiếp tục là deployment drift; không đăng nhập, không gửi
biểu mẫu, không gọi provider và không mutation.

## R216-H — landing header responsive

Ảnh live read-only ở viewport hẹp đã cho thấy header landing bị ép một hàng:
logo/brand vẫn chiếm chỗ trong khi cụm ngôn ngữ, giao diện và nút hành động bị
cắt ở mép phải. Source đã thêm nhánh `@media (max-width: 420px)` trong
`static/portal/portal.css`: nav chuyển về grid một cột, cụm actions chiếm hàng
riêng, locale links thu nhỏ theo vùng an toàn và không đổi route/action.

Regression gate `Landing mobile header wraps controls instead of clipping the
brand row` đã đạt; browser recheck sau khi source này được giao lên runtime vẫn mở.

### Recheck live viewport hẹp — bundle cũ còn drift

Codex In-app Browser đã đọc landing ở viewport khoảng `327×667`, chỉ đọc, không
đăng nhập, không bấm CTA, không gửi form và không tạo dữ liệu. Ảnh live xác nhận:

- Logo/brand vẫn giữ ở hàng đầu nhưng cụm locale, giao diện và CTA bị cắt ở mép
  phải vì runtime chưa nhận media rule mới.
- Nút cài PWA đang là FAB cố định ở góc trái phía dưới và che một phần dòng
  proof khi nội dung hero dài trên màn hình hẹp.
- Source hiện tại đã có hai chốt đúng phạm vi: media rule `max-width: 420px`
  trong `static/portal/portal.css`, và placement `--landing-inline` trong
  `static/portal/portal-theme.css` để control nằm trong CTA cuối trang.
- Regression `tests/pwa-landing-install-placement.test.mjs` và gate responsive
  đều xanh; vì bundle live còn cũ, R216-H vẫn `LIVE_DRIFT_OPEN`.

## File/contract đã khóa

- `static/portal/portal-auth.js` — auth lifecycle, provider hydration, Telegram
  gesture, PWA readiness.
- `static/portal/portal.js` — auth install CTA locale drift fix (R216-L).
- `static/portal/portal-features.js` — Features motion cleanup for stale observer,
  RAF, timer, focus callbacks và stale async hydration.
- `static/portal/portal-motion.js` — landing reduced-motion lifecycle, pointer RAF
  cleanup và scroll metadata hot-path.
- `static/portal/portal.css` — reservation cho vùng provider và media rule
  responsive cho landing header ≤420px.
- `static/portal/portal-theme.css` — auth entry, compositor sheen, scroll layer,
  reduced-motion fallback.
- `tests/r216-motion-lifecycle-compositor.test.mjs` — 10 regression gates cho
  auth, compositor, reduced-motion, scroll paint và metadata hot-path.
- `tests/feature-catalog-route-presentation.test.mjs` — 6 regression gates cho
  Features route lifecycle cleanup và stale hydration guard.
- `tests/current-main-motion-static-gates.test.mjs` — gate không để inline
  `transition: all` quay lại renderer, shorthand quay lại Dashboard cũ hoặc
  header landing bị clipping trên mobile.
- `tests/pwa-landing-install-placement.test.mjs` — bảo vệ placement PWA inline
  trong CTA cuối landing.
- `templates/dashboard.html` — giới hạn hover transition ở hai thuộc tính thực sự thay đổi.
- `tests/test_auth_reference_login_001_contracts.py` — cập nhật phase contract
  theo lifecycle mới.
- `docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md` —
  spec/evidence ledger.

## Source audit follow-up — lifecycle và hot-path compositor

Audit đọc mã sau checkpoint live đã tìm và khóa bốn điểm source còn thiếu:

1. Features route giữ callback IntersectionObserver/RAF sau khi unmount. Đã thêm
   cờ lifecycle, huỷ cả hai RAF entrance và RAF reveal, huỷ timer, disconnect
   observer và tháo listener `focusin`.
2. Landing không phản ứng khi người dùng bật `prefers-reduced-motion` trong lúc
   đang chạy. Đã thêm listener `MediaQueryList`; khi chuyển sang reduce, landing
   gọi cleanup cho RAF, timer, observer, scroll/pointer listener và lớp trang động.
3. Scroll hot path cập nhật gradient nền theo `--landing-section-progress` ở mỗi
   frame. Đã chuyển phần nhấn nền sang gradient tĩnh trên pseudo-element, chỉ
   thay đổi bằng `opacity`; bỏ biến `--landing-section-offset` không có consumer CSS.
4. Scroll hot path ghi lại hai data attribute ở mọi frame và Portal áp
   `will-change`/`translateZ(0)` lên toàn bộ page/card/table. Đã ghi attribute theo
   điều kiện khi giá trị đổi và gỡ hint compositor blanket; control có motion riêng
   vẫn giữ hint cục bộ.
5. Dark theme còn map ô nhập sang palette obsidian gần đen, lệch khỏi quy cách
   navy/xanh. Đã chuyển bốn token nền/chữ/placeholder/viền sang
   `--portal-dark-input-*`, `--portal-dark-ink` và `--portal-dark-placeholder`.

Regression mới:

- `tests/feature-catalog-route-presentation.test.mjs`: 6/6.
- `tests/r216-motion-lifecycle-compositor.test.mjs`: 10/10.
- `tests/current-main-motion-static-gates.test.mjs`: 10/10, gồm gate palette
  dark navy/xanh.
- Các test mới khóa stale callback sau cleanup, dynamic reduced-motion, scroll
  background paint, metadata writes và blanket compositor hints.

## Bằng chứng terminal

```text
node --test tests/r216-motion-lifecycle-compositor.test.mjs
10 passed, 0 failed

node --test tests/current-main-motion-static-gates.test.mjs
9 passed, 0 failed

node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs
15 passed, 0 failed

node --test tests/**/*.test.mjs
469 passed, 0 failed

node --test tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs tests/feature-catalog-route-presentation.test.mjs
26 passed, 0 failed (latest recheck)

node --test tests/feature-catalog-route-presentation.test.mjs
6 passed, 0 failed

node --test tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs tests/auth-locale-copy-purity.test.mjs tests/auth-pwa-install-control.test.mjs
31 passed, 0 failed (prior focused ledger)

node --check static/portal/portal-auth.js
node --check static/portal/portal-motion.js
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
node --check static/portal/offline.js
PASS (5/5)

git diff --check
PASS

py_compile (17 touched Python contract files)
PASS
```

`pytest` chưa chạy được: Python bundled trong workspace không có module
`pytest`; không cài dependency trong checkpoint này.

## Acceptance ledger

| Spec | Kết quả source | Runtime |
|---|---|---|
| R216-A auth lifecycle | GREEN — focused 2/2, full Node 469/469 | Chưa có browser QA |
| R216-B provider stability | GREEN — focused 1/1, `min-height: 86px` | Chưa đo CLS thật |
| R216-C compositor/scroll | GREEN — focused 2/2 + new hot-path gates, full Node 469/469 | Chưa đo FPS/INP thật |
| R216-D Telegram gesture | GREEN — regression hiện có | Chưa thao tác browser |
| R216-E PWA readiness | GREEN — regression hiện có | Chưa thao tác browser |
| R216-F reduced-motion | GREEN — focused 1/1, full Node 469/469 | Chưa đo CLS/LCP/INP thật |
| R216-G browser acceptance | OPEN | QA fixture server có thể dựng; Chrome sandbox đóng với `exitCode=13` trước khi tạo phiên |
| R216-L locale drift CTA đăng nhập | GREEN — source regression + duplicate-key guard; full Node 469/469 | OPEN — `/features` → `/login?next=/features` AX còn `Tải & Cài đặt App TOAN AAS`; bundle/route drift |
| R216-H landing header responsive | GREEN — static gate + source media rule; PWA inline placement regression xanh | OPEN — live read-only 327×667 còn clipping header và FAB cũ che proof vì deployment drift |
| R216-I Features hydration lifecycle | GREEN — async response chỉ render khi đúng `portal-main` và `/features` hoặc `/features/` sau chuẩn hóa dấu `/` cuối; regression 6/6 | Chưa có browser QA runtime |
| R216-P auth install icon structure | GREEN — shared SVG `portal-icon`, wrapper ổn định 18px, không emoji; focused auth/PWA + motion 32/32 và full Node 469/469 | Runtime visual acceptance mở cùng R216-G/H/L/P |

## Chưa được tuyên bố

Chưa có DOM snapshot, screenshot, computed style, console/network trace,
keyboard/focus interaction, FPS/LCP/INP/CLS measurement trên runtime QA cô lập;
vì vậy `LIVE_PASS=NO`. Source green không đồng nghĩa deployed/live.

```ini
TASK=R216-motion-lifecycle-compositor
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=LOCAL_BRANCH_HEAD (verify with `git rev-parse HEAD`)
FILES_CHANGED=static/portal/portal-auth.js; static/portal/portal.css; static/portal/portal-theme.css; static/portal/portal.js; static/portal/portal-motion.js; static/portal/portal-features.js; templates/dashboard.html; tests/auth-pwa-install-control.test.mjs; tests/current-main-motion-static-gates.test.mjs; tests/r216-motion-lifecycle-compositor.test.mjs; tests/feature-catalog-route-presentation.test.mjs; tests/test_auth_reference_login_001_contracts.py; docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md; reports/audit/WEBAPP-E0-MOTION-LIFECYCLE-COMPOSITOR-R216-20261015.md; reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-20261010.md; .agents/state/WEBAPP-UIUX-PLAN-20261010.yaml
TESTS=focused auth/PWA + motion 32/32; latest motion/static/palette/features 26/26; Features lifecycle 6/6; full Node 469/469; JS syntax 4/4 latest recheck; py_compile 17/17 prior gate; diff-check PASS
BASELINE_FAILURES=0
BRANCH_FAILURES=0
NEW_FAILURES=0
PROTECTED_COMPARATORS=routes/actions/fields/capabilities/csrf/idempotency/revisions/dynamic_server_data
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=NOT_AVAILABLE
LIVE_PASS=NO
BLOCKERS=live runtime still serves pre-patch bundle for R216-H; isolated QA runtime metrics unavailable because Chrome sandbox exits 13 before session; Antigravity PHIEU-217 cannot run because agy.exe is not available; pytest module unavailable in bundled Python
COMMIT=YES (local checkpoint commit; exact HEAD is read from git)
PUSH=YES (branch `webapp-checklist-r116`; remote ref verified)
PR=OPEN #647
PR_URL=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/647
MERGE=NO
```

## Delegation and QA recheck — 2026-10-15

- Đã chuẩn bị phiếu Antigravity `PHIEU-217` cho đúng một phạm vi: rà soát
  `templates/dashboard.html` và regression gate tương ứng. Phiếu cấm trình duyệt,
  mạng, git, package và mọi file ngoài phạm vi.
- Lần giao lại qua `chay-phieu-agy.ps1` trả `NOT_RUN`: `LOI: khong tim thay
  agy.exe. Dat bien AGY_EXE tro toi agy.exe.`; không có báo cáo của thợ nên
  không ghi nhận PASS từ Antigravity.
- QA fixture đã dựng được server và đọc source, nhưng Playwright bundled thiếu
  Chromium; khi chuyển sang Chrome hệ thống, Chrome thoát `exitCode=13` trước khi
  mở phiên remote debugging. Vì vậy chưa có DOM/screenshot/CLS/LCP/INP runtime.
- Delivery GitHub đã thực hiện ngày 2026-10-16: sau khi fetch `main=3df20c7`,
  branch local được rebase không conflict và push thành công lên
  `webapp-checklist-r116`. Theo xác nhận action-time của Owner, PR WebApp
  UI/UX–motion đã được tạo một lần qua GitHub Web: **PR #647**, trạng thái Open,
  Able to merge; CI `Web App quality gate / Verify Web App` đang chạy. Không
  merge/deploy; `gh auth status` vẫn báo CLI token không hợp lệ nên không dùng
  CLI cho thao tác PR. Không dùng chuỗi xác thực người dùng đã dán.

## Source follow-up — R216-P — auth install icon structure (2026-10-16)

- `static/portal/portal-auth.js` không còn dùng emoji làm icon cấu trúc cho CTA
  cài PWA. CTA dùng `portal-auth-install-icon` chứa SVG `portal-icon`, giữ kích
  thước khung 18px để không gây layout shift khi font hoặc locale thay đổi.
- `static/portal/portal.css` giới hạn hộp icon và SVG ở 18/17px; không đổi màu
  navy/xanh, route, hành vi cài đặt, API, provider hay wallet.
- `tests/auth-pwa-install-control.test.mjs` khóa không emoji, có wrapper SVG và
  giữ toàn bộ ma trận hướng dẫn cài đặt VI/EN/ZH.
- Kết quả kiểm chứng: focused auth/PWA + motion `32 passed, 0 failed`; toàn bộ
  Node suite `469 passed, 0 failed`; `git diff --check` xanh. Đây là source
  evidence; runtime/live visual confirmation vẫn mở theo R216-G/H/L/P.
