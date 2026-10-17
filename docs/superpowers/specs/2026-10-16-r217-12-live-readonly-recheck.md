# R217-12 — Live read-only recheck sau delivery hợp lệ

**Status:** `LIVE_DRIFT_OPEN`
**Wave:** W8

## Latest read-only observation 2026-10-16

At `https://app.toanaas.vn/welcome?lang=vi`, viewport `327×668`, production served
`portal.js?v=local-57e76aa281dcc721fdaa` and `portal.css` with the pre-fix behavior:
`.portal-landing-nav-actions` computed as `flex-wrap: nowrap` with a child right edge
around `372px`, and `.portal-pwa-fab-trigger` computed as `display:flex`,
`position:fixed`. `document.documentElement.scrollWidth` remained `327px`, confirming
clipping instead of a visible horizontal scrollbar. The source fix is on the pushed branch
but this runtime has not received it; keep R216-H/R216-P open.

GitHub PR #647 was read in the authenticated web session on 2026-10-16. Its current
status is `Open` and the page explicitly shows `This branch has not been deployed` and
`No deployments`, confirming that the old production fingerprint is a delivery-state
blocker rather than a failed source fix.

### Fresh browser evidence — 2026-10-16 14:52:08 UTC

- URL `https://app.toanaas.vn/welcome?lang=vi`, viewport `327px` wide: `body.scrollWidth=327`,
  `documentElement.clientWidth=327`; no horizontal overflow. The live DOM still exposed
  `.portal-pwa-fab-trigger[data-portal-pwa-fab="true"]` with text `Cài đặt ứng dụng`,
  `display:flex`, `position:fixed`, `44×44px`, at approximately `(12,544)`. This is the old
  PWA FAB behavior and keeps `LIVE-UI-02` open.
- The same page loaded scripts with fingerprint
  `?v=local-57e76aa281dcc721fdaa` for `portal-theme.js`, `portal-i18n.js`,
  `portal-motion.js`, `portal.js` and `integration.js`.
- Direct read-only navigation from `/features?lang=vi` redirected to
  `https://app.toanaas.vn/login?next=/features`. The route matrix readback was:

  | locale | final title | document language | main id | main tabindex |
  | --- | --- | --- | --- | --- |
  | vi | `Đăng nhập · TOAN AAS` | `vi` | `portal-main` | `-1` |
  | en | `Sign in · TOAN AAS` | `en` | `portal-main` | `-1` |
  | zh | `登录 · TOAN AAS` | `zh-CN` | `portal-main` | `-1` |

- On the Vietnamese login DOM the legacy PWA button text `📲Tải & Cài đặt App TOAN AAS`
  still exists in a hidden `.portal-auth-intro` (`display:none`, zero bounding rect), so it
  did not appear in the AX tree. It remains a stale-bundle copy that must be rechecked after
  the pushed source is delivered.
- No form was filled, no login was submitted, no CTA was activated, no file was uploaded and
  no provider/wallet/production mutation occurred.

### Fresh browser evidence — 2026-10-17 11:40:28 UTC

The read-only recheck was repeated against production with the existing in-app browser tab.
No account was entered and no form, CTA, upload, provider, wallet or production mutation was
performed.

- `/welcome?lang=vi` served `TOAN AAS` at the available `1280×720` viewport. The live asset
  fingerprint remained `local-57e76aa281dcc721fdaa` on `portal-theme.js`, `portal-i18n.js`,
  `portal-motion.js`, `portal.js`, `integration.js`; `body.scrollWidth`,
  `documentElement.scrollWidth` and `clientWidth` were all `1280`, and the browser console
  returned no warning/error records. This confirms a stale delivery bundle, not a source-gate
  failure. The earlier `327×668` mobile observation remains authoritative for the unmeasured
  mobile viewport in this tab.
- At the fresh desktop viewport, `.portal-landing-nav-actions` was `display:flex` with
  `flex-wrap:nowrap`; `.portal-pwa-fab-trigger[data-portal-pwa-fab="true"]` was still
  visible (`hidden=false`, `display:flex`, `position:fixed`, `171.95×41.10px`, roughly
  `(863.05,654.90)`) with `data-portal-action="pwa-toggle-banner"`. The source branch's
  inline/readiness-gated placement is therefore not present in production yet; keep
  `LIVE-UI-02` open.
- Direct `/features?lang=vi|en|zh` navigation still finished at
  `/login?next=/features` without a locale query. All three final pages had
  `main#portal-main[tabindex="-1"]`, but the final document language/title fell back to
  Vietnamese (`vi`, `Đăng nhập · TOAN AAS`) for the `en` and `zh` attempts. Keep `R216-L`
  open until the next-route redirect preserves locale.
- Direct `/login?lang=vi|en|zh` preserved the requested locale (`vi`, `en`, `zh-CN`) and
  showed a visible install control in every locale. The stale Vietnamese control was the
  exact legacy text `📲Tải & Cài đặt App TOAN AAS` (`display:inline-flex`, `410.4×44px`,
  roughly `(110.8,566.67)`); English and Chinese showed the translated stale equivalents
  `📲Install TOAN AAS App` and `📲安装 TOAN AAS App`. This is visible in both DOM and the
  rendered screenshot, so `R216-P` remains open until the delivered bundle exposes the
  reviewed icon/locale control.
- A fresh screenshot was captured for `/welcome?lang=vi` and `/login?lang=vi`; both pages
  rendered without a framework error overlay. The screenshot also visually confirms the
  navy/teal brand is still in use, while the old landing FAB and auth install copy remain.

### Fresh viewport-capable browser evidence — 2026-10-17 12:29:53 UTC

The in-app browser viewport capability was used for a read-only measurement at the two sizes
that were previously unavailable. The override was reset after the measurements. No account,
form, CTA, upload, provider, wallet or production mutation was performed; console error and
warning logs were empty for both loads.

