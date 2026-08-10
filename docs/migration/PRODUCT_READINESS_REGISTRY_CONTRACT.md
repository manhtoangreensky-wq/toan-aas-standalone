# Product Readiness Registry Contract

`copyfast_product_readiness.py` is the one display-only taxonomy for every
feature emitted by `GET /api/v1/catalog`. It makes the product boundary clear
without implying that a route can make a provider call, create a job, charge a
wallet, finalize payment, deliver an output, or bypass its own server-side
checks.

## Public states

| State | Meaning |
| --- | --- |
| `available` | A Web-owned workspace, account, support, history, or navigation surface is enabled. It is not an execution promise. |
| `planning_only` | The Web route provides authoring, brief, blueprint, or deterministic planning only. |
| `local_execution` | A reviewed Web-local transform/artifact boundary is enabled. Its route still validates input, ownership, limits and output. |
| `canonical_read` | A configured Bot/Core canonical source may provide read-only data. Account linking and each route's own bridge contract still apply. |
| `guarded` | The product does not publish an actionable capability: the feature is unknown, requires a missing canonical bridge, or is an always-guarded write/payment path. |
| `disabled` | A Web-native surface is deliberately paused by its existing feature gates. |

## Boundary

- The module imports no Bot, Core Bridge client, provider, wallet, PayOS,
  database, storage, environment, network, or subprocess code.
- It receives already-public feature flags and a bridge-configuration boolean
  from `copyfast_api.py`; it never reads account/link state or returns internal
  handler names, flag names, endpoint paths, prices, provider metadata, files,
  or delivery data.
- The Portal renders the descriptor only as a readable label. It is not used
  by action gating, `fetch`, confirmation, payment, job, output, or delivery
  logic.
- Missing or malformed data renders as `guarded`. A canonical write such as
  wallet top-up remains `guarded` even if its read companion is configured.
- Canonical pricing is `canonical_read` only while the configured Core Bridge
  is available; otherwise it is `guarded`. Partner Readiness remains
  `available` only while its existing maintenance flag is enabled, and becomes
  `disabled` when that private Web-native surface is paused.

## Maintenance rule

An implementation must add a feature to `local_execution` only after its
private input/output, ownership, idempotency and artifact-verification contract
exists. A route is not upgraded merely because it has a UI card, a global
provider flag, or a matching Telegram command.
