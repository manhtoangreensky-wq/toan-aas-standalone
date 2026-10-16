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

## Phạm vi

Chỉ đọc các defect đã có evidence: R216-L auth next-route CTA, R216-H landing mobile
header/PWA placement và R216-P auth install icon. Không biến recheck thành deploy.

## URL và viewport

- `/features` rồi ghi URL redirect `/login?next=/features` ở VI/EN/ZH.
- `/login?lang=vi|en|zh`.
- `/welcome?lang=vi` ở 327×667, 390×844 và 1440×900.
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
