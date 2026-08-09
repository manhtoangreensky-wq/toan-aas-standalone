# Subtitle Studio Quality Report Contract

## Purpose

`GET /api/v1/subtitle-studio/projects/{project_id}/quality` is a signed,
owner-scoped, aggregate-only self-review read for the Web-native Subtitle
Studio. It is not an AI verdict, media analysis, provider task or delivery.

## Request

| Input | Values | Default |
| --- | --- | --- |
| `project_id` | Canonical UUID owned by signed account | none |
| `track` | `source`, `translation`, `both` | `both` when omitted |
| `profile` | `generic`, `vi`, `en`, `zh` | `generic` when omitted |

Explicit empty or unknown `track`/`profile` values are HTTP 422. A project
outside the signed account returns the existing guarded not-found envelope;
the route never reveals another account's project state.

## Safe response data

The response may contain only project/revision identity, requested option,
unit metadata, aggregate metric counts, translation coverage, fixed review
state/reason labels and the standard false execution boundary flags.

It must not contain:

- cue IDs, ordinals, timestamps or per-cue result rows;
- caption, translation, notes or excerpts;
- assets, media, file paths, URLs or download metadata;
- provider handles, Bot/bridge state, jobs, PayOS, wallet or payment data;
- a result that claims processing, output creation or delivery.

`present_duration_ms` means the summed duration of cue rows that contain text
for the selected track. It is not the source media duration or full timeline
duration.

## Status rules

| Case | `review_status` | `review_reasons` |
| --- | --- | --- |
| Active rows with no structural reason | `clear` | `[]` |
| No active cue and the selected track applies | `needs_review` | `no_active_cues` |
| Target language requested but one or more selected translations are empty | `needs_review` | `translation_incomplete` |
| `track=translation` but project has no target language | `not_assessed` | `[]` |

Archived projects and malformed persisted rows are guarded, not successful
empty reports.

## Read/write boundary

The route uses a read transaction and must not mutate Subtitle Studio projects,
cues, versions, idempotency records, workspace events or audit events. Signed
session validation can update the normal session heartbeat; that authentication
behavior does not alter the subtitle domain.

## Portal boundary

The Portal fetches this route only after owner-scoped detail hydration. It
validates the complete payload and execution boundary, copies only approved
primitive aggregate fields into current-tab state, and clears them on logout,
route change, stale response, list transition or validation failure. The
report is accepted only when `project_revision` exactly matches the detail
revision being rendered; a cross-tab mutation therefore produces a guarded
panel instead of mixed snapshots. The renderer has no fetch, execution or
payment code and shows guarded state when the contract is not safe.
