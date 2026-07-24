# Web Consultation Request → CRM lead draft

## Purpose

This is a Web-native customer intake at `/crm/consultations/new`. It lets a
signed account prepare a limited consultation request, preview the exact
server validation, then explicitly create a private CRM **draft**. It is not
the generic CRM form and is intentionally separate from Support's
non-persistent Consultation Brief.

The module borrows only the useful high-level topics that users previously
encountered through Telegram. It neither imports nor changes `bot.py`, and it
does not replay a Bot callback, conversation, identity, state or delivery.

## Boundary

| Area | Contract |
| --- | --- |
| Identity | Signed Web account only; record ownership is server-side. |
| Catalog | 15 closed server-owned service choices; no quote, price, contact channel or provider action. |
| Preview | CSRF-protected and non-persistent; no table row, audit record or idempotency receipt. |
| Confirmation | Requires `consent_to_store=true`, `confirm_create=true`, CSRF and a bounded idempotency key. |
| Storage | Additive `web_partner_crm_*` tables only; no Bot, PayOS, wallet, job or provider table. |
| Contact | No free-text email, phone, Zalo or Telegram handle. Storage-only consent is explicitly not consent to contact. |
| Output | Successful confirmation returns only an opaque owner lead receipt; it does not claim delivery or commercial progress. |

The response boundary always sets Bot/bridge/provider/payment/wallet/job/
notification/contact/publish/referral side effects to `false`.

## Server projection

The browser may submit only a closed service ID, a title and a need summary.
On confirmed storage, the server derives all CRM metadata:

```text
lead_kind       customer
source_kind     inbound
source_label    Yêu cầu tư vấn Web · <server catalog title>
contact_email   ""
tags            ["web-consultation", <server service ID>]
consent_status  documented
stage           draft
```

`consent_status=documented` means only that the account confirmed storage of
this private Web draft. `outbound_contact_authorized` remains `false`.

## User flow

```text
catalog → safe request input → server preview (awaiting_confirm)
        → explicit storage-only checkbox + native confirmation
        → idempotent private lead draft → optional owner lead link
```

The portal keeps unfinished text only in route memory. It does not put the
request in local storage, session storage or a URL, and it never redirects the
user automatically after confirmation.

## Validation and operational guards

- `request_title`: 4–120 characters.
- `need_summary`: 12–1,000 characters.
- Inputs reject control characters, markup, secrets/tokens, OTP/CVV/card-like
  values and direct contact details.
- Generic CRM fields, Bot callback/session state and browser-supplied source,
  stage, tag, contact or consent metadata are rejected by the strict schema.
- Confirmations use a per-account idempotency scope. Same key/same request
  replays the opaque receipt; a changed request returns conflict.
- Preview and confirmation use fixed pre-DB rate buckets. The 16 KiB CRM
  raw-body limit also covers canonical and trailing-slash paths.

## Explicit non-goals

This is not a support case, manual-payment request, account-link mechanism,
CRM automation, sales inbox, email/SMS/Telegram sender, quote/contract flow,
provider call, background job, output/asset delivery or admin cross-account
action. Those boundaries require separate reviewed modules.
