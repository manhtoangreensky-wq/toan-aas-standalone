# Partner Readiness Workspace contract

## Purpose and authority

`/partner-readiness` is a private, signed-account Web workspace for preparing
one professional collaboration profile. It is Web-native preparation metadata,
not an implementation claim for a Bot freelance, referral, affiliate, CRM or
marketplace runtime.

The server derives the owner exclusively from the signed Web session. Browser
input never carries an account ID, canonical user ID, Telegram ID, role,
profile ID, referral code, payout identity, recipient or contact destination.
There is no public profile URL, search/discovery endpoint, Admin ERP route or
Partner CRM projection for this feature. `/referrals` remains its separate,
guarded Bot-companion surface.

## Customer route and API

The one customer page is `/partner-readiness`. It is intentionally absent from
the mobile dock and has no `/admin/partner-readiness` counterpart.

| Endpoint | Access | Behaviour |
| --- | --- | --- |
| `GET /api/v1/partner-readiness/policy` | Signed owner | Returns closed choices and the explicit Web-only boundary. |
| `GET /api/v1/partner-readiness/profile` | Signed owner | Returns the one private profile or a safe empty result. |
| `GET /api/v1/partner-readiness/profile/history` | Signed owner | Returns bounded immutable versions and narrow events for that owner. |
| `PATCH /api/v1/partner-readiness/profile` | Signed owner + CSRF | Creates or updates the profile with revision and idempotency checks. |
| `POST /api/v1/partner-readiness/profile/request-review` | Signed owner + CSRF | Moves `draft` to customer self-review. |
| `POST /api/v1/partner-readiness/profile/interest` | Signed owner + CSRF | Moves `review` to `submitted` and writes one local receipt. |
| `POST /api/v1/partner-readiness/profile/archive` | Signed owner + CSRF | Archives a non-archived profile without deleting history. |
| `POST /api/v1/partner-readiness/profile/restore` | Signed owner + CSRF | Restores an archived profile to `draft`. |

Every response preserves the normal envelope and a truthful boundary. In
particular, an interest receipt means only: “Đã ghi nhận quan tâm trong Web
App; chưa có duyệt, ghép khách, liên hệ, referral, hoa hồng, thanh toán hoặc
payout.” It is not staff approval or an external handoff.

## Data and lifecycle

The additive local schema is created by `ensure_copyfast_schema()`:

- `web_partner_readiness_profiles` — one owner-scoped profile, current state,
  optimistic revision and timestamps.
- `web_partner_readiness_versions` — immutable sanitized snapshot per revision.
- `web_partner_readiness_events` — narrow lifecycle event metadata only.
- `web_partner_readiness_interest_submissions` — one local,
  profile-version-pinned `submitted` receipt.

States are `draft`, `review`, `submitted` and `archived`. Valid transitions
are `draft → review`, `review → submitted`, any non-archived state →
`archived`, and `archived → draft`. Editing a `review` profile deliberately
returns it to `draft`, so the owner must self-review the changed revision.

All writes include `expected_revision` and a 12–160 character idempotency key.
The server fingerprints normalized input, replays only an exact prior receipt,
rejects a changed reuse, and uses a conditional revision update to prevent a
lost update. A stale or invalid transition leaves profile, version, event and
interest receipt unchanged. Local audit entries carry only state/revision
metadata, never authored profile text.

## Privacy, safety and runtime limits

`WEBAPP_PARTNER_READINESS_ENABLED` controls availability and defaults to the
safe enabled state for this metadata-only workspace. Disabled mode returns an
honest `503` before a partial write. The raw request guard applies a compact
body limit before model parsing; responses retain `Cache-Control: no-store,
private`. The shared rate middleware separates reads (120/min), profile writes
(30/min) and interest submissions (12/min).

Models are strict (`extra="forbid"`) and use closed capability/brief/state
vocabularies. Text is normalized and rejects controls, markup, URLs, handles,
contact patterns, secrets/tokens, OTP/card/payment material, referral terms,
staff identity and numeric amount patterns. Histories are bounded to prevent
an unbounded private response.

The Portal keeps policy/profile/history in page memory only, fences delayed
responses across account/session/route changes, and re-reads server data after
an acknowledged write. It does not use URL query values, `localStorage`,
`sessionStorage`, generic CRM hydration or a browser-derived owner. The route
and `/api/v1/partner-readiness/` prefix are excluded from Service Worker cache.

## Explicit exclusions

This contract does **not** call or create any of the following:

- Bot, Telegram identity, Core Bridge, provider/model request, job, media
  output, asset delivery, notification or external execution.
- Wallet/Xu, PayOS, invoice, payment, charge, refund, ledger, commission,
  attribution, referral, affiliate code, payout or recipient.
- Public listing, portfolio discovery, matching, lead routing, contact,
  inbox, CRM record, staff approval or cross-account visibility.

An authorized human handoff, if it is ever required, needs a separate reviewed
cross-domain contract. This workspace must never silently grow into that
handoff.

## Presentation rule

The page is a compact signed application workflow: one aligned editor, one
state/action rail and two bounded server-owned timelines. It uses existing
teal/cyan `--portal-*` tokens, visible focus, 44px mobile controls and
reduced-motion-safe opacity/transform enhancement only. It is not a public
portfolio, lead-magnet form or marketing card grid.
