# Delivery Center record identity contract

## Scope

This presentation-only slice upgrades `/jobs`, `/jobs/{id}` and `/assets` into
an app-first Delivery Center. It changes neither `bot.py`, Core Bridge,
provider execution, wallet/Xu, PayOS, payment webhooks, database schemas nor
download endpoints.

The signed server remains the authority for every record, job status,
ownership decision and delivery decision. The browser only renders redacted
metadata that it has already received from an owner-scoped read.

## Record identities in `/assets`

The generic Assets read intentionally combines bounded sources. The UI must
make their identity visible rather than calling every row a Bot output.

| Public ID namespace | UI label | Safe route | Delivery rule |
| --- | --- | --- | --- |
| `wna:v1:*` | Tệp riêng Web | `/asset-vault` | It is an Asset Vault source/reference, **not** a generated output or waiting delivery. Generic Asset UI never advertises a delivery download for it. |
| `wnj:v1:*` | Output Web-native | `/jobs/{opaque-id}` | It is an owner-scoped Web operation projection. The normal verified delivery guard remains required. |
| Other opaque validated IDs | Delivery canonical | `/jobs/{opaque-id}` | Core Bridge/Bot projection. The normal verified delivery guard remains required. |

The namespace is never decoded and never gains query parameters. A row may
only navigate using its existing opaque identifier. In particular, the UI must
not send `wna:v1:*` to `/jobs/{id}`: that route correctly rejects it, but it
would be a misleading customer journey.

## Delivery truth

`completed`, `output_available`, output metadata and a file download are
separate facts.

1. Job status comes from the owner-scoped canonical read.
2. Output metadata may be reported, but does not grant a file URL.
3. A generic Assets record may render the same-origin download route only when
   both `download_ready === true` and `delivery_ready === true` are literal
   server metadata. The existing server route re-checks signed-session
   ownership, artifact validity and its temporary delivery contract.

The Job Detail lifecycle panel is a compact explanation of those three facts.
It contains no inferred timestamps, provider polling, retry, refund, charge or
browser-generated delivery state. If an exact asset ID does not match the
owner-checked job ID, it says so rather than guessing from feature or time.

## Interaction and accessibility

- Desktop retains semantic data tables. At phone width, the same redacted
  records are rendered as compact cards so required fields and the one safe
  next action are visible without horizontal-table discovery.
- Filter controls preserve the existing in-memory `filter-jobs` and
  `filter-assets` actions. Their result count uses `role="status"` and
  `aria-live="polite"`; no filter is stored in a URL, local storage or a
  canonical record. `Tệp riêng Web` is its own Asset filter and cannot fall
  into the `Chờ delivery` view.
- Refresh gives an `aria-live` status and disables only the existing refresh
  control while its signed read is in flight. A malformed successful payload
  leaves the current list intact and reports a failure; it is not converted
  into a deceptive empty/zero state. Before merging a refresh, each row must
  be an object with a bounded opaque ID and bounded status token, and the list
  stays within the existing 100-record window.
- Controls are at least 40px on desktop and 44px on mobile. Focus remains
  visible and all added motion respects `prefers-reduced-motion`.

## Explicit non-goals

- No Browser/Portal retry, cancel, refund, charge, provider call or payment
  action.
- No merging Asset Vault upload management into generated-output delivery.
- No raw provider URL, storage key, path, hash, account identifier or Bot
  callback state in the client.
- No PWA/private-cache change. Existing private route/API no-cache boundaries
  remain authoritative.
