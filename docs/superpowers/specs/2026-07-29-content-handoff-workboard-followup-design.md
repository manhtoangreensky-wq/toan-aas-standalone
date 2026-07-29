# Content Handoff to Workboard Follow-up Design

## Goal

Let the signed owner of an eligible Web-native Content Handoff create one private Workboard follow-up for the current handoff revision. The card is an owner-managed coordination record, never evidence that staff, a provider, Bot, payment, or delivery operation ran.

## Selected approach

The feature uses a dedicated `POST /api/v1/workboard/content-handoff-followups` endpoint and an additive relation table owned by the Workboard module. A generic Workboard reference is deliberately not extended: generic references would let callers attach a handoff without the exact owner, lifecycle, confirmation, and revision checks required here.

The rejected alternatives are:

- A navigation-only link, which cannot prevent duplicate or stale follow-ups.
- A generic `content_handoff` reference type, which would broaden a sensitive source into ordinary Workboard creation and make source-boundary enforcement less clear.

## Data model

`copyfast_workboard._ensure_schema()` will create `web_content_handoff_workboard_followups` with:

- `id`, `account_id`, `handoff_id`, `handoff_revision`, `workboard_item_id`.
- `link_state` constrained to `active` or `superseded`.
- timestamps for creation, update, and supersession.
- a unique `(handoff_id, handoff_revision)` constraint and a unique `workboard_item_id` constraint.

The relation stores identifiers and revision only. It never stores the Handoff purpose, staff note, recipient, asset paths, external URLs, source references, Bot identity, provider handles, payment values, or delivery claims.

## Request and authorization contract

The endpoint accepts a closed Pydantic request model:

- `handoff_id`, `expected_handoff_revision`, `title`, `checklist`, `priority`, `due_at`, `confirm`, and `idempotency_key`.
- `extra="forbid"`; request fields such as `purpose`, `staff_note`, `recipient`, `references`, `asset_path`, URL, payment, provider, and Bot values are rejected.

It requires the existing signed `require_account` and `require_csrf` dependencies. The authenticated account must own the source Handoff. A staff role does not grant authority to create a follow-up for another customer.

The source Handoff must have `record_state=active`, an exact matching revision, and `handoff_status` equal to `approved_for_handoff` or `handed_off`. A stale revision, blocked handoff, archived handoff, foreign ID, missing record, missing confirmation, or idempotency-key collision is guarded or rejected without creating a card.

## Transaction and lifecycle

The endpoint uses the existing Workboard idempotency ledger. In one write transaction it validates the source, creates a normal Web-owned Workboard item and owner-provided checklist, writes its Workboard version/event/audit entries, then writes the unique relation. The unique database constraint and existing idempotency fingerprint make retry and concurrent duplicate attempts safe.

The source only contributes `id`, `revision`, current lifecycle state, and eligibility. It does not prefill the card. The owner supplies the title and checklist through Workboard validation; a card can be manually edited and progressed through ordinary Workboard rules after creation.

When the source is later archived, blocked, or has a different revision, reads reconcile the relation to `superseded`. Reconciliation never edits, closes, completes, or deletes the Workboard item. A new owner-confirmed follow-up may be created only for a newly eligible revision.

## Read model and cache boundary

Workboard list/detail responses expose a minimal `content_handoff_followup` object only for the owner: Handoff ID, Handoff revision, and link state. The original Content Handoff body, staff note, and references are not exposed through Workboard.

The route remains inside `/api/v1/workboard/`, so the existing signed-session, body-size, CSRF, rate-limit, no-store/private-cache, and PWA private-data controls apply. The endpoint adds no Bot import, bridge call, provider call, job creation, wallet mutation, PayOS/webhook path, file delivery, notification, or external network call.

## Test contract

Focused tests must prove:

- signed-owner and CSRF enforcement; foreign owner and staff isolation;
- lifecycle/status and stale-revision guards;
- confirmation and strict sensitive-input rejection;
- duplicate idempotency replay and unique-relation race safety;
- `superseded` source-link behavior without mutating the card;
- owner-only minimal read model and no private PWA cache;
- absence of Bot/bridge/provider/payment/webhook imports or calls.

The feature is complete only after these tests, `py_compile`, `git diff --check`, independent spec review, code-quality review, PR CI, and merge all pass.
