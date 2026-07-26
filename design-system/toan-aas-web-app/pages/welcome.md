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
   sign-in/account action and one teal primary CTA.
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
  copy.  At 600px retain 44px controls, safe horizontal padding and no
  horizontal overflow.  The locale selector must remain discoverable without
  crowding the two primary account actions.
- Keep header, CTA and proof text aligned to the same content container; do
  not centre unrelated content inside cards just to fill space.
