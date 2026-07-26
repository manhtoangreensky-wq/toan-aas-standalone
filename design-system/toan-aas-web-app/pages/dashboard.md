# `/dashboard` Page Override

This page inherits `../MASTER.md`. It is the signed customer command center,
not a marketing surface. The dark ink-blue workspace shell, teal primary
action and cyan contextual states are already established by the master.

## Visual direction

- Retain the existing data-first command-center layout: a concise workspace
  summary, explicit work/account/canonical lanes and a studio launchpad.
- Keep the dashboard dense but calm. A metric never substitutes an unverified
  canonical value with `0`, and empty states remain descriptive rather than
  decorative.
- Align headings, cards, actions and table edges to the existing shell grid.
  Do not add hero imagery, marketing gradients, fake charts, fake activity or
  new dashboard cards merely to fill space.
- Keep the existing SVG icon family, 44px mobile controls and reduced-motion
  rules. Status always has a textual label in addition to color.

## Language and data boundary

- Vietnamese is the default. English and Simplified Chinese must receive
  equivalent reviewed UI copy for all fixed Dashboard chrome.
- Project titles, brief text, customer records, file names, dates, numbers,
  canonical provider status and other server/customer data are never
  translated in the browser.
- The Dashboard remains a signed, owner-scoped reader. It does not create
  provider calls, job writes, wallet/ledger changes, payment confirmation or
  asset delivery just because a different display locale is selected.
