# Landing Motion Clarity — Design

## Goal

Make the public `/welcome` motion visibly continuous and section-specific while preserving the TOAN AAS teal/cyan light/dark design, native scroll behavior, readable content, and a fail-open static mode.

## Design

The existing scroll signal remains the single source of truth. The hero keeps bounded depth/parallax; the studio preview/card surfaces add pointer depth; workflow steps use a horizontal response and progress rail; trust cards use a restrained lift; and the final CTA uses a one-pass light sweep tied to scroll progress. Each effect is limited to compositor-friendly `transform`/`opacity` where it is continuous. Existing border/shadow transitions remain only for short hover feedback.

The replay control is an enhancement, not a required action. It is hidden and disabled when `?motion=0` is selected or the browser reports `prefers-reduced-motion: reduce`, so no visible control is inert. Keyboard focus still reveals content, but focusing replay does not cancel the replay animation itself.

## Boundaries

- Presentation-only: no route, API, provider, payment, wallet, job, storage, or bot changes.
- No scroll hijacking, pinning, infinite animation, or new dependency.
- Existing semantic landing markup and shared teal/cyan theme tokens remain unchanged.

## Verification

- Contract tests cover opt-out control state, focus exception, compositor-only scan keyframes, and section-specific motion markers.
- `node --check` validates both portal scripts.
- Browser smoke checks live `/welcome` at hero, workflow, and final scroll positions, plus light/dark and `?motion=0`.
