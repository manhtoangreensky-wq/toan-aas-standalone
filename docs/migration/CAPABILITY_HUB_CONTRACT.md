# Capability Hub contract

## Purpose

`/features` is the product-facing map for converting the Telegram Bot into a
full Web/App. It groups the static Bot inventory into product domains instead
of creating hundreds of duplicate command pages.

The Hub is useful for sequencing migration work. It is not a claim that a
provider, payment, job, output, download or Bot bridge is live.

## Data boundary

- Source: the already-sanitized, static-only
  `reports/migration/parity_gap.json` audit artifact.
- Runtime reader: `copyfast_capability_hub.py` reads that local artifact only.
  It never imports `bot.py`, reads environment values, opens the Bot database,
  calls a provider, or makes a network request.
- Browser payload: only aggregate counts, fixed family labels/descriptions and
  fixed same-origin destination routes.
- The payload deliberately excludes raw commands, callback tokens/patterns,
  handlers, source file paths/lines, staff/admin actions, provider names,
  secrets, identifiers and customer data.

## Product semantics

Each family shows only static migration counts:

| Label | Meaning |
| --- | --- |
| `lệnh người dùng` | Bot commands statically classified into the family. |
| `đã map route` | A customer Web route was statically observed. It does not prove an engine works. |
| `đang guarded` | A signed/guarded compatibility route exists but must not imply feature execution. |
| `chỉ Bot` | The capability intentionally remains Telegram-only pending a separate product and security decision. |

Admin, worker, backup, provider, wallet/PayOS and callback implementation
detail never becomes a customer button through this Hub. Admin ERP has its own
server-side authorization and audit boundary.

## Execution boundary

The Hub does not grant `feature-draft`, `feature-estimate`, `feature-confirm`,
payment, upload or any provider capability. Existing per-workflow server
checks remain mandatory:

```text
signed session -> CSRF -> schema/ownership -> estimate -> explicit confirm
-> canonical job adapter -> validated output -> private delivery
```

No static count may be represented as successful execution. A route marked
guarded stays guarded until its own contract and tests are complete.

## Refresh

Run `scripts/migration/audit_bot_to_web.py` only against the selected local
Bot baseline/worktree. Review the resulting JSON and coverage changes before
shipping them. The audit itself remains source-only and masks secret-shaped
literals.
