# Subtitle Quality & Readability Design

## Goal

Add a deterministic, owner-scoped Subtitle Studio report that summarizes the
structure of the active cue timeline before a customer performs self-review.
It is a Web-native, aggregate-only read: it does not claim AI review, make a
content judgement, create an output, or call an external engine.

## Scope and boundaries

- New route: `GET /api/v1/subtitle-studio/projects/{id}/quality`.
- Query contract: `track=source|translation|both` and
  `profile=generic|vi|en|zh`. Omission uses the documented defaults;
  explicit blanks and unknown values receive HTTP 422.
- The lookup is owner-scoped through the signed Web account. A different
  account receives the guarded `WEB_SUBTITLE_PROJECT_NOT_FOUND` envelope.
- Archived projects return `WEB_SUBTITLE_PROJECT_ARCHIVED`. Corrupt,
  oversized, duplicate-ordinal, invalid-timestamp, or overlapping active cue
  rows return `WEB_SUBTITLE_QUALITY_DATA_GUARDED`.
- Only active cues are read. The response is bounded to the project cue cap.
- The endpoint never writes subtitle projects, cues, versions, idempotency
  receipts, Subtitle Workspace events, or audit events. Existing signed-session
  authentication may update its normal session heartbeat and is outside the
  Subtitle Studio domain.
- No Bot, bridge, provider, ASR, translation, TTS, dubbing, payment, wallet,
  file, asset, job, download, media preview, or output path is called.

## Aggregate model

The server NFC-normalizes text for measurement only. It returns aggregate
counts, not per-cue assessment or text. For each selected track it reports:

- present/empty cue counts;
- text-unit count and largest cue count;
- `present_duration_ms`: duration of cues that actually contain text for that
  track, explicitly not a media duration or full timeline duration;
- units per minute over that present-text duration; and
- translation coverage only when the project requested a target language.

`generic` and `zh` measure non-whitespace characters; `vi` and `en` measure
whitespace-separated tokens. This is a neutral unit choice, not a quality
threshold or score.

The only fixed review reasons are `no_active_cues` and
`translation_incomplete`. A translation-only request with no target language
is `not_assessed` and intentionally has no reason inherited from the source
track.

The payload never contains cue IDs, ordinals, source/translated text, notes,
excerpts, timestamps, URLs, media metadata, asset paths, provider handles, or
generated result details.

## API shape

Successful responses use `status: "read_only"` and keep the existing false
execution boundary fields:

```json
{
  "ok": true,
  "status": "read_only",
  "data": {
    "project_id": "opaque UUID",
    "track": "both",
    "profile": "vi",
    "profile_unit": "whitespace_tokens",
    "checked_cue_count": 12,
    "translation_requested": true,
    "tracks": {
      "source": {
        "applicable": true,
        "present_cue_count": 12,
        "empty_cue_count": 0,
        "unit_count": 140,
        "max_units_per_cue": 18,
        "present_duration_ms": 24000,
        "units_per_minute": 350.0,
        "coverage_percent": null
      }
    },
    "review_status": "clear",
    "review_reasons": []
  }
}
```

## Portal experience

Project-detail hydration requests the report only after validating the signed,
owner-scoped project detail. The client validates the full boundary and schema,
then retains a new sanitized projection containing only the fields shown by the
panel. It clears that projection on session, route, list, failure, or stale
request changes.

The compact Quality panel sits beside the existing Timeline Estimate card and
shows only aggregate metrics, review state and localized fixed reason labels.
Loading, archived and guarded states deliberately replace data rather than
showing stale values. A report is accepted only when its `project_revision`
matches the owner-scoped detail revision currently rendered; a mismatch is
guarded until the project is refreshed. A translation-only request without a
target language has a dedicated `not_assessed` explanation rather than the
copy used for a clear report. It supports Vietnamese, English and Chinese,
uses the existing teal/cyan light/dark system, and becomes one column on
small screens.

No new local storage, URL state, private PWA cache entry, fake completion,
provider action, browser POST, or unsafe animation is added.

## Verification

1. API tests cover authentication, owner scope, blank/unknown queries,
   deterministic replay, track shape, redaction, archive/corruption/overlap
   guards, non-applicable translation, bounded rows, boundary fields and zero
   Subtitle Studio domain writes.
2. Portal contract tests cover the owner-scoped route, strict validator,
   sanitized state, localized renderer and absence of execution calls in the
   renderer.
3. Targeted tests, JavaScript syntax checks, diff check and local UI smoke
   validate normal, guarded and mobile detail states without external calls.
