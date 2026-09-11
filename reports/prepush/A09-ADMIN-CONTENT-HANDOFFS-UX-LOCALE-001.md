# A09 — Admin Content Handoffs UX/locale

Spec: `A09-ADMIN-CONTENT-HANDOFFS-UX-LOCALE`
Route: `/admin/content-handoffs`
Base: `4f83a81c0e60a5ccc1a8aa5f896abb45320c295b`

## User-visible result

The staff queue is task-first: one localized page heading, a short queue summary,
status filter, records and their permitted decision forms. Process, role and
safety details are preserved in one disclosure that starts closed. Labels,
statuses, decisions, pagination, empty and guarded states use a VI/EN/ZH
catalogue; customer-authored title and purpose remain unchanged across locales.

The light theme no longer renders form labels nearly white. The route uses
semantic teal/cyan tokens, one-column cards on mobile, 44px controls and a 48px
keyboard disclosure. No customer Content Handoff renderer or backend contract
was changed.

## Measured evidence

- Browser: `20` states = VI/EN × light/dark × 1440/1024/768/390/360.
- All browser assertions true: identity, locale purity, dynamic record visible,
  filter before records, guidance closed, overflow/clipping/touch violations,
  framework overlay, relevant events and staff write requests all `0`.
- Minimum sampled contrast including filter and decision labels: `7.26:1`.
- Keyboard Enter opened and closed the process disclosure.
- One disposable local record `review/revision=2`; no decision submitted.
- Report SHA-256:
  `04AC45A9948A0F7AEBE723ECD60776DE79B6FECE498BCCA51EF4926196FCCB1E`.

External evidence (not committed to the public repository):
`evidence/a09-admin-content-handoffs-20260911/browser/a09-content-handoffs-browser-qa.json`.

## Automated verification

- Focused backend/customer/staff/workboard/stale/i18n/Tester suite:
  `95 passed`, `1` Windows-only POSIX permission test deselected, `1` existing
  Pydantic warning.
- Protected exact base/candidate comparator: both `69 passed / 2 failed`; the
  two IDs are the same pre-existing CSS-tail failures; `NEW_FAILURES=0`.
- Node syntax and `git diff --check`: exit `0`.

## Authority and limitations

Transition values (`approved_for_handoff`, `blocked`, `handed_off`), record ID,
revision, cursor, server role, CSRF, idempotency and audit checks are preserved.
No production record was created or reviewed. This is local rendered acceptance,
not deployment or signed production LIVE evidence.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
ENV_MUTATIONS=0
STAFF_REVIEW_WRITES=0
LIVE_PASS=NOT_TESTED
