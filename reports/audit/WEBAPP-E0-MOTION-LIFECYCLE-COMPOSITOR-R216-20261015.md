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
- `static/portal/portal.css` — reservation cho vùng provider và media rule
  responsive cho landing header ≤420px.
- `static/portal/portal-theme.css` — auth entry, compositor sheen, scroll layer,
  reduced-motion fallback.
- `tests/r216-motion-lifecycle-compositor.test.mjs` — 6 regression gates.
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

## Bằng chứng terminal

```text
node --test tests/r216-motion-lifecycle-compositor.test.mjs
6 passed, 0 failed

node --test tests/current-main-motion-static-gates.test.mjs
9 passed, 0 failed

node --test tests/auth-telegram-popup-order.test.mjs tests/auth-pwa-install-control.test.mjs
15 passed, 0 failed

node --test tests/**/*.test.mjs
461 passed, 0 failed

node --test tests/current-main-motion-static-gates.test.mjs tests/r216-motion-lifecycle-compositor.test.mjs
15 passed, 0 failed (latest recheck)

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
| R216-A auth lifecycle | GREEN — focused 2/2 | Chưa có browser QA |
| R216-B provider stability | GREEN — focused 1/1, `min-height: 86px` | Chưa đo CLS thật |
| R216-C compositor/scroll | GREEN — focused 2/2 | Chưa đo FPS/INP thật |
| R216-D Telegram gesture | GREEN — regression hiện có | Chưa thao tác browser |
| R216-E PWA readiness | GREEN — regression hiện có | Chưa thao tác browser |
| R216-F reduced-motion | GREEN — focused 1/1, full Node 461/461 | Chưa đo CLS/LCP/INP thật |
| R216-G browser acceptance | OPEN | QA fixture server có thể dựng; Chrome sandbox đóng với `exitCode=13` trước khi tạo phiên |
| R216-L locale drift CTA đăng nhập | GREEN — source regression + duplicate-key guard; full Node 461/461 | OPEN — `/features` → `/login?next=/features` AX còn `Tải & Cài đặt App TOAN AAS`; bundle/route drift |
| R216-H landing header responsive | GREEN — static gate + source media rule; PWA inline placement regression xanh | OPEN — live read-only 327×667 còn clipping header và FAB cũ che proof vì deployment drift |

## Chưa được tuyên bố

Chưa có DOM snapshot, screenshot, computed style, console/network trace,
keyboard/focus interaction, FPS/LCP/INP/CLS measurement trên runtime QA cô lập;
vì vậy `LIVE_PASS=NO`. Source green không đồng nghĩa deployed/live.

```ini
TASK=R216-motion-lifecycle-compositor
BASE_SHA=44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
HEAD_SHA=LOCAL_BRANCH_HEAD (verify with `git rev-parse HEAD`)
FILES_CHANGED=static/portal/portal-auth.js; static/portal/portal.css; static/portal/portal-theme.css; static/portal/portal.js; templates/dashboard.html; tests/auth-pwa-install-control.test.mjs; tests/current-main-motion-static-gates.test.mjs; tests/r216-motion-lifecycle-compositor.test.mjs; tests/test_auth_reference_login_001_contracts.py; docs/superpowers/specs/2026-10-15-motion-lifecycle-compositor-r216.md; checklist/state
TESTS=latest motion-focused 15/15; prior combined motion/auth/locale/PWA focused 31/31; full Node 461/461; JS syntax 3/3 latest recheck; py_compile 17/17 prior gate; diff-check PASS
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
PUSH=NO
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
- Delivery GitHub chưa thực hiện: `origin` hiện là bundle local
  `C:\Users\toann\Documents\Codex\toanaas-origin-main-r116.bundle`; lệnh
  `git push --dry-run origin webapp-checklist-r116` trả exit `1`, và
  `gh auth status` báo token GitHub không hợp lệ. Không đổi remote, không dùng
  mã xác thực nhạy cảm và không tuyên bố đã push.
