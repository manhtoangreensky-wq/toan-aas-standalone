# Support Resolution Feedback Design

## Goal

Let the owner of a terminal Web Support Desk case record one concise service-quality assessment for its current terminal revision. The assessment must be private to the signed Web application, safe to aggregate for Customer Care managers, and must never turn into a Bot ticket, message, payment/refund operation, provider call, job action, external notification, or automatic remediation.

## Context and source boundary

`copyfast_support.py` already owns Web-native cases, state/revision transitions, signed owner reads, CSRF-protected writes, idempotency receipts, staff roles, and audit events. The old `customer_api.py` feedback endpoint accepts a browser-provided user identifier and is therefore explicitly out of scope. The frozen Telegram Bot is reference-only and is not modified by this feature.

The reviewed customer states are `resolved` and `closed`. A customer may submit one assessment for the exact terminal case revision currently returned by the server. If the case is reopened and later reaches another terminal revision, that later revision is independently eligible. Feedback does not itself change the case state or revision.

## Options considered

1. Reuse the legacy generic feedback endpoint. Rejected: it accepts browser identity and does not provide owner/revision or Support Desk guarantees.
2. Store feedback columns directly on `web_support_cases`. Rejected: this collapses a revision-bound assessment into mutable lifecycle data and cannot safely preserve multiple terminal cycles.
3. Add a dedicated Web-native relation table keyed by `(case_id, terminal_revision)`. Selected: it preserves immutable terminal-revision ownership, supports idempotent receipts, and keeps aggregate reporting separate from customer content.

## Architecture

### Persistence

Add `web_support_case_resolution_feedback` through `ensure_copyfast_schema()` with:

- a UUID primary key;
- signed owner `account_id`;
- `case_id` and immutable `terminal_revision`;
- `terminal_state` limited to `resolved` or `closed`;
- closed numeric `rating` range 1–5;
- optional sanitized comment no longer than 600 characters;
- `created_at`; and
- `UNIQUE(case_id, terminal_revision)` plus owner/time and terminal-state indexes.

The table does not store email, Telegram IDs, payment evidence, provider details, Bot state, raw audit payloads, or any browser-selected owner/admin identity.

### Customer API

The module exposes:

- `POST /api/v1/support/cases/{case_id}/resolution-feedback`
- `GET /api/v1/support/admin/care/resolution-feedback-summary`

The POST route requires `WEBAPP_SUPPORT_DESK_ENABLED`, a signed account, CSRF, explicit `confirm: true`, a UUID case id, exact `expected_revision`, a strict Pydantic payload, and a valid idempotency key. It reads the case using `case_id` **and** server session account id, rejects a missing/foreign case without disclosure, rejects non-terminal states, rejects stale revisions, and inserts one row in the existing transaction/idempotency mechanism. The response returns only the safe feedback receipt (id, rating, terminal revision/state, submitted time); comments are never copied into generic events or idempotency response data.

The route is placed under the existing support write pre-DB rate family but receives a dedicated fixed `support-resolution-feedback-write` scope and a compact raw-body cap. This prevents UUID/path variations from creating unbounded rate buckets and limits malformed input before Pydantic/SQLite work. It does not weaken the router's own CSRF, ownership, revision, idempotency, and uniqueness gates.

The admin GET route requires the protected Web Customer Care manager role. It returns only an aggregate for a bounded optional `days` window: total ratings, rating histogram, average when there are ratings, and count of comments. It returns no case IDs, account IDs, names, emails, timestamps, raw comments, payment metadata, or Bot/external information. A zero count yields `average_rating: null`, not a fake score.

### Portal contract and UX

The existing customer case-detail hydration receives a narrow optional `resolution_feedback` object in the owner-safe case projection. The Portal accepts it only if its case id, revision, terminal state, rating and timestamp satisfy strict local guards. The detail renderer shows a compact, semantic feedback card only when the current state is terminal:

- if there is no receipt for the current terminal revision: an accessible 1–5 rating radio group, optional comment, confirmation checkbox, and a single explicit submit action;
- if a receipt exists: a non-editable confirmation state containing the rating and submitted timestamp;
- if the case is non-terminal, stale, unauthenticated, or the feature is guarded: no enabled feedback write action.

The form uses the shared teal–sky light-surface design system: existing `portal-card`, `portal-form`, semantic labels, 44px mobile controls, visible focus states, status text in addition to color, and the existing confirmation modal/toast. It introduces no hero, landing treatment, UI storage, fake score, animation dependency, or raw style colors. The staff Support Desk view adds only a compact Customer Care Quality aggregate panel for managers; operators see neither customer comments nor manager-only aggregate data.

### Security and privacy guarantees

- Owner checks occur in the SQL selector; browser-provided account/role/id fields are rejected by strict models.
- A CSRF token, confirmation, expected revision, idempotency key, `UNIQUE(case_id, terminal_revision)`, and transaction guard protect every write.
- Retries with the same idempotency key and unchanged request return the original safe receipt; reusing a key with different content remains guarded by the existing fingerprint mechanism.
- Sensitive-content validation reuses the Support Desk sanitizer for comments. Secret, credential, OTP/CVV, card, manual payment, TXID, bank, QR, and control-character content is rejected before persistence.
- The feedback write never increments case revision, changes case state, emits a customer-visible Support event, starts a task, or creates a notification. It records one narrow audit action without raw comment content.
- The private API remains outside PWA cache paths. No localStorage/sessionStorage or browser cache becomes a feedback authority.

## Non-goals

- No Telegram/Bot change or state synchronization.
- No PayOS, wallet/Xu, refund, manual top-up, webhook, provider, job, asset, email, push, SMS, or external support action.
- No public testimonials, staff-facing comments, AI sentiment analysis, auto-close/reopen, case scoring, or automated escalation.
- No Video menu or LocalVideoStudio work.

## Acceptance criteria

1. A signed owner can submit exactly one confirmed 1–5 assessment for the current `resolved`/`closed` revision and receives a safe receipt.
2. Cross-owner access, non-terminal cases, stale revisions, duplicate terminal feedback, missing confirmation, malformed input, sensitive comments, invalid CSRF, maintenance flag, and idempotency mismatch all fail closed and write no feedback row.
3. Reopened/re-resolved cases can receive a separate assessment only for their new terminal revision.
4. Customer GET/detail responses are owner scoped and do not disclose staff data; manager summary contains only bounded aggregate data; operator access is forbidden.
5. Portal client validates server projection, shows an accessible confirmation flow, does not store comments locally, and refreshes the verified case state after success.
6. Focused tests, syntax checks, static cache/boundary contracts, code review, CI, and merge all pass without a Bot, provider, payment, or live service call.
