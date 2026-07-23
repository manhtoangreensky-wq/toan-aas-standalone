# Web Consultation Brief Composer — Web-native contract

## Purpose

`/support` includes a compact **Consultation Brief** composer for customers who
want to clarify a Premium, custom-solution, or service question before they
write a normal Web Support Desk request.  It is a preparation surface, not a
lead capture, quote, purchase, ticket or execution surface.

The catalog is informed by the useful topic families in the frozen Telegram
Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4`:

| Frozen Bot topic family | Closed Web catalog group | Web case category only after explicit customer submit |
| --- | --- | --- |
| Premium personal / shop / business / private consultation choices | `premium` | `premium_lead` |
| Custom shop / content / support / internal / other choices | `custom_bot` | `custom_bot_lead` |
| Image / video / image-to-video / document / voice / package consultation choices | `service` | `service_consulting` |

This is a fresh, server-owned Web catalog.  It never accepts the Bot's raw
`support|*` callback, pending conversation state, customer contact prompt,
ticket ID, Telegram message, notification or admin alert.

## Customer flow

```text
signed session
  -> GET catalog (read-only)
  -> customer chooses a closed service + writes safe context
  -> POST compose (CSRF; returns an in-memory draft only)
  -> customer reviews and explicitly confirms local handoff
  -> existing Support form is filled in the browser
  -> customer independently chooses “Tạo yêu cầu”
  -> POST /api/v1/support/cases (existing CSRF/idempotent case write)
```

The handoff never navigates, auto-submits, calls a provider, or creates a
case.  It replaces the normal form fields only after a confirmation message
explains that existing form text will be replaced and that no request has been
created.  The normal Support form remains the single case-write route.

## API contract

```text
GET  /api/v1/support/consultation-brief/catalog
POST /api/v1/support/consultation-brief/compose
```

Both routes require a signed Web account and `WEBAPP_SUPPORT_DESK_ENABLED`.
Compose additionally requires CSRF.  The service ID is one of fifteen exact
catalog IDs; all request models are `extra="forbid"`.

Catalog responses use `status: read_only`; compose responses use `status:
draft`.  Their `data` has all of the following truthful boundaries:

```json
{
  "delivery": "web_view_only",
  "persistence": "none",
  "automation": "none",
  "case_created": false,
  "input_persisted": false
}
```

The catalog has `case_auto_create`, `lead_or_crm_write`,
`external_notification`, `contact_collection`, `quote_or_contract`,
`payment_or_wallet`, `bot_or_telegram`, and `provider_job_or_asset` all set
to `false`.

## Privacy and safety boundary

- The server does not call `ensure_copyfast_schema`, `transaction`,
  `_record_audit`, a Bot bridge, provider, job, asset, CRM, payment, wallet,
  Xu, PayOS, refund or notification adapter for catalog/compose.
- Brief input is length-bounded and uses the existing secret, OTP/CVV,
  card-shaped-number and manual-payment rejection.  The composer additionally
  refuses email addresses, telephone numbers, Telegram handles, and labelled
  Zalo/Telegram/contact details because identity comes from the signed session.
- The compose route has a fixed pre-route rate-limit bucket.  It does not
  weaken the CSRF, session, or normal Support case limits.
- Both canonical compose paths are raw-stream capped at 16 KiB before
  FastAPI/Pydantic reads JSON. An oversized request receives a `413` envelope
  and cannot create a case or persist a draft.
- Catalog, preview, selection, and bounded raw input exist only in signed-page
  memory. Input remains visible after a successful preview so the customer can
  revise it, then is cleared on handoff, catalog refresh/failure, signed-account
  change, feature gate failure, stale response, or route change. None of it is
  placed in localStorage, sessionStorage, URL state, service-worker cache, or a
  Support table.
- The portal validates the closed server shape again before display, compose,
  or handoff.  A click's DOM attributes are never trusted for service/category
  selection.
- A catalog failure guards only this preparation panel; it does not stop the
  normal Support Desk. The customer can explicitly retry the closed catalog in
  place, with no fallback data.

## Verification

Focused tests prove anonymous denial, CSRF, exact closed catalog shape,
secret/payment/contact rejection, no case/message/event/audit row creation,
disabled-flag behavior, stale/session guarding, one explicit handoff, mobile
controls, and the PWA private-route exclusion.  No Telegram, provider, PayOS,
wallet/Xu, job, asset, CRM, or live delivery flow is exercised or claimed.
