# Workboard Task Terminal Callback Catalog Design

## Intent

Close only the frozen Bot `pipe|*` and `task|*` literals whose source
handlers are proven to require Telegram-admin identity plus an opaque Bot
production job/task identifier.  The standalone Web Workboard remains a
separate signed, Web-native product and never receives those identifiers,
state values or handoff prompts.

The finite lower-case templates observed in the frozen baseline are:

- `pipe|stage|voice|{*}`, `pipe|stage|edit|{*}`,
  `pipe|stage|review|{*}`, `pipe|stage|publish|{*}` and
  `pipe|stage|script|{*}`;
- `pipe|status|ready|{*}`, `pipe|status|published|{*}` and
  `pipe|status|blocked|{*}`;
- `task|status|ready|{*}`, `task|status|blocked|{*}` and
  `task|handoff|x|{*}`.

## Decision

Use a finite raw, case-sensitive terminal catalog in the static audit.
Every listed literal and source template maps only to an envelope whose
`target` and `status` are `TELEGRAM_ONLY`.  The mapping records the Bot-admin,
canonical production-state and opaque-identifier boundaries, with
`NO_RUNTIME_CLAIM`.

This is a safety disposition, not browser access to the Bot production system.
It creates no route, browser action, Web Workboard item, API request, provider
call, job/output delivery, payment/refund/ledger mutation or external effect.

## Exactness and drift handling

Raw values must be matched exactly.  A concrete terminal callback has exactly
four segments and a final **ASCII decimal** identifier; upper-case/case-mixed,
whitespace, Unicode/non-numeric identifiers, suffix, missing-token, arbitrary
stage/status and future `pipe|*` or `task|*` values remain
`WORKBOARD_TASK_SOURCE_REVIEW_REQUIRED`.  They receive no route, launch
metadata or Web action.

The generic source-review boundary continues to cover templates that are not
one of the finite catalog entries.  This keeps Bot drift visible while making
the proven Telegram-only controls explicit in the parity matrix.

## Evidence and verification

The static audit must regenerate from frozen Bot baseline
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`, without importing or starting
the Bot.  Tests prove the finite catalog, terminal envelope, exactness,
template handling and remaining source-review drift.  The existing Web
Workboard runtime is a regression-only surface and is not modified.

## Non-goals

Do not edit `bot.py`, create a Bot bridge, alter the Web Workboard runtime,
enable flags, call Telegram, provider, PayOS, wallet, jobs or Railway, or
touch Video/LocalVideoStudio/motion-kit/OpenMontage files.
