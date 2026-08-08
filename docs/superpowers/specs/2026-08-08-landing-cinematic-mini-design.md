# Landing Cinematic Mini — Design

## Goal

Make the public `/welcome` landing visibly premium on first load without
turning it into a heavy marketing animation. The reference contributes its
cinematic rhythm—an opening frame, editorial title reveal, layered stage, and
deliberate pacing—while TOAN AAS keeps its teal–sky palette, Inter typography,
real product copy, and semantic HTML preview.

## Approved direction

The user approved an ordered, reviewable Landing-first change. The previous
Motion TEST1 implementation is real but was gated behind `?motion=1`, so a
normal visitor could not see it. This change makes the presentation-only
landing motion available by default on `/welcome`; `?motion=0` remains a
comparison/diagnostic opt-out. It does not change the root route, access,
customer workspace, ERP, Bot, APIs, provider calls, PWA scope, or server data.

## Visual system

- Keep the existing teal–sky semantic tokens. No warm brown/cream palette,
  spa imagery, copied typography, or Lisa Nail & Spa branding.
- Use a light landing as the public first-paint default when the visitor has
  no explicit saved choice. An explicit light or dark choice remains a local
  presentation preference. Signed application routes retain their existing
  system/light/dark controller.
- Replace the ambiguous cycle-only affordance on `/welcome` with a compact,
  labelled two-button Light/Dark switch. It uses the existing theme controller
  and does not store account data or call an API.
- Add a teal–sky "aperture" frame around the existing semantic Workspace
  preview. The frame is an abstract CSS treatment, not a fabricated image or
  activity record.

## Motion language

All motion runs only under `prefers-reduced-motion: no-preference`, uses
opacity/transform/clip-path once, and does not animate layout dimensions.

1. Header: retain the existing 220 ms compact/blur state after 20 px scroll.
2. Hero: copy reveals through a short editorial curtain (600 ms); description,
   actions, proof, and preview follow at 80 ms intervals.
3. Aperture: the hero frame and preview make one shallow 680 ms entrance;
   there is no parallax, looping glow, video, auto-playing media, or large
   zoom.
4. Preview: the existing four prepared-workflow steps enter in sequence only
   after their parent preview is visible.
5. Sections/cards/CTAs: retain TEST1’s one-time intersection reveal and
   160–220 ms interaction feedback.

When reduced motion is requested, all content is immediately visible, the
aperture remains a static decorative frame, and controls retain normal
keyboard/focus behaviour.

The motion helper must load before the Portal mount script. The public route
also has two separate decisions: `/welcome` suppresses the generic page-enter
animation, while `/welcome?motion=0` suppresses the cinematic lifecycle as
well. This makes `motion=0` a genuine no-motion comparison rather than a
different animation.

## Theme behaviour

`portal-theme.js` continues to be presentation-only. When no saved value is
present, `/welcome` resolves to light rather than inheriting a dark operating
system. The Landing’s explicit controls set only `light` or `dark`; the
existing shared cycle on access and signed routes remains unchanged.

## Acceptance criteria

- `/welcome` enables the cinematic lifecycle by default; `/welcome?motion=0`
  keeps the no-motion comparison state.
- The motion helper is available before initial Portal mount, and the static
  aperture classes are applied before reduced motion skips dynamic behaviour.
- Both Light and Dark choices are visible, keyboard-operable, local-only, and
  use the existing controller with no network calls.
- The cinematic frame and hero entrance are limited to `/welcome` and leave
  public copy, routes, and real CTA destinations unchanged.
- Reduced motion, no-JavaScript content visibility, mobile layout, focus
  order, and existing PWA/public-route contracts remain intact.
- No animation library, images, provider/Bot/API/runtime changes, or new ENV
  variables are introduced.
