# Postback Readiness Locale Design

## Goal

Present every Portal-owned fixed label on the signed canonical-admin
`/admin/growth/postback-readiness` preparation guide in reviewed Vietnamese,
English, and Simplified Chinese without turning it into a postback
configuration, event, attribution, or payout surface.

## Architecture

Add one equal-key `adminGeneric.postbackReadiness.*` catalogue and a narrow
`adminPostbackReadinessText()` wrapper beside the existing Admin Generic
locale helpers. The renderer resolves only presentation constants through that
wrapper; route paths, signed authorization outcomes, badge state, page object
data, and canonical role state stay runtime data.

The guide's two existing route notes also need localization. `renderNotes()`
will accept an optional, presentation-only labels object while retaining its
current Vietnamese defaults for every existing caller. The Postback renderer
will pass a shallow local notes object containing translated fixed note bodies
and safe translated labels. No route registration, navigation manifest,
server guard, bridge, or data model changes are required.

## Closed Locale Namespace

Each of `vi`, `en`, and `zh` contains the identical key set:

```text
route.{title,description}
intro.{kicker,title,body,statusTitle,statusBody}
checklist.{kicker,title,body}
checkpoint.{scope,dedupe,handoff}.{title,body}
handoff.{kicker,title,body,itemScope,itemAuthority,itemChannel}.{title,body}
limits.{kicker,title,body}
boundary.{noConfig,noEvents,noFinancial}.{title,body}
link.{growth,audit}
notes.{integration,safety}.{title}
notes.{scope,botBoundary}.{body}
```

`title` interpolation is not needed; no route, authority, server state,
manifest value, account identifier, connection datum, callback, or tracking
field becomes a locale key.

## Invariants

- Preserve the generic canonical-admin server gate for the exact route.
- Preserve `serverAuthorizesAdminRoute(context, "/admin/growth")`,
  `serverAuthorizesAdminRoute(context, "/admin/audit")`, the existing two
  paths, `badge("read_only")`, `renderHero(page, context)`, and guarded-link
  behavior.
- Preserve the exact fallback strings already rendered in Vietnamese when the
  catalogue is unavailable; translated catalogue values may differ by locale.
- Keep `renderNotes(page)` output unchanged when no optional label object is
  supplied, and escape every localized label/body before it reaches HTML.
- Add no browser fetch/API call, form, POST, storage, URL state, refresh,
  bridge target, configuration, credential, tracking URL, event/replay,
  attribution, referral, reward, Xu, payment, revenue, payout, entitlement,
  or audit-event behavior.
- Do not edit Bot files, `app.py`, `integration.js`,
  `copyfast_admin_erp_navigation.py`, `copyfast_registry.py`, CSS, migration
  audit logic, provider/PayOS/wallet code, or Railway configuration.

## User-visible Behavior

A signed canonical administrator receives consistent VI/EN/ZH route title,
description, guide copy, checklist, handoff sequence, safety boundaries,
authorized link labels, and note labels/bodies. The page stays intentionally
read-only and continues to disclose that all real configuration and event
handling remain in the canonical Bot-owned process.

## Verification

Focused static and Node runtime contracts prove equal catalogue coverage,
route chrome/first-paint localization, fallback compatibility, safe rendering,
and preservation of the no-control-plane boundary. The bounded Web App gate
and migration evidence verifier provide release evidence. No live Bot,
provider, Telegram, PayOS, wallet, or Railway action is run.
