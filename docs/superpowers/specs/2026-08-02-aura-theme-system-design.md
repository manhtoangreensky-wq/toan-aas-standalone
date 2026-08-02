# Aura theme system - design specification

## Goal

Add a professional light/dark presentation layer to the existing TOAN AAS
Portal without changing routes, business state, authority boundaries, or
provider/payment behavior. The existing teal-sky palette remains the brand
source of truth; Aura contributes semantic surface, elevation, and theme
switching rules inspired by the supplied Aura UI showcase.

## Scope and invariants

- Applies to the shared Portal shell, customer workspace, ERP, auth and public
  landing surfaces.
- Light mode keeps the current cyan canvas, white working surfaces and deep
  teal navigation rail.
- Dark mode uses slate navy `#0B132B` canvas and `#1C2541` working surfaces;
  teal/cyan accents are softened neon highlights, never a new brand palette.
- Theme choice is presentation-only. It is stored locally, never sent to the
  bridge, bot, wallet, PayOS, provider or job APIs, and cannot grant access.
- Default is `system`; explicit light/dark choices persist in local storage.
- Every switch is keyboard accessible, has a 44px target, announces its
  current and next mode, cycles deterministically through
  `system → light → dark → system`, and honors `prefers-reduced-motion`.

## Component and token design

`portal-theme.css` owns semantic tokens for canvas, surface, elevated surface,
text, muted text, border, focus, action, accent, status and shadows. A
`[data-portal-theme="dark"]` override maps only those tokens and a small set of
legacy hard-coded surfaces. Existing component classes continue to consume
semantic variables, so route-specific markup does not fork between themes.

The dark primitive values remain in the canonical `:root` token owner; the
dark selector remaps aliases only. This retains the repository-wide rule that
route and component rules never introduce raw colour literals.

`renderHeader` exposes one sun/moon control with a text label that remains
visible at desktop and compact on mobile. `portal-theme.js` runs before the
shell becomes interactive, resolves system preference without a flash, stores
only the bounded value `light|dark|system`, and delegates clicks through the
document so hydration remounts keep working.

## Motion and accessibility

Theme changes cross-fade color/background/border tokens for 180ms; no layout
properties animate. Reduced motion disables the transition. Focus rings use
the sky context color in both themes, body text stays at least 4.5:1, and
status meaning is never conveyed by color alone.

The switcher is one native cycling button rather than a binary pressed toggle:
its accessible name announces the current `light`, `dark` or `system` mode and
the next action. It does not expose misleading `aria-pressed` state for the
three-mode choice.

## Reference triage: Aura UI + UI/UX Pro Max

Adopt the parts that improve an operational AI workspace: the shared
teal--sky token family, deep slate dark canvas, explicit elevation tiers,
readable card boundaries, 44px mobile controls, responsive grid rails and
high-contrast focus treatment.

Do not import decorative glassmorphism, cinematic blobs, infinite animation,
or a separate mobile product language. TOAN AAS remains a clean, dense,
application-first workspace and ERP; motion is limited to semantic
opacity/transform feedback.

At `1180px` the signed header compacts secondary labels before its layout can
clip. At `390px` the auth header keeps the TOAN AAS wordmark and moves the
locale group onto a deliberate second row. It never hides brand text merely to
fit another control.

## Verification

- Static: JS syntax, CSS diff check, token/allow-list tests.
- Rendered: authenticated workspace shell and public landing at desktop and
  375px; toggle light -> dark -> system and reload persistence.
- Accessibility: current/next button label, keyboard activation, focus ring,
  no horizontal overflow, reduced-motion media query.
- No provider, payment, Telegram or live integration calls are introduced.
