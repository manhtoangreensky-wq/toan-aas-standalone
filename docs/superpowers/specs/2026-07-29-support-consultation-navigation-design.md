# Support Consultation Navigation Design

## Goal

Allow four frozen, static Bot consultation-detail callbacks to begin a brand-new signed Web Support Desk visit, without transferring Bot state or creating a case.

## Scope

The only reviewed source literals are:

- `support|consult_type|image`
- `support|consult_type|document`
- `support|consult_type|voice`
- `support|consult_type|package`

Each maps only to `/support` in the static migration audit. The existing Web Support Desk remains the product surface; no API, schema, server route, form field, consultation category, query parameter, browser draft, ticket, lead, payment, provider call, job, asset, or delivery behavior changes.

## Source evidence

At frozen Bot SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`, `bot.py:58866-58872` checks the finite `SUPPORT_CONSULT_DETAILS` membership and renders static text and a keyboard. The reviewed entries are defined at `bot.py:38045-38051`. The later `consult_need` and `consult_input` branch begins at `bot.py:58873` and writes Bot pending state, so it stays outside this design. `video` and `frame_video` also stay deferred with the Video menu.

## Architecture

`scripts/migration/audit_bot_to_web.py` owns the private, exact allow-list `SUPPORT_TICKET_FRESH_WEB_NAVIGATION_ACTIONS`. Add four descriptors with the existing fresh `/support` target and opaque Web-only intent labels. The mapping function retains its case-sensitive exact dictionary lookup; unsupported spellings and values continue through the source-review-required path.

The generated migration contract and JSON reports describe navigation only. The existing `/support` route independently requires a signed Web account and still needs explicit Web form submission, CSRF and idempotency before creating a Web-owned case.

## Safety boundaries

- No raw Bot callback, Telegram identity, selected service, pending support state, ticket/lead ID, attachment, command or category reaches the browser.
- No form preselection, case or lead creation happens from the mapping.
- No provider, wallet/Xu, PayOS, payment, refund, job, output, asset or delivery operation is added.
- The mapping is exact and case-sensitive. Suffixes, case variants, `video`, `frame_video`, `consult_need`, `consult_input`, `premium_type`, `bot`, and `bot_type` remain fail-closed.

## Verification

The migration audit test must first prove the four keys are not allowed. After implementation it must prove their exact target, navigation-only status, customer classification, fresh-navigation dispositions and opaque intent. It must also prove every excluded variation remains `SUPPORT_TICKET_SOURCE_REVIEW_REQUIRED`. Regenerate static migration evidence with the frozen Bot baseline, run the focused migration test, Python syntax checks, and `git diff --check`.
