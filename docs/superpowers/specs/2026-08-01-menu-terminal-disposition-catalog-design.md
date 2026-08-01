# Manual Transcript Fallback Design

## Context

The static parity audit identifies `menu|translation_transcript` as a
known-broken Bot branch. The frozen Bot stores a `transcript` pending source,
but its later callback accepts only voice, file and text and returns an
unsupported-source alert. The current Web App has an independently signed,
owner-scoped Subtitle Studio for manual transcript and cue authoring.

The Web route must not inherit or replay the Bot pending source, Telegram
identity, file/media, selected language, provider request, job, wallet/Xu,
PayOS, payment, output or delivery state.

## Options considered

1. Keep the action only as a known-broken Bot boundary.
   This is safe, but leaves a customer-facing dead end despite a capable
   Web-native manual alternative.
2. Add a Bot/core translation bridge.
   This is outside this Web-only task, would require Bot changes and a
   canonical provider/job/payment/delivery contract.
3. Map this one exact Bot literal to a fresh guarded `/subtitle-studio`
   workspace that begins with a blank Web-owned manual transcript.
   It fixes the customer journey without claiming that the Bot runtime worked.

Option 3 is selected. All other non-Video Bot-canonical mutation callbacks
remain explicitly guarded or Telegram-only, and Video-menu work remains last.

## Scope

- Add one finite, case-sensitive descriptor for `menu|translation_transcript`.
- Preserve the Bot-known-broken evidence in the mapping and prohibit all
  runtime, provider, job, finance and delivery claims.
- Generate the translation boundary contract with the Bot failure and manual
  Web fallback shown separately.
- Regenerate only migration artifacts that are outputs of the static audit.
- Add focused audit tests for exactness, status, and no-route/no-runtime
  invariants.

## Out of scope

- Editing `bot.py`, deploying a Bot bridge, or changing Telegram callbacks.
- Creating a translation provider bridge, ASR, job, wallet/Xu, PayOS, payment,
  output or delivery path.
- Changing any Video-menu callback or LocalVideoStudio-owned file.
- Claiming that the known-broken Bot transcript action works in Web.

## Design

The audit will use a private finite descriptor keyed by the exact lower-case
literal. It will emit a guarded Web fallback to `/subtitle-studio`, with no
raw callback payload, browser parameter or preselected source. The mapper will
retain the known-broken Bot status and explicitly state that the Web route is
manual authoring only.

The generated contract will distinguish the Bot failure from the new manual
Web alternative. A case variant, suffix, unknown source and every Video literal
stay on existing fail-closed mappings.

## Verification

Focused tests will prove exact mapping, guarded status, no public catalog
exposure and no runtime claim. A case variant and a Video literal will remain
outside the fallback. The full static audit will run once because it generates
the updated migration artifacts.
