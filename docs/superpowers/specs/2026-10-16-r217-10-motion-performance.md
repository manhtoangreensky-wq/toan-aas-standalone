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
