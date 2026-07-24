# Partner & Lead CRM — Web-native contract

## Scope

`copyfast_partner_crm.py` is an isolated, signed-account CRM workspace for
draft partnership/customer leads. It is intentionally independent from the
Telegram Bot, historical affiliate/ERP prototypes, payment flows and social
connections. It is mounted by `app.py` and rendered by the portal only through
the bounded Web-native routes described below.

The feature is controlled by `WEBAPP_PARTNER_CRM_ENABLED` (default `true` for
this metadata-only workspace). Disabling it returns a guarded `503` before a
lead read or write.

## Routes

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/partner-crm/policy` | signed account | States the exact CRM and manager-directory boundary. |
| `GET /api/v1/partner-crm/consultations/catalog` | signed account | Returns a closed customer consultation catalog; no record is created. |
| `POST /api/v1/partner-crm/consultations/preview` | signed + CSRF | Validates a consultation request in memory only; no CRM write, audit or receipt is created. |
| `POST /api/v1/partner-crm/consultations` | signed + CSRF | Creates one owner-scoped `draft` only after storage-only consent, confirmation and idempotency validation. |
| `GET /api/v1/partner-crm/summary` | signed account | Owner-scoped stage counts. |
| `GET /api/v1/partner-crm/leads` | signed account | Owner-scoped lead list and search. |
| `POST /api/v1/partner-crm/leads` | signed + CSRF | Creates a `draft` lead. |
| `GET /api/v1/partner-crm/leads/{id}` | signed account | Owner-scoped lead detail, notes and activity timeline. |
| `PATCH /api/v1/partner-crm/leads/{id}` | signed + CSRF | Revisioned replacement of bounded metadata/tags. |
| `POST /api/v1/partner-crm/leads/{id}/stage` | signed + CSRF | Validated pipeline transition or archive/restore. |
| `POST /api/v1/partner-crm/leads/{id}/consent` | signed + CSRF | Records consent status/note only; never contacts a person. |
| `POST /api/v1/partner-crm/leads/{id}/notes` | signed + CSRF | Adds a private activity note and increments lead revision. |
| `GET /api/v1/partner-crm/manager/leads` | signed Web admin | Redacted, cross-account, read-only pipeline directory. |

All writes require a bounded idempotency key and `expected_revision` where an
existing lead is changed. The replay receipt contains only opaque lead/note
IDs, revision and stage; no contact email, lead name, notes or opportunity
text is retained in `web_idempotency`. Audit records store action, target and
safe metadata only.

## Data ownership

The router lazily creates only these additive Web-owned tables:

- `web_partner_crm_leads`
- `web_partner_crm_notes`
- `web_partner_crm_events`

Every row is bound to `web_accounts.id` via `account_id`. Detail queries,
updates, consent, notes and normal lists always filter by that account ID. A
foreign lead deliberately appears as the same guarded not-found result rather
than leaking whether it exists.

Pipeline stages are `draft`, `qualified`, `review`, `proposal`, `won`, `lost`
and `archived`. Invalid jumps are rejected. An archived lead can only return
to `draft`; no operation silently restores a commercial status.

## Manager directory

The manager directory is deliberately weaker than a future canonical-live
Admin ERP boundary and is read-only. It requires the Web server-side `admin`
role from the signed session and returns only anonymous pipeline metadata:
lead kind, stage, consent state, revision and timestamps. It excludes lead
IDs, owner IDs/display names, contact email, lead name, organization,
opportunity text, source detail, free-form tags, consent note, activity notes
and every mutation route.

No Core Bridge/Bot lookup is used to turn a cached session role into a
canonical-live role. If operations later require that stronger guarantee, a
separate explicitly approved canonical-admin integration must be designed;
this CRM module must not be widened implicitly.

## Explicit non-goals

The CRM does not:

- calculate referrals, commissions, attribution, payouts or a ledger;
- change Xu, package, membership, promotion, payment, refund or PayOS state;
- send email, Telegram, SMS, notifications, webhooks or CRM automations;
- fetch a URL, call a social network/provider, publish content or create a job;
- import Bot state or the historical affiliate/ERP prototype modules.

Every response carries an explicit boundary with these side effects set to
`false`, so a Web UI cannot represent stored CRM metadata as a completed
commercial action.

## Customer consultation intake

`/crm/consultations/new` is a dedicated customer route. It does **not** reuse
the generic `/crm/leads/new` payload, and it is not a handoff from the
non-persistent Support Consultation Brief.

The flow is deliberately one-way:

1. A signed account reads the closed server-owned catalog.
2. It sends only `service_id`, `request_title` and `need_summary` to a
   CSRF-protected preview route. Preview is non-persistent and returns
   `awaiting_confirm`.
3. The account separately submits `consent_to_store=true`,
   `confirm_create=true`, and an idempotency key to create a private draft.

The browser cannot set CRM stage, source, tags, lead kind, consent state,
contact address or organization. On confirmation the server pins:

| Field | Server-owned value |
| --- | --- |
| `lead_kind` | `customer` |
| `source_kind` | `inbound` |
| `stage` | `draft` |
| `contact_email` | empty |
| `tags` | `web-consultation` and the closed service ID |
| `consent_status` | `documented` |
| `consent_note` | storage of this Web CRM draft only; never contact consent |

The signed account is the ownership boundary; free text rejects email, phone,
Zalo, Telegram handles, secrets/tokens, OTP/CVV/card-like numbers and markup.
The response explicitly states `intake_consent_scope=crm_draft_storage_only`
and `outbound_contact_authorized=false`. It does not authorize email,
Telegram, Zalo, SMS, marketing, quote, contract, provider, job, wallet,
payment, notification or Support-case action.

Only the server-owned service ID/version and opaque lead ID/revision/stage are
kept in the replay receipt. Request title and summary never enter the CRM
idempotency receipt or audit detail. The exact preview and confirm paths,
including trailing-slash variants, have fixed pre-DB rate buckets.

## Focused verification

`tests/test_copyfast_partner_crm.py` covers signed-session/CSRF, strict schema
validation, idempotency replay/collision/redaction, owner-scoped CRUD,
tags/consent/notes/pipeline revision rules, archive behavior, redacted manager
directory behavior, disabled mode and static no-Bot/no-provider/no-money
imports.
