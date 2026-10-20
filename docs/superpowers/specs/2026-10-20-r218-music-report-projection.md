# MU-D — Music progress/report projection

## CONTRACT

Scope: Music-only result/report surface after the canonical flow returns a
confirm status. Project only bounded server signals: status, numeric progress,
output availability, download readiness, delivery readiness and a short safe
reason. Never fabricate audio, player, download link, two-track result, asset
ID or provider success. Existing `safeVoiceReport` is reused read-only; no
Voice behavior changes.

Allowed: `static/portal/portal.js`, `static/portal/portal-i18n.js`, one focused
Music test plus this spec/checklist/state/evidence. Protected: generic Voice,
Image, Video report renderers; integration payload; job/asset APIs; engine,
provider, wallet/PayOS, schema and motion.

## Root finding

Music canonical flow currently ends at generic `renderFeatureTracking` and a
generic result dump. It does not provide a localized Music report projection;
`completed` can therefore look like a result without a clear, bounded
delivery state. The existing Voice report helper already rejects non-numeric
progress and unknown download/output booleans, so this spec projects those
signals without changing their truth rules.

## Required behavior

1. On Music confirm, render one localized report section. With no report, show
   a pending message; with a report, show only known fields.
2. Escape server reason text and preserve zero/decimal progress semantics.
3. Never emit `<audio>`, `download`, private URL, player, asset/job claim or
   success wording unless an explicit canonical field is already known; even a
   ready boolean remains a status, not a fabricated file.
4. Keep tracking/job navigation and confirm payload unchanged; no network or
   mutation from rendering.

## Checklist

- [ ] AC01 pending/processing/completed/failed report states render in VI/EN/ZH.
- [ ] AC02 numeric progress/output/download/delivery truth is bounded and
  escaped; unknown values are not shown as false or ready.
- [ ] AC03 no audio/player/download/private URL/fake two-track output.
- [ ] AC04 Voice/Image comparators and full regression remain green.
- [ ] AC05 browser fixture has report DOM, no external requests/console errors.

Verify: `node --test tests/music-report-projection.test.mjs tests/music-quote-freshness.test.mjs tests/music-canonical-suggestions-presentation.test.mjs tests/music-product-controls.test.mjs tests/music-flow-state-and-surface-contract.test.mjs tests/music-workspace-draft-navigation.test.mjs` → zero failures. Provider/wallet/deploy/LIVE remain zero/NO/NOT_TESTED.
