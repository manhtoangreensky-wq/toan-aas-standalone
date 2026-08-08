# Landing Cinematic Mini — Fidelity Ledger

## Review target

- Route: `/welcome`
- Reference: supplied Lisa Nail & Spa hero screenshot
- Intent adopted: cinematic opening rhythm, a curved/aperture layer and staged
  reveal.
- Intent deliberately not adopted: spa photography, brown/cream palette,
  serif branding, copied text, or service-domain styling.

## Local visual verification

Local FastAPI preview was opened through the Browser client at 1280 px wide.
The captures were checked visually against the supplied reference:

| Comparison point | Reference cue | TOAN AAS implementation | Result |
| --- | --- | --- | --- |
| Opening rhythm | Large title appears through a cinematic frame | H1 uses a one-time 620 ms curtain, then the factual copy/actions/preview stage in sequence | Kept, adapted |
| Aperture | Large arched layer establishes depth | Teal–sky abstract aperture sits behind the semantic Workspace preview | Kept, brand-safe |
| Color | Warm editorial photo treatment | Existing teal–sky light surface and slate dark surface remain unchanged | Intentionally different |
| Product surface | Photo is the focal artifact | Real HTML Workspace preview stays readable and cannot imply a completed job | Intentionally different |
| Theme | Single dark editorial look | Explicit Sáng/Tối control is visible, keyboard semantics use pressed state, and both screenshots remain high-contrast | Added for product usability |
| Motion safety | Decorative reveal | One-time transform/opacity/clip-path only; no loop, scroll timeline, media or new library | Kept constrained |

## Interaction evidence

- Fresh `/welcome` preview rendered Light when no theme preference was present.
- Clicking **Tối** set `data-portal-theme="dark"` and the Dark control to
  `aria-pressed="true"`; switching back to **Sáng** did the inverse.
- `/welcome?motion=0` left no cinematic lifecycle attribute, no cinematic
  class, and no heading animation.
- Default `/welcome` mounted `data-landing-motion="cinematic-mini"`; the H1
  computed animation was `portal-landing-cinematic-curtain`.
- Scrolling revealed the first studio section through the existing
  IntersectionObserver lifecycle. Browser console output was empty.

## Accessibility and responsive boundaries

- The two theme buttons use a real `role="group"`, 44 px minimum touch targets,
  clear active state and the existing high-contrast focus treatment.
- `prefers-reduced-motion` is covered by a Node-backed contract: it still adds
  the static aperture/preview classes but schedules no animation lifecycle.
- At a live 375 px viewport, both Light and Dark renders had `scrollWidth ==
  innerWidth == 375`; the two theme controls measured 44 × 44 px. The compact
  header, hero frame and preview remained visible without horizontal overflow.
- The existing `max-width: 600px` rules keep the frame inside the hero, hide
  the workflow connector and preserve the compact navigation pattern.

## Intentional deviations

The result is not a visual clone. It keeps the reference's feeling of an
editorial opening while using the TOAN AAS design system, semantic Workspace
preview and product-safe copy.
