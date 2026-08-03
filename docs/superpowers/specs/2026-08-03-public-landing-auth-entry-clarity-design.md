# Public Landing Auth Entry Clarity — Design

## Context and evidence

The signed Web App and its public companion must be easy to enter on phone as
well as desktop. The current published `/welcome` page correctly exposes a
desktop `Đăng nhập` header action, but at `375px` the compact header retains
brand, the three reviewed locale choices, and the Aura switcher. Its direct
header sign-in and registration actions intentionally collapse to avoid
overflow. The hero still has two actions, but the anonymous secondary action
is labelled “Khám phá Studio” while it redirects to `/login?next=/features`.
That label does not state the immediate result for someone who needs to sign
in.

This slice follows the explicit product direction already approved for TOAN
AAS: a clean, clear, professional customer application with simple account
entry, VI/EN/ZH interface copy, teal/cyan Aura light/dark presentation, and no
fake provider, payment, Bot, job, or delivery action.

## Goal

Make the public landing hero's two actions truthful and immediately useful for
both account states without expanding the mobile header or changing auth,
routes, permissions, browser storage, or workflow authority.

## Alternatives considered

1. Keep the existing anonymous “Khám phá Studio” action that routes to login.
   This preserves the layout but leaves the most important mobile entry action
   mislabeled.
2. Add a visible login control to the `<=420px` header. This would compete with
   the brand, three locale selectors, and Aura switcher in a `328px` content
   column; it risks an unstable, crowded header.
3. **Chosen:** keep the compact header unchanged and make the hero CTA pair
   state-aware. An anonymous visitor sees `Tạo workspace` and `Đăng nhập`;
   the latter goes directly to `/login`. A signed visitor sees `Mở workspace`
   and `Khám phá Studio`; the latter goes directly to `/features`.

## Interaction contract

| Session state | Primary hero action | Secondary hero action | Exact destination |
| --- | --- | --- | --- |
| Anonymous | Existing `landing.cta.start` | Existing `landing.cta.signIn` | `/register`, `/login` |
| Signed in | Existing `landing.cta.workspace` | Existing `landing.hero.explore` | `/dashboard`, `/features` |

The secondary action remains an ordinary anchor. It does not submit a form,
dispatch a Portal action, call an API, write storage, affect a session, or
alter the existing language/theme controls. The existing locale catalogue
already has both copy keys in Vietnamese, English, and Simplified Chinese, so
the change adds no translation namespace or fallback copy.

## Visual and accessibility rules

- Keep the current Aura teal/cyan light and dark themes, 44px action-control
  height, semantic anchor markup, visible focus treatment, and reduced-motion
  behavior.
- Do not add a header button, overlay, toast, icon-only action, or motion for
  this correction. The visible change is wording and truthful deep-linking;
  existing route transition feedback remains sufficient.
- The action pair must remain ordered primary then secondary at phone and
  desktop widths. The `<=420px` header may continue hiding duplicated header
  actions because the hero is in the first viewport.

## Safety boundary

This is presentation/navigation clarity only. It does not change Telegram
linking, email/password/OAuth registration, signed session handling, CSRF,
Web/Telegram identity ownership, wallet/Xu/PayOS authority, provider calls,
feature readiness, job creation, or PWA caching.

## Verification

Create a static Portal contract that locks both exact session-state CTA pairs,
their copy keys and destinations, and rejects new network/storage/action/form
tokens in the landing action projection. Run the focused landing and i18n
contracts plus Portal JavaScript syntax. Then inspect `/welcome` on production
read-only at desktop and `375px`, in light and dark, confirming the anonymous
secondary label is `Đăng nhập`, the route is `/login`, and no console error or
horizontal overflow appears. Restore the browser's previous system theme after
the audit.
