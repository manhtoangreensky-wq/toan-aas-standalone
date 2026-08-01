# Customer Partner Readiness Workspace Design

## Context

The Web App has a guarded `/referrals` entry that remains a Bot-companion
surface. It cannot safely create referral links, calculate attribution or
commission, read membership, issue payouts, or change Xu/PayOS state.

The static inventory also retains an unreferenced historical freelance handler.
It is source evidence only, not observed Bot runtime parity. Reusing either
the referral surface or the internal Partner & Lead CRM would blur authority
boundaries and create misleading financial or operational claims.

This design adds one independent, customer-owned Web workspace for preparing a
professional service/partner profile before a separately authorized human
handoff. It is not a public marketplace or a referral system.

## Options considered

1. Expand `/referrals` into a Web affiliate surface.
   This would require canonical attribution, eligibility, ledger, payout and
   abuse-policy authority that the Web App deliberately does not own.
2. Reuse `/crm/leads` or Admin Partner CRM for a customer portfolio.
   Those routes are internal lead-management workflows and must not receive a
   customer-owned service identity or grant cross-account visibility.
3. Add one small owner-scoped Partner Readiness profile per Web account.
   It safely holds authored metadata, immutable versions and an explicit
   non-financial interest receipt without making an external claim.

Option 3 is selected. One account has one bounded working profile, which keeps
the first release focused and avoids a misleading public "portfolio library".

## Scope

- Add a signed customer route `/partner-readiness`.
- Add `/api/v1/partner-readiness/*` for one private profile, history and an
  explicit interest receipt.
- Persist only account-authored professional metadata: service focus,
  capability tags, availability, non-numeric rate-display preference, accepted
  brief types, portfolio summary, collaboration note and a private visibility
  draft.
- Maintain immutable version snapshots, lifecycle events, optimistic revision
  checks, idempotent write receipts and sanitized audit events.
- Expose a Vietnamese-first Portal screen through the existing teal/cyan
  application shell and existing reduced-motion-safe interaction primitives.
- Add a migration contract that documents the authority split and exclusions.

## Explicitly out of scope

- Editing `bot.py`, importing Telegram data, connecting the Bot/Core Bridge or
  presenting this as Bot runtime parity.
- Referral code generation, attribution, commission, membership entitlement,
  payout, escrow, wallet/Xu, PayOS, payment, invoice or ledger activity.
- Public listing, search, discovery, matching, client contact, inbox delivery,
  lead routing, automatic publishing, social connection or notification.
- Provider/model calls, job creation, media output, asset delivery or runtime
  execution.
- Reading, editing or handing data to Admin Partner CRM. A future authorized
  human handoff needs its own reviewed cross-domain contract.

## Authority and data model

The signed Web account is the only owner. Browser input never carries an
account ID, canonical user ID, Telegram ID, referral code, payout identifier
or Admin role. The profile is always selected by the server-side account ID;
there is no client-supplied profile ID and therefore no cross-account lookup
surface.

`web_partner_readiness_profiles`

- `account_id` is the primary owner key; an opaque profile UUID is retained for
  version/event foreign keys only.
- The safe authored fields, `state`, `revision`, timestamps and `archived_at`
  are stored directly, never as external identities, URLs, prices or contacts.
- State is one of `draft`, `review`, `submitted`, `archived`. `review` means
  the customer has marked the profile ready for self-review; it never means
  staff approval. `submitted` means only that a local interest receipt exists.

`web_partner_readiness_versions`

- One immutable sanitized JSON snapshot per profile revision, unique per
  `(profile_id, revision)`. Snapshots remain private to the owning account.

`web_partner_readiness_events`

- Narrow event metadata (`profile_created`, `profile_updated`,
  `review_requested`, `interest_submitted`, `profile_archived`,
  `profile_restored`) with no free-text audit detail.

`web_partner_readiness_interest_submissions`

- One local, profile-version-pinned receipt per explicit submission. It records
  `submitted` only; it contains no recipient, contact destination, price,
  referral, attribution, payment or approval state.

All tables are additive in `ensure_copyfast_schema()` and use only foreign keys
to `web_accounts` and the new local profile table. No destructive migration is
permitted.

## API and lifecycle

| Endpoint | Authority | Behavior |
| --- | --- | --- |
| `GET /policy` | signed owner | Read the explicit Web-native boundary and closed choices. |
| `GET /profile` | signed owner | Read the one private profile or a safe empty projection. |
| `GET /profile/history` | signed owner | Read bounded versions and events for that account only. |
| `PATCH /profile` | signed owner + CSRF | Create/update `draft`, version and audit event. |
| `POST /profile/request-review` | signed owner + CSRF | `draft -> review`; no staff action. |
| `POST /profile/interest` | signed owner + CSRF | `review -> submitted`, then create one local receipt. |
| `POST /profile/archive` | signed owner + CSRF | Archive without deleting history. |
| `POST /profile/restore` | signed owner + CSRF | Restore only to `draft`, so the customer must review again. |

All writes require an opaque idempotency key and `expected_revision`. The
server fingerprints the normalized request and returns the original success
receipt only for an exact replay; a reused key with different input returns
409. Stale revisions and invalid lifecycle transitions return truthful guarded
or conflict envelopes and do not create an event/version/submission.

Permitted transitions are `draft -> review`, `review -> submitted`, any
non-archived state to `archived`, and `archived -> draft`. Updating a
`review` profile returns it to `draft` because its self-review must be repeated.

## Security and privacy

- Strict Pydantic models reject extra fields, invalid enum values, duplicate
  tags and unsafe/secret/payment/contact-like text.
- Every mutable API uses `require_csrf`; every read uses `require_account`.
- The shared API rate middleware gets fixed read, profile-write and interest
  buckets before database work. Existing private responses retain
  `Cache-Control: no-store`.
- The feature guard `WEBAPP_PARTNER_READINESS_ENABLED` defaults to enabled for
  this Web-native metadata-only workspace; disabled mode returns an honest
  503 without a partial write.
- The private page/API prefixes are explicitly excluded from service-worker
  caching. No browser persistence or query-string propagation is added.

## Portal experience

The page follows the existing TOAN AAS application design system rather than a
landing/portfolio site: light cyan canvas, white working surfaces, deep-teal
desktop rail, dark-teal actions, sky context and compact aligned forms. The
screen has one deliberate workflow:

1. Draft a private service profile.
2. Fill capability, availability and briefing preferences.
3. Self-review a versioned private record.
4. Explicitly submit an interest receipt, which explains that it has not
   contacted, matched or enrolled the customer.

The screen shows the editor, lifecycle controls, history and local activity.
Controls are semantic buttons/forms with existing focus styles, 44px mobile
targets and transform/opacity-only motion already provided by `portal-motion`.
No generated raster asset is needed: this is a private operational workspace,
not a public portfolio or marketing page.

## Verification

- Anonymous read/write, missing or invalid CSRF, malformed/oversized/extra
  input, disabled feature, rate limiting, stale revision, invalid state
  transition, idempotency replay/collision and archive/restore behaviors are
  covered by focused API tests.
- Tests assert the response boundary contains no Bot, provider, job,
  wallet/Xu, PayOS, referral, payout, public-listing or Admin CRM claim.
- Portal contract tests prove signed hydration, no localStorage, clear
  submitted-state wording, private PWA exclusion and existing
  responsive/reduced-motion shell behavior.
- The migration contract and registry preserve `/referrals` as its separate
  guarded Bot-companion surface.
