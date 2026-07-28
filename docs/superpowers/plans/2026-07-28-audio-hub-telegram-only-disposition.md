# Audio Hub Telegram-Only Disposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the migration inventory disposition for the frozen Bot Audio Hub callback families without turning a Telegram state machine into a browser route or changing `bot.py`.

**Architecture:** The static migration audit classifies every `music_quick|*`, `sfx_quick|*`, `media_quick|*`, and `suggest_music|*` source value and template as `TELEGRAM_ONLY`.  The classification records why the Bot callback cannot cross the boundary and names only fresh, non-executable Web-native equivalents.  It does not add a route, API parameter, provider call, wallet action, job, output, payment, or delivery claim.

**Tech Stack:** Python static audit, generated Markdown/JSON migration evidence, focused pytest contracts.

---

### Task 1: Lock the reviewed boundary in a failing contract

**Files:**
- Modify: `tests/test_migration_audit.py:5053-5330`

- [x] Change the focused Audio Hub contract assertions so exact and opaque callback templates require `target=TELEGRAM_ONLY`, `status=TELEGRAM_ONLY`, and a `TELEGRAM_ONLY` resolution that states a raw Bot callback is never replayed.
- [x] Add assertions that the generated contract names fresh Web-native equivalents only as non-executable alternatives and explicitly says no Web feature or runtime-equivalence claim is gained.
- [x] Run:

  ```powershell
  python -m pytest -q tests/test_migration_audit.py -k audio_hub -p no:cacheprovider
  ```

  Observed before implementation: failed because the audit emitted `*_SOURCE_REVIEW_REQUIRED` and `NEEDS_FEATURE_DISPOSITION`.

### Task 2: Implement the reviewed, non-executable disposition

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py:7276-7365`
- Modify: `scripts/migration/audit_bot_to_web.py:10745-10772`
- Modify: `scripts/migration/audit_bot_to_web.py:11590-11710`
- Modify: `scripts/migration/audit_bot_to_web.py:12355-12540`

- [x] Replace the Audio Hub and suggestion source-review targets with `TELEGRAM_ONLY` for all case variants, suffixes, future values and opaque templates.
- [x] Preserve identity, pending/cache, voice-profile, video-finalization, provider/Xu/Telegram-delivery and keyword-source evidence.
- [x] Keep every raw callback out of route/action fields and out of all browser/API input grammar.
- [x] State that `/media-workspace/music-directions`, `/media-workspace/sfx-cue-sheet`, `/voice-studio`, `/audio/assets`, and `/audio-hub` are fresh Web-native surfaces only; none is an adapter for a raw callback.
- [x] Regenerate migration evidence through the audit's supported command for verification; stage/commit only the focused Audio Hub generated contract/doc hunks and preserve unrelated audit rebaseline reports/docs unstaged.

### Task 3: Verify, review, and prepare one focused PR

**Files:**
- Stage/commit only the focused Audio Hub generated contract/doc hunks; preserve unrelated audit rebaseline reports/docs unstaged for a separate task.

- [x] Run the focused Audio Hub audit contracts and the static audit command used by the repository.
- [x] Inspect the JSON mapping counts: Audio Hub callback families leave the unresolved-feature backlog but do not increase `static_web_surface_coverage_percent` or `workflow_equivalence`.
- [x] Run `git diff --check` and inspect the diff for bot, PayOS, wallet, provider, production configuration, and route changes; all must remain absent.
- [x] Commit a focused branch change after the spec and code-quality reviews approved it.
