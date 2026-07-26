# TOAN AAS `/welcome` Public Companion Design

## Purpose

Turn `/welcome` into a concise, professional introduction to the TOAN AAS
Web App.  It must share the teal–cyan brand system with the signed workspace
while making the distinction clear: the public page explains the product; the
signed Web App owns projects, planning, account controls and real workflow
state.

## Scope boundary

- This repository owns `app.toanaas.vn` and `/welcome` only.
- The live root `toanaas.vn` is presently served from the Bot repository.
  The Bot is read-only in this work, so the root-domain landing is explicitly
  not changed or deployed here.
- No Bot source, Core Bridge authority, session model, CSRF, wallet/Xu,
  PayOS, provider key, webhook, job or delivery behaviour changes.
- `/welcome` stays public and does not fetch account data, create a job,
  invent an output, submit payment or cache private data.

## Audience and language

The page is Vietnamese-first for new Vietnamese customers, with reviewed
English and Simplified Chinese versions.  The locale switcher is a
presentation-only public `?lang=vi|en|zh` choice.  It is exact allowlist
input, does not persist, does not read or write a signed profile and never
copies a Telegram/Bot locale or changes a workflow language.

## Layout and visual system

Use the accepted teal–cyan direction and the page override at
`design-system/toan-aas-web-app/pages/welcome.md`.

1. A restrained header carries the TOAN AAS mark, product anchors, locale
   selector, sign-in/account action and one primary CTA.
2. The hero states the value proposition in one sentence, then explains the
   real boundary: Web App authoring is independent; an engine or Bot
   companion connects only after its capability is ready.  A semantic HTML
   workflow preview illustrates `Brief → Plan → Confirm → Delivery` without
   showing fabricated customer data.
3. Six real, route-backed studios explain planning/use cases with uniform
   cards, existing SVG icons and no emoji or provider-logo decoration.
4. A four-step workflow section names the stage, expected customer action and
   real guardrail.  It never presents a finished result before a verified job
   and delivery exist.
5. A trust section explains signed sessions, guarded integrations and private
   delivery in plain language.  It supplements colour with labels and icons.
6. The final CTA and footer use only valid `/register`, `/login`, `/account`,
   `/legal` and `/privacy` routes.

## Copy rules

- Use clear Vietnamese verbs and short sentences.  Avoid Bot-only terms,
  hyperbole, vague “AI magic”, fake metrics and unsupported provider claims.
- English and Chinese are equivalent product copy, not machine fallback or
  untranslated Vietnamese strings.
- The landing may say a capability is guarded or forthcoming when that is the
  actual state; it must not create an unavailable feature to make the page
  look complete.

## Accessibility and responsive behaviour

- Reuse Portal SVG icons, semantic landmarks, heading order and descriptive
  aria labels.  Buttons and locale controls are at least 44px on mobile.
- The primary teal button uses dark ink.  Focus rings on public light surfaces
  retain the final cyan 3px, high-specificity indicator.
- At 920px the hero becomes a single column.  At 600px the header reduces to
  the brand plus real account actions and the locale selector; no content may
  overflow the safe-area gutters.
- The stylesheet uses only semantic theme tokens introduced by the teal–cyan
  foundation.  Reduced motion remains supported.

## Acceptance criteria

- `/welcome?lang=vi`, `en` and `zh` render matching reviewed copy and
  document metadata; invalid or legacy locale parameters fall back to `vi`
  without being echoed.
- The renderer has no public provider, wallet, job, payment, upload or
  delivery action.  CTA routes are real and retain correct signed/anonymous
  behaviour.
- Every added translation key exists exactly once in each reviewed catalog.
- Desktop and 390px mobile smoke checks show no horizontal overflow, no
  clipped CTA, no inaccessible focus regression and no console error.
- The repo continues to pass the i18n, access, PWA and focused landing
  contracts; Bot and live-provider tests are not run.
