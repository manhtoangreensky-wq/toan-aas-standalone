# `/welcome` Page Override

This page inherits `../MASTER.md`.  It is the public companion at
`app.toanaas.vn/welcome`, not the production root `toanaas.vn` marketing
site.  It introduces the product and sends customers into a real signed
Web App flow; it does not claim that a provider, job, payment, asset or Bot
action has already happened.

## Visual direction

- Use the light canvas `--portal-light-canvas`, light surface
  `--portal-light-surface`, ink `--portal-ink`, teal action
  `--portal-accent` and sky-cyan context `--portal-info` from the master.
- Keep a single, quiet editorial hero with a balanced two-column desktop
  composition.  The product preview is a semantic HTML illustration, not a
  screenshot or fabricated user data.
- Use Inter with a 52–64px desktop H1 and 36–46px mobile H1.  Body copy is
  16px or larger with a readable 55–65 character measure.
- Use the existing Portal SVG icon system.  Do not use emoji, decorative
  animated blobs, provider logos or fake metrics.
- Use only 150–220ms opacity/transform feedback and respect the inherited
  reduced-motion rule.

## Information hierarchy

1. Header: TOAN AAS mark, three in-page anchors, reviewed locale switcher,
   Aura light/dark switcher, sign-in/account action and one teal primary CTA.
2. Hero: one direct product statement, one short factual explanation, two
   real route CTAs, three concise trust statements and a workflow preview.
3. Studios: six real Web App routes grouped as a compact, even grid; every
   card says what can be prepared today instead of promising a provider
   result.
4. Workflow: `Brief → Plan → Confirm → Delivery` as an explicit four-step
   sequence.  Explain that confirmed jobs and private delivery remain
   capability-gated.
5. Trust: signed sessions, guarded integrations and private delivery, each
   expressed with an SVG icon and text rather than colour alone.
6. Final CTA and legal footer: retain only real account, legal and privacy
   routes.

## Locale and responsive rules

- The public selector may request exactly `vi`, `en` or `zh` through the
  dedicated public `lang` query value.  It is display-only, not persisted,
  does not read a Telegram locale and never changes workflow language.
- At 920px collapse the hero to one column and place the preview after the
  copy. At 600px retain 44px controls, safe horizontal padding and no
  horizontal overflow. At 420px keep the locale selector and Aura switcher in
  the header, while the duplicate nav CTA yields to the real hero CTA below.
- Keep header, CTA and proof text aligned to the same content container; do
  not centre unrelated content inside cards just to fill space.

## Cinematic Mini refinement

- The public landing may use a single cinematic opening: editorial H1 curtain,
  shallow teal–sky aperture frame and the existing semantic preview steps.
  This is a presentation layer only; it never substitutes a photographic
  background, fabricated activity, a provider result or a fake account state.
- `/welcome` defaults to Light only when the browser has no saved theme value.
  Its header exposes explicit **Sáng** and **Tối** choices. An explicit browser
  choice is reused; the signed application keeps its established theme cycle.
- The cinematic lifecycle is default on `/welcome`; `?motion=0` is reserved for
  a no-motion comparison. `prefers-reduced-motion` keeps the aperture static
  and reveals every control/content item immediately.
- Keep the aperture as one quiet background frame. The scroll-continuity
  extension may add bounded, CSS-variable-driven parallax on the semantic
  preview, a section progress wash, and pointer tilt on the preview/studio
  surfaces. It must never pin the whole page, scroll-jack, animate body copy
  independently, use ambient video, or add an unbounded looping glow.
- Reference-derived motion is limited to the interaction grammar (sticky
  compact header, masked transition, depth layers, section reveal and hover
  response); it does not copy Lisa Nail & Spa's imagery, typography, palette or
  brand identity. All content stays code-native and truthful to Web capability.
- Every continuous effect is presentation-only, uses transform/opacity/CSS
  variables, is throttled through one `requestAnimationFrame` scroll loop, and
  fails open to a fully visible static page under `prefers-reduced-motion` or
  `?motion=0`.
