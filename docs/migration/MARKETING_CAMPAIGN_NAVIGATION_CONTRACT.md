# Marketing callbacks → Campaign Planner — fresh Web navigation

## Purpose

The standalone Web App has an account-owned [`Campaign Planner`](CAMPAIGN_PLANNER_BOUNDARY.md)
at `/campaigns`. This contract records the narrow migration disposition for a
finite set of frozen Bot `marketing|…` callbacks: they may open a **fresh**
signed Web Campaign Planner, but they never replay the Telegram conversation.

The capability is exposed to the Web catalog as `campaign_planner`. It is a
navigation-only capability, not a Bot adapter or a claim that a Bot campaign,
publish operation, provider action, job, analytics result, wallet settlement,
PayOS webhook or delivery has executed.

## Reviewed finite actions

These exact literals map to `/campaigns` with
`reviewed_marketing_fresh_web_navigation`:

- Conversation entry/navigation: `marketing|start`,
  `marketing|back_suggestions`, `marketing|refresh`.
- New brief/suggestion UI: `marketing|brief_custom`, `marketing|choice|1`,
  `marketing|choice|2`, `marketing|choice|3`.
- Campaign context choices: `marketing|cskh`, `marketing|kind_custom`,
  `marketing|kind|affiliate`, `marketing|kind|food`,
  `marketing|kind|physical`, `marketing|kind|realestate`,
  `marketing|kind|service`, `marketing|kpi`.
- Bot-local transitions: `marketing|save`, `marketing|schedule`.

For every entry above, the Web starts with an empty, signed-account planner.
It does not receive any Bot suggestion index, custom brief, product kind, KPI,
customer-care context, campaign ID, pending message, selected state, save
receipt, schedule state or Telegram identity.

`marketing|save` and `marketing|schedule` are especially important: opening
the Web Planner does **not** perform the Bot save/schedule. A user may later
create an independent Web plan only through its own CSRF, idempotency,
account-ownership and audit controls. The ordinary Web calendar marker remains
inert; private Web Inbox schedule intents require their separate explicit
opt-in contract.

## Deliberately separate actions

- `marketing|caption` retains the existing content-tool disposition.
- `marketing|select_video` stays on its explicit Video boundary and is not
  promoted by this Campaign batch.
- Any dynamic `marketing|…{*}` template is
  `MARKETING_SOURCE_REVIEW_REQUIRED`. A future opaque value can carry a Bot
  suggestion, campaign identifier, text or state-machine transition and must
  not inherit `/campaigns` from a namespace prefix.

## Authority and privacy boundary

The Planner only owns Web planning metadata under the current signed account:
title, HTTPS destination, platform, objective, inert planning date and
self-review lifecycle. It does not read or mutate Bot campaign rows, Telegram
identity, canonical publishing state, social channel connections, analytics,
providers, jobs, files/assets, wallet/Xu, PayOS, payment signatures, webhooks
or refunds.

All Web Planner writes continue to require server-side signed ownership, CSRF,
bounded idempotency and audit logging. Browser navigation never grants a role,
accepts a Bot ID, restores state from URL/local storage, or bypasses a server
check.

## Verification

Focused migration tests assert the finite allow-list, its public catalog
equivalence, no-state-transfer dispositions and the dynamic-template
fail-closed rule. This contract does not run Bot source, Telegram, provider,
payment or deployment flows.
