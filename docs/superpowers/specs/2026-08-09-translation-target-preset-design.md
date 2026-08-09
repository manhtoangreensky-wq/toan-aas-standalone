# Translation Target Preset Design

## Goal

Make the existing Web-native manual Subtitle Studio translation intake easier to start in Vietnamese, English and Chinese without representing a Bot callback, provider translation request, job or delivery.

## Scope

- Applies only to `/subtitle-studio/new?intent=translation`.
- Offers a closed directional pair chooser: `vi-en`, `en-vi`, `vi-zh`, `zh-vi`, `en-zh`, and `zh-en`.
- Converts the selected pair into the existing `source_language` and `target_language` fields immediately before the existing signed, CSRF-protected project-create request.
- Keeps the general Subtitle Studio route unchanged, including its existing manual language labels.

## Boundary

The chooser creates a new Web-owned authoring project only. It never reads Telegram pending state, takes a Telegram ID, calls the bridge/provider/job/payment APIs, creates output, or changes Bot authority. `tr_target` remains `CORE_CANONICAL_TRANSLATION_GUARDED`.

## Interaction

1. A reviewed `/translate` companion link opens the existing fresh route with `intent=translation`.
2. The new route renders one labelled language-pair select instead of free-form language source/target fields.
3. The browser accepts only a closed pair key, maps it to the two existing request properties and submits through the current idempotent project-create flow.
4. An absent, malformed, wrong-route, or non-translation query value keeps the manual source/target language form; browser-supplied values outside the pair set are rejected before API submission.

## Verification

- Static portal contract proves the pair set, route+intent query gate, and no runtime/network capability in the preset helper.
- Integration contract proves a closed-pair parser produces the existing request fields and rejects bypass input before the API call.
- Existing Subtitle Studio contract remains text-only and preserves `/translate` as a companion navigation, not an alias or runtime translation claim.
