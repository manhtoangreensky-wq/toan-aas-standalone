# AI Studio Explorer — Design

## Goal

Make the customer `/features` directory feel like a focused AI workspace: a
clear control bar, an easy family choice, and a result region that stays honest
when the local search narrows the already-published catalogue.

## Boundaries

- Presentation only. Route manifest, signed-session hydration, capability
  readiness, provider boundaries, jobs, billing and wallet rules remain
  untouched.
- Search is local DOM filtering over server-rendered catalogue entries.
- Family links remain fixed member routes from the closed seven-family
  allowlist; browser input never creates a route.
- Vietnamese, English and Simplified Chinese copy stays in the existing fixed
  i18n catalogue.

## Layout and motion

The directory places search, family exploration and group jumps inside one
token-driven control region above the result groups. Each group advertises its
stable `id` through `aria-controls`; filtering hides both empty result groups
and their stale jump links. A single bounded reveal target animates the control
region with transform/opacity only. Focus immediately reveals a pending target,
and reduced-motion keeps every control and result visible without animation.

Desktop uses a two-level directory/result rhythm. At mobile widths the family
and jump controls wrap instead of requiring horizontal scrolling. All controls
remain at least 44px tall and retain visible focus rings in both Aura themes.

## Verification

The contract test checks closed route authority, local-only filtering,
ARIA semantics, token-only light/dark styles, mobile wrapping and reduced-motion
visibility. Existing feature-family, dashboard-motion and teal foundation
tests remain regression comparators.
