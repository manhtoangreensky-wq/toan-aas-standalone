# R217-10 — Motion lifecycle, compositor và perceived performance

**Status:** `SOURCE_GREEN_RUNTIME_OPEN`
**Wave:** W6 (sau W1–W5 source gate)

## File có thể sửa khi mở

- `static/portal/portal-auth.js`
- `static/portal/portal-motion.js`
- `static/portal/portal-features.js`
- `static/portal/portal.css`
- `static/portal/portal-theme.css`
- `static/portal/portal-first-paint.css`
- motion/performance regression tests.

## Cấm sửa

Không thay route/engine/provider/wallet; không thêm thư viện animation nếu CSS/RAF hiện có
đủ; không animate dữ liệu hoặc đổi copy chỉ để tạo cảm giác nhanh.

## Contract kỹ thuật

1. Auth entry một lần render; async response cũ không ghi DOM đã unmount.
2. Chỉ transform/opacity trong transition/scroll hot path; không `left`, `top`, width/height,
   `transition: all`, blanket `will-change`/`translateZ(0)`.
3. Micro interaction 150–300ms, exit nhanh hơn entry; tối đa 1–2 nhóm motion chính/view.
   Auth/customer observable entrance giữ `680ms` theo R216 và WA-35; landing cinematic
   sequence giữ token riêng `980ms`. Không áp dụng mốc micro 150–300ms cho hai timeline này.
4. Scroll reveal hiện đúng khi section vào viewport, không `opacity:0` tạo vùng trống;
   observer/RAF/timer/listener cleanup khi route rời.
5. Reduced-motion tắt parallax/stagger và phản ứng khi setting đổi trong lúc chạy.
6. Telegram popup giữ user gesture; PWA prompt chờ readiness thật.

## Acceptance

- Static gates xanh; no stale callback; reduced-motion và unmount regression xanh.
- Browser trace không có layout thrash dài; CLS <0.10, LCP ≤2.5s, INP ≤200ms hoặc ghi
  blocker runtime.
- Screenshot trước/sau cho landing/auth/dashboard/product lane không khựng hoặc trắng.

## Verify

```powershell
node --test tests/r216-motion-lifecycle-compositor.test.mjs tests/current-main-motion-static-gates.test.mjs tests/feature-catalog-route-presentation.test.mjs
node --check static/portal/portal-auth.js
node --check static/portal/portal-motion.js
```

## Source closeout — 2026-10-17

- Fixed the remaining timing-contract drift: `--portal-motion-fast` is now `160ms`
  (inside the required `150–300ms` micro-interaction window and still faster than
  the `220ms` route-entry token).
- Added a regression assertion covering the micro window, exit-before-entry order,
  the `680ms` auth entrance and the `980ms` landing hero timeline.
- Updated the three Python motion contracts that still expected the old `140ms`
  token; they now assert the shipped `160ms` value. Python/pytest execution is
  still not available in this environment, so it remains an explicit blocker.
- `HEAD_SHA=2d756b8db62f74cb331065c3b9ec74691f06a8cd` was pushed to
  `github/webapp-checklist-r116` (PR #647 branch).
- Evidence: focused motion/auth/PWA gates `43/43`; full Node suite `523/523`;
  `node --check static/portal/portal-auth.js` PASS; `node --check
  static/portal/portal-motion.js` PASS; `git diff --check` PASS.
- Runtime FPS/CLS/LCP/INP trace, browser AX/scroll evidence and the production
  delivery fingerprint remain open. No provider call, wallet mutation, merge,
  deploy or production-data mutation was performed.

## Provenance gate repair — 2026-10-17

- CI run `39015089989` failed before product tests in `Verify committed migration
  evidence`: committed Web provenance still recorded the prior eligible-source
  fingerprint `4dbdf2…`, while the current 284-file source inventory measured
  `8ee8c9130c1fb121ff73c0d9ad6cd2fa35877f69c67449d7b3ffcaa9de3f424e`.
- Refreshed only `reports/migration/preflight.json` and
  `reports/migration/web_inventory.json` with the static-only audit at
  `fe146c191ffd7abc2d6d4d8a679e3630ccea1a0e`; local `--verify-web-evidence`
  returned `ok: true`. No application/runtime/provider/wallet/production change.
- The next CI run is the acceptance gate for this repair; motion runtime trace and
  live delivery evidence remain open regardless of this provenance repair.
