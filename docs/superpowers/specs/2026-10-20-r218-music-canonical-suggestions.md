# MU-B — Music suggestions presentation

## CONTRACT

Scope: Music-only projection of server-issued planning suggestions in
`renderCanonicalFlow`; no engine, provider, quote, payment, job, asset or
motion behavior. The UI must show the real suggestions that arrive in the
canonical draft/estimate and must never invent a missing option.

Allowed files: `static/portal/portal.js`, `static/portal/portal-i18n.js`,
`tests/music-canonical-suggestions-presentation.test.mjs`, this spec and the
R218 checklist/state/evidence. `portal-theme.css` is protected unless a
route-scoped selector is proven necessary. Protected: Voice/Image/Video
generic renderer, integration payloads, action values, quote guards,
provider/wallet/PayOS/auth and the blue/navy/teal tokens.

## Root finding

The existing generic renderer at `static/portal/portal.js:31872–31883`
maps the first three array entries, including malformed objects, into cards;
it uses fixed English/technical labels and adds a generic first-suggestion
action. Music with flow is rendered through that generic path at
`static/portal/portal.js:32373`, so EN/ZH can leak technical copy when data is
present. This is a presentation boundary defect, not proof of a bad provider
payload.

## Required behavior

1. Accept only object suggestions with a non-empty bounded `prompt`. Render at
   most the first three valid items; render one or two real cards when only one
   or two are valid and never add a placeholder card.
2. Escape every server/user value. Keep prompt/name/metadata as received; do
   not translate or infer their content. Use localized `musicProduct.*` keys
   for heading, explanation, metadata labels and copy/apply actions.
3. Keep copy/apply actions scalar-only and route/field-bound through the
   existing `canonicalDraftActions`; do not imply engine selection or confirm.
4. Music flow must not render generic canonical source/planning jargon or a
   duplicate global first-suggestion action. It must not render audio, player,
   download, confirm, provider request or price.
5. Missing/malformed data renders one concise localized notice and zero fake
   cards; the surrounding form remains unchanged.

## Checklist and gates

- [ ] AC01 valid fixture with 3 prompts renders exactly 3 cards in VI/EN/ZH.
- [ ] AC02 0/1/2/malformed fixture renders no filler; XSS is escaped.
- [ ] AC03 fixed Music chrome is locale-complete and has no `canonical`,
  `planning`, `provider`, `asset`, `job`, `Engine`, `server` leakage.
- [ ] AC04 copy/apply retains scalar prompt and route/field; no audio,
  download, confirm or network behavior is introduced.
- [ ] AC05 targeted tests, full Node regression, syntax and diff-check pass.

Verify: `node --test tests/music-canonical-suggestions-presentation.test.mjs
tests/music-product-controls.test.mjs tests/music-flow-state-and-surface-contract.test.mjs
tests/music-workspace-draft-navigation.test.mjs` → all pass, zero failures.
No provider calls, wallet mutations, deploy or LIVE claim.
