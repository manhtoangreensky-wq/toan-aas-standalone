# Delivery Center Light Surface Design

## Status and scope

This approved presentation slice makes the existing customer Delivery Center
(`Jobs`, `Job detail`, and canonical `Assets`) consistent with the teal/cyan
light application system. It is a UI-only slice: delivery, job, output,
download, receipt, payment, provider, Bot and Core Bridge authority remain
unchanged.

The routes remain signed-session routes:

| Route | Customer purpose | Truth boundary that must remain visible |
| --- | --- | --- |
| `/jobs` | Review owner-scoped canonical job metadata | A completed job is not automatically a downloadable asset. |
| `/jobs/{id}` | Inspect one owner-checked job and its delivery lifecycle | Output metadata, delivery contract, recovery and support remain separate states. |
| `/assets` | Find assets returned by the canonical delivery boundary | `reported`, `pending`, `validated`, `unavailable` and Web Vault origin are not interchangeable. |

`/asset-vault` is deliberately outside this slice. Its existing
`.portal-asset-vault` ownership and lifecycle styling remain intact.

## Visual system

- Add `.portal-delivery-page` only to the three Delivery Center renderers so
  the final theme layer is route-local.
- Use existing `--portal-*` semantic tokens only: light/soft surfaces,
  `--portal-ink`, `--portal-muted`, action/context colors, semantic status
  colors, `--portal-focus`, and motion tokens.
- Make the delivery navigation an aligned, stable three-item route strip on
  desktop. At `700px`, it becomes a three-column grid with no horizontal
  scrolling or snap behavior. Every touch control remains at least `44px`.
- Keep cards stationary: hover and focus alter only tokenized
  border/background/color. No lift, transform, new shadow, opacity trick or
  invented success state is permitted.
- At `980px`, the job-detail work grid becomes one column so the delivery
  protection panel does not compress the canonical job facts.
- Keyboard focus is a clear `3px` focus ring. Reduced motion removes the
  cosmetic transitions and transforms from delivery cards, route links,
  filters and controls.

## Truth and safety boundaries

- The renderers retain their exact routes, labels, `data-*` controls,
  disabled state, signed-download ownership checks, status sources and support
  copy. The class addition has no business logic effect.
- The light layer must preserve semantic state colors for `reported`,
  `pending`, `validated`, `unavailable` and `vault`; it must not use a generic
  text reset that masks them.
- No file is downloaded, uploaded, mutated, retried, refunded, queued,
  delivered, charged or sent to a provider during implementation or QA.

## Acceptance evidence

1. A red-first static contract isolates only `/* Final light Delivery Center
   surface */`, requires the renderer class, and checks scoped token-only CSS
   declarations for status, navigation, focus, responsive and motion rules.
2. Existing delivery identity/navigation, asset lifecycle and portal safety
   tests continue to pass.
3. A private-route browser visual pass is claimed only if a signed local
   session is attachable. Anonymous redirect smoke is safe; no state-changing
   interaction is allowed.

## Local verification record

- The new contract was exercised red-first for the absent route class, then
  passed green after the route-local renderer class and final light CSS layer
  were added.
- The focused Delivery, identity, navigation, Asset Vault lifecycle and portal
  safety suite passed with `177 passed`. JavaScript syntax and `git diff
  --check` also passed.
- No local application listener or signed browser session was available for a
  private-route visual smoke. This record therefore does not claim a rendered
  browser pass, and no file, job, support, payment, provider or Bot action was
  performed.
