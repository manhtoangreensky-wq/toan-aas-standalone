# Subtitle Quality & Readability Implementation Plan

**Goal:** Give each signed Subtitle Studio project a deterministic,
aggregate-only structural report for self-review without exposing caption text
or invoking an execution engine.

**Architecture:** `copyfast_subtitle_workspace.py` reads active owner-scoped
cues inside a SQLite read transaction. `integration.js` validates and reduces
the response to a safe tab-memory projection. `portal.js` renders only that
projection; `portal-i18n.js` owns the visible vi/en/zh strings; CSS uses the
existing teal/cyan token surface.

## Task 1 — Read-only server contract

- [x] Write a RED API test for owner scope, deterministic replay and absence
  of caption text.
- [x] Add the read-only route and bounded aggregate metrics.
- [x] Extend RED tests for blank query values, redaction, track selection,
  full boundary flags, no-write Subtitle Studio snapshots, overlap corruption
  and non-applicable translation.
- [x] Make malformed query values reject with HTTP 422 and make persisted
  timeline invariant violations fail closed.
- [x] Run `pytest -q tests/test_copyfast_subtitle_workspace.py -k quality`.

## Task 2 — Private Portal panel

- [x] Write a RED Portal contract test for the quality path, validator,
  renderer and isolated styling.
- [x] Add session/request epoch fencing, strict schema validation and a
  sanitized state projection.
- [x] Render an aggregate-only detail panel with loading, guarded and archive
  states; do not render per-cue details or text.
- [x] Add vi/en/zh labels and responsive teal/cyan theme rules.
- [x] Run the Portal contract test, JS syntax checks and local browser smoke;
      the smoke covered signed registration/login, project/cue authoring,
      settled quality metrics, desktop/mobile layout and console health with
      provider/payment/bridge flags disabled.

## Task 3 — Review and source-of-truth sync

- [x] Inspect the complete diff and remove any stale wording or out-of-scope
  file.
- [x] Run the targeted regression suite and protected comparators, including
      revision-mismatch and `not_assessed` portal regression checks.
- [x] Commit the cohesive feature (`6a080a7`), fast-forward it into the Web
  App source-of-truth `main`, and push it. Remote `origin/main` was verified
  at the same SHA; Railway was not deployed and ENV was not modified.

## Non-goals

- No Bot modification or bridge dependency.
- No provider, payment, wallet, PayOS, PWA private-cache, asset, job, media,
  ASR, translation, TTS or dubbing execution.
- No threshold-derived "AI quality score", per-cue warning list or fake
  success state.
