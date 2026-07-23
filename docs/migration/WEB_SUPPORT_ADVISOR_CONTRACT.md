# Web Support Advisor — Web-native read-only contract

## Purpose

`/support` includes a small **Support Advisor** before the normal Web Support
Desk composer. A signed customer selects one existing Web case category and
receives a short, reviewed checklist. The checklist helps the customer write
a clearer request; it never submits, updates, routes or promises a case.

This is deliberate progressive disclosure, not a replacement ticket system:

```text
signed Web session -> choose existing category -> GET checklist
  -> customer may choose "use this category" -> focus existing composer
  -> customer independently writes + submits the normal protected case form
```

The final submit remains `POST /api/v1/support/cases`, with its existing
CSRF, owner, validation and idempotency controls. A checklist view has no
CSRF requirement because it is a signed, non-mutating `GET`.

## Bot-reference boundary

The frozen Bot baseline (`b29d0d474974075f4cba963d2c510f49d2d1b3e4`) is
research evidence only. Its `support_v1b.py` persona guard, rule-first
classification and escalation templates explain why this Web surface gives
safe, bounded preparation guidance. It does **not** import Bot source,
execute a Bot classifier, use an optional AI fallback, replay a callback, read
Bot tables, create a Bot ticket or send a Telegram notification.

In particular, the Bot's automatic ticket/reply/notification code remains
outside this contract. A Web checklist is not a support case, not a message,
not a classification result and not an external delivery.

## Closed API

```text
GET /api/v1/support/advisor?category=<one existing Web category>
```

The route requires `require_account` and
`WEBAPP_SUPPORT_DESK_ENABLED=true`. It accepts only the same closed category
vocabulary used by the Web Support Desk:

| Topic | Categories |
| --- | --- |
| Technical | `image_error`, `video_error`, `document_pdf` |
| Billing review | `payment_topup`, `package_combo`, `refund` |
| Product consulting | `feature_request`, `lead_consulting`, `service_consulting`, `premium_lead`, `custom_bot_lead` |
| General | `general_support`, `other` |

Unknown, Bot-style or future unreviewed categories fail closed. If a future
Web category is added without a guide, the endpoint returns `503`; it never
falls back to free text, an AI/provider query or generic advice.

Every successful response uses the standard envelope and has this closed
shape:

```json
{
  "ok": true,
  "status": "read_only",
  "data": {
    "guide": {
      "category": "image_error",
      "topic": "technical",
      "title": "...",
      "summary": "...",
      "checklist": ["...", "...", "..."],
      "handoff": "...",
      "boundaries": {
        "ticket_auto_create": false,
        "notification": false,
        "payment_or_refund": false,
        "provider_or_job_lookup": false,
        "bot_or_telegram": false
      }
    },
    "delivery": "web_view_only",
    "automation": "none"
  }
}
```

The browser validates every field, requires exactly the five `boundaries`
keys to be false, caps title/summary/handoff/checklist lengths, and renders
only three or four checklist items. A malformed, stale, cross-session or
unavailable response is guarded rather than displayed.

## UI and ownership model

The Advisor state is mounted-page memory only. It is cleared on a session or
support-gate reset, is not stored in localStorage, URL parameters, a case
draft or a service-worker cache, and is protected by a request/session/route
epoch before rendering.

The handoff button never trusts a `data-*` category from the DOM. It
revalidates the current in-memory, server-shaped guide; then it selects the
matching existing case-composer category and focuses the subject field. It
does not prefill customer text or call any POST endpoint. Customers retain
control over whether and what they submit.

The Advisor uses the existing Portal design system, semantic labels and
`aria-live` status feedback, 44px controls, visible existing focus behavior,
and one-column mobile flow. It adds no decorative animation or separate
navigation state.

## Explicit non-execution boundary

The route and its browser actions never:

- create, change, assign, close or reply to a case;
- send email, push or Telegram notifications;
- accept or verify payment proof, start/finish PayOS, alter wallet/Xu or
  approve/refuse a refund;
- inspect a provider, job, output, asset, engine or worker;
- import Bot modules, use Telegram identity/callbacks or touch Bot state;
- invoke an AI model/classifier, external network service or automation.

Support Desk text validation remains the only place a customer can create a
Web case, and it continues to reject secret, card, OTP, payment-proof and
manual-payment content.

## Configuration and verification

`WEBAPP_SUPPORT_DESK_ENABLED` remains the sole feature flag. No new secret,
provider credential, worker or payment setting is introduced.

Focused tests prove signed-session and feature-gate behavior, exact closed
guide shape, invalid-category failure, no database/audit/case write, browser
response validation, no DOM-category trust in handoff, no hidden POST/bridge
fallback, private PWA exclusion and responsive/a11y primitives. This contract
makes no live Telegram, provider, payment, job or deployment claim.
