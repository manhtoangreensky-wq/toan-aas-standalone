# TOAN AAS `/welcome` scroll motion contract

This document records the bounded motion extension requested for the public
Web companion. It is presentation-only and does not change the Web App's
authority, account, provider, payment, Bot, job or delivery boundaries.

## Interaction grammar

- A sticky header becomes compact after the first scroll threshold.
- The hero preview has a small scroll-tied depth shift; the copy remains
  readable and in normal document flow.
- Each semantic section receives a viewport-progress value. Studios use a
  stagger/reveal and pointer tilt, Workflow draws its vertical progress rail,
  Trust uses a restrained depth lift, and the final CTA receives a single
  scroll-linked light sweep.
- Pointer effects are limited to the preview, studio surfaces and supporting
  workflow/trust controls. They use CSS variables and compositor-safe
  transforms; no layout dimensions are animated.
- One `requestAnimationFrame` loop batches scroll reads/writes. Route unmount
  removes the scroll, pointer and observer listeners and clears all variables.

## Safety and accessibility

- `prefers-reduced-motion: reduce` and `?motion=0` keep every content item
  visible without the scroll loop, parallax or pointer setup.
- No scroll-jacking, full-page pinning, ambient video, infinite animation,
  API request, browser persistence or fabricated product state is introduced.
- The interaction grammar is inspired by the reference site's use of sticky
  chrome, masked transitions, depth layers and section reveals. Its imagery,
  typography, palette and brand identity are not copied.
- Content remains semantic HTML and every CTA remains a real route.

## Verification evidence

The focused contract suite is
`tests/test_landing_scroll_motion_contracts.py`, alongside the existing
Cinematic Mini lifecycle contracts. Production verification must check:

1. `/welcome` renders with no console errors in light and dark modes.
2. Scrolling updates `data-landing-scroll-progress`, the compact header and
   each section's visible effect.
3. Hovering the preview/studio surfaces changes only their pointer state and
   returns to neutral on pointer leave.
4. `?motion=0` and reduced-motion render the same content without hidden
   controls or motion scheduling.
