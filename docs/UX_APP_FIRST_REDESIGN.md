# TOAN AAS Web App — App-first UI/UX system

## Product intent

`app.toanaas.vn` is a signed workspace and operations application, not a
marketing landing page. The customer lands in login or their dashboard; the
optional public introduction remains at `/welcome`.

The interface must make it easy for a new customer to understand three things
at every point: where they are, what information is safe to act on, and the
next useful action. It must never make a guarded capability, a Bot-owned
record, or an unavailable provider look ready.

## Visual direction

- **Style:** Swiss-modern productivity workspace with a compact, Odoo-like
  information hierarchy. It uses a quiet dark slate foundation rather than a
  decorative "AI landing" treatment.
- **Brand expression:** one teal action accent only. Status colours are
  semantic, never the only way a state is communicated.
- **Typography:** Inter/system sans; body text is readable at 14–16px, with
  tabular figures for counts, balances and timestamps.
- **Surfaces:** solid, layered surfaces; subtle 1px dividers; restrained
  shadow. Gradients are reserved for the public `/welcome` experience, not
  operational workspace screens.
- **Motion:** 150–220ms opacity/transform transitions only. No decorative
  continuous motion; all motion respects `prefers-reduced-motion`.

## Navigation model

| Viewport | Primary navigation | Secondary navigation |
| --- | --- | --- |
| Desktop (>=981px) | Persistent sidebar with progressive disclosure | Command palette and page-level tabs/filters |
| Tablet / phone | Drawer for full navigation | Five-item labelled bottom dock for top-level destinations |

The sidebar, command palette and mobile dock all use the same server-issued
route manifest. Browser state cannot disclose an admin route or grant access.

## Shared component rules

- A visual action control has a 40px desktop minimum and a 44px mobile
  minimum. Icon-only controls carry an accessible name.
- Cards, tables, fields and dialogs use the same surface, border, focus and
  disabled-state tokens. A primary action is singular per screen.
- Forms keep visible labels, helper copy, inline error recovery and clear
  asynchronous feedback. Destructive operations remain confirmation-gated.
- Loading keeps the previous layout stable; private data is never put into a
  shell/PWA cache as a loading fallback.
- The page retains its existing semantic headings, skip link, keyboard focus
  flow, dialog focus handling and signed-session guards.

## Delivery order

1. Global design tokens, desktop/mobile app shell and shared controls.
2. Dashboard, feature discovery and the customer work surfaces.
3. Authentication, onboarding, account and billing surfaces.
4. Admin ERP information architecture and dense operational tables.
5. Visual responsive/accessibility review at 375, 768, 1024 and 1440px.

This is a presentation redesign only. It does not alter Bot ownership,
Core-Bridge contracts, wallet/PayOS authority, provider calls, CSRF/session
rules, private-download checks, or PWA no-cache boundaries.