- At `390×844`, production still loaded
  `https://app.toanaas.vn/static/portal/portal.js?v=local-57e76aa281dcc721fdaa`.
  `body.scrollWidth=390`, `documentElement.scrollWidth=390`, and `clientWidth=390`, but the
  landing navigation itself clipped (`.portal-landing-nav`: `scrollWidth=356`,
  `clientWidth=343`) while `.portal-landing-nav-actions` remained `display:flex` with
  `flex-wrap:nowrap`. The old `[data-portal-pwa-fab]` stayed `hidden=false`,
  `display:flex`, `position:fixed`, `44×44px`, at approximately `(12,720)`.
- At `1440×900`, the page root remained within the viewport (`body/root/client=1440`) and
  `.portal-landing-nav-actions` remained `display:flex`/`flex-wrap:nowrap`. The old PWA FAB
  stayed `hidden=false`, `display:flex`, `position:fixed`, `171.95×41.10px`, at approximately
  `(1023.05,834.90)`, with the same stale asset fingerprint.

These measurements close the evidence gap for the two viewport sizes but do not close the
defects: the source branch's mobile wrap and readiness-gated inline placement are still not
delivered to production. Keep `LIVE-UI-01`, `LIVE-UI-02`, `R216-H`, `R216-L` and `R216-P`
open until a valid delivery and a post-delivery recheck succeed.

## Post-delivery evidence — 2026-10-17 13:35 UTC

The Owner-authorized WebApp deployment workflow `39036918159` deployed merge SHA
`bc0d089055df7a52c1ee9e3e76a5cbc57beacce4`. The workflow's forward-only guard, tracked-source
backup, `toanaas-web.service`/`nginx.service` checks and `/health` payload validation all passed.
The production asset fingerprint changed from the pre-delivery `local-57e76aa281dcc721fdaa`.

The read-only browser probe then found one remaining defect: all three requests
`/features?lang=vi`, `/features?lang=en` and `/features?lang=zh` still ended at
`/login?next=/features`, so the requested interface locale was discarded before the login shell.
The root cause is the shared unauthenticated redirect in `app.py`: it used `normalized` as the
return target and never copied the reviewed `lang` query. The focused fix on `webapp-live-r117`
allowlists only `vi|en|zh` and appends that value to the encoded return target; other query data
remains discarded. Regression coverage asserts all three locale redirects and preserves the
existing `/dashboard` no-query redirect. No account, form, CTA, upload, provider, wallet or
production-data mutation occurred during this probe.

## Source correction — candidate `0ad78e5` — 2026-10-17

The first source correction preserved `lang` only inside `next`, which was not enough for the
public login shell and was rejected by the browser return-path guard. The focused follow-up now:

- appends the same allowlisted `lang=vi|en|zh` to `/login` while keeping the encoded return target;
- permits exactly one `lang` query on the client return path, while continuing to reject every other
  query, fragment, backslash, external path and auth-loop route;
- covers both password/Telegram auth (`portal-auth.js`) and the shared OAuth/link return helper
  (`integration.js`) without changing route/action/field or session authority.

Evidence on the candidate: focused locale/UX guard `17/17`, full Node suite `525/525`,
`node --check` for both modified JavaScript files, `py_compile` for `app.py` and three Python
contract files, and `git diff --check` all pass. `pytest` is not runnable in this checkout because
the bundled Python runtime has no `pytest` module. The candidate is committed but not deployed;
R217-12 remains `LIVE_DRIFT_OPEN` until CI, delivery and a read-only production recheck prove the
new redirect and the prior PWA/mobile/auth surfaces together.

## Source quality-gate refresh — 2026-10-17

After the final provenance refresh candidate `7942548`, GitHub workflow `39034978224` completed
successfully. `Verify Web App` job `117402852575` and `Authenticated WebApp QA (R217-11)` job
`117403448516` both passed; the authenticated matrix remained `456/456` with no forbidden
provider, wallet or production-data mutation. This confirms the source/QA candidate is green,
but it does not change the live conclusion above: production still serves the older bundle and
must be rechecked only after an authorized delivery.

## Phạm vi

Chỉ đọc các defect đã có evidence: R216-L auth next-route CTA, R216-H landing mobile
header/PWA placement và R216-P auth install icon. Không biến recheck thành deploy.

## URL và viewport

- `/features` rồi ghi URL redirect `/login?next=/features` ở VI/EN/ZH.
- `/login?lang=vi|en|zh`.
- `/welcome?lang=vi` ở 327×667, 390×844 và 1440×900. The current viewport-capable
  read-only run covers 390×844 and 1440×900; 327×668 remains covered by prior evidence.
- Nếu đã có authenticated QA, thêm `/dashboard` và một route product; nếu không ghi blocked.

## Evidence bắt buộc

Asset fingerprint/script version, runtime SHA (nếu hiển thị), DOM selector/value, AX snapshot,
screenshot, computed style, `scrollWidth/clientWidth`, console error/warning, network read
requests và timestamp. So sánh với source SHA đã push.

## Acceptance

- Không còn CTA cũ `App` trong visible/AX auth next-route.
- Header không clipping; PWA CTA không che proof và chỉ hiện khi readiness thật.
- Icon auth có stable 18px SVG wrapper, focus/contrast đúng.
- Chỉ khi tất cả đạt mới đổi item tương ứng sang `CLOSED_WITH_EVIDENCE`; nếu bundle cũ,
  giữ `LIVE_DRIFT_OPEN`.

## Cấm và verify

Không nhập tài khoản, không bấm submit/confirm, không provider/wallet mutation, không deploy.
Lưu evidence theo format của `reports/audit/` và chạy `git diff --check`.
