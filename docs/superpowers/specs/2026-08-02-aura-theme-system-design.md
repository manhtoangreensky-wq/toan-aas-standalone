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
- Every switch is keyboard accessible, has a 44px target, updates
  `aria-pressed`, and honors `prefers-reduced-motion`.

## Component and token design

`portal-theme.css` owns semantic tokens for canvas, surface, elevated surface,
text, muted text, border, focus, action, accent, status and shadows. A
`[data-portal-theme="dark"]` override maps only those tokens and a small set of
legacy hard-coded surfaces. Existing component classes continue to consume
semantic variables, so route-specific markup does not fork between themes.

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

## Verification

- Static: JS syntax, CSS diff check, token/allow-list tests.
- Rendered: authenticated workspace shell and public landing at desktop and
  375px; toggle light -> dark -> system and reload persistence.
- Accessibility: button name/pressed state, keyboard activation, focus ring,
  no horizontal overflow, reduced-motion media query.
- No provider, payment, Telegram or live integration calls are introduced.
