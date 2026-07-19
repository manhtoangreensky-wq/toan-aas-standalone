# Web-native Workspace Setup Profile

## Purpose and authority boundary

`/workspace/setup` is a compact, signed-account preference profile used to
make the standalone TOAN AAS Web App easier to enter and revisit. It records
only a person's selected working style and up to three preferred Web studios;
it is not an identity, entitlement, execution, pricing or integration record.

| Surface | Owner | It never does |
| --- | --- | --- |
| Workspace Setup profile | Signed Web account | Read or write Telegram identity, Bot state, Core Bridge, provider, job, wallet/Xu, PayOS, publication or notifications. |
| Dashboard guidance | Web presentation layer | Infer access, execute an action, create a job or hide a guarded capability. |
| Account-level update | Signed Web account + CSRF | Accept a browser-supplied account ID, canonical user ID or raw Telegram ID. |

This is a Web-native quality-of-life feature. It does not claim parity with a
Bot command and does not alter the frozen Bot baseline.

## Profile lifecycle

```text
not_started --complete--> completed --complete--> completed (new revision)
not_started --skip-----> skipped   --complete--> completed
completed   --skip-----> skipped   --complete--> completed
```

Every successful write increments `revision`. A stale form cannot overwrite a
newer profile. `completed` requires a role, goal, experience level and one to
three distinct studio choices; `skipped` intentionally stores no choices.

## API and controls

```text
GET  /api/v1/workspace/setup
POST /api/v1/workspace/setup
```

The route uses a signed Web session. `POST` additionally requires the current
CSRF token, strict closed-vocabulary JSON, optimistic `expected_revision` and
a scoped idempotency key. The API exposes the normal envelope plus an explicit
Web-only boundary. A malformed boundary is rejected by the Portal rather than
being treated as a valid preference profile.

- Read/write rate buckets are fixed by method and route; a trailing slash is
  covered before Starlette can redirect it.
- The raw mutation body is capped at 8 KiB before JSON parsing.
- Idempotency receipts are scoped to the signed account, retained for at most
  24 hours and capped at 1,024 records per account.
- Audit events record only the action and a fixed target/detail, never a
  person's selections, email, Telegram identity or credential.
- `web_workspace_setup_profiles` is an additive Web-owned table with a
  foreign key to `web_accounts`; it has no Bot table or ledger migration.

## Portal experience and privacy

The app-first screen is one explicit form with three visible parts, not a
fake multi-step wizard. It has a persistent Dashboard shortcut so a completed
or skipped setup can be updated later. Studio selection is constrained to
three choices with a live, keyboard-readable count; mobile selects and
buttons meet the 44 px touch target baseline.

No preferences are placed in `localStorage`, `sessionStorage`, a URL, the
service-worker cache or a public PWA fallback. `/workspace/setup` and its API
prefix are explicitly private-cache exclusions.

## Verification

Focused contracts cover signed-session and CSRF rejection, strict schema,
owner isolation, revision collisions, complete/skip/edit transitions,
idempotency replay/expiry/cap, bounded bodies, fixed rate limits including the
trailing slash, audit minimization, PWA exclusion, fail-closed boundary
projection, responsive app-first markup and the max-three accessibility
behavior. They do not claim a live Bot, provider, payment or notification
flow.
