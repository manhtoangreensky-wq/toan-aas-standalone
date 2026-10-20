# MU-C — Music quote freshness and safe confirmation

## CONTRACT

Scope: customer-facing Music form presentation only (`/music/create` and
`/music/song`). A Music confirmation button may be visible only when the
server-issued estimate is fresh, the form fingerprint has not changed, the
receipt is valid and the public price is a finite known number ≥ 0. A real
zero is valid; missing, conflicting, negative, string or non-finite prices are
unknown and must remain blocked.

Allowed: `static/portal/portal.js`, `static/portal/portal-i18n.js`, one focused
Music test and this checklist/spec/evidence. Protected: integration payload,
backend quote/charge rules, Voice/Image quote behavior, wallet/PayOS/provider,
engine, schema, action values and blue/navy/teal tokens.

## Root finding

At `portal.js:11643–11648`, confirm visibility applies a public-price guard
only to Voice and Image; Music can expose confirm when execution capability is
present but price is unknown. Input freshness comparison and expiry timer are
also Voice-only (`voiceQuoteHasEdits`, `synchronizeVoiceQuoteFreshness`,
`scheduleVoiceQuoteExpiry`), while integration later rejects a stale
fingerprint. This produces a late error instead of a clear Music UI state.

## Required behavior

1. Add a Music-only comparison/state helper; compare only declared form fields,
   preserving file/password exclusions and treating defaults consistently.
2. Use the helper in render and input/change synchronization. Show a localized
   “options changed / quote expired / price unavailable” note and hide confirm;
   never send a request as part of this UI change.
3. Extend the existing single quote timer to Music routes without a second
   timer or remount. On expiry, re-evaluate the current Music form and hide
   confirm. Route change clears/replaces the timer.
4. Do not infer currency, compute price, enable a provider, or change receipt
   validation. Price `0` is explicitly known.

## Checklist

- [ ] AC01 fresh known price including 0 permits only the existing guarded
  confirm path; unknown/conflicting/negative/string price blocks it.
- [ ] AC02 editing any Music form field makes quote stale and keeps content.
- [ ] AC03 expiry hides confirm through the existing timer without remount.
- [ ] AC04 VI/EN/ZH note/fallback copy is balanced; Voice/Image comparators pass.
- [ ] AC05 targeted/full Node, syntax/diff-check and QA browser fixture pass.

Verify: `node --test tests/music-quote-freshness.test.mjs tests/music-canonical-suggestions-presentation.test.mjs tests/music-product-controls.test.mjs tests/music-flow-state-and-surface-contract.test.mjs tests/music-workspace-draft-navigation.test.mjs` → zero failures. Provider/wallet/deploy/LIVE remain zero/NO/NOT_TESTED.
