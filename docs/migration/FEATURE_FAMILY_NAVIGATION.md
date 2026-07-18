# Feature Family Navigation Contract

`/features/content`, `/features/image`, `/features/video`, `/features/voice`,
`/features/music`, `/features/subtitle`, and `/features/documents` are
navigation surfaces for the corresponding Web App families.

- A family page builds its cards only from the customer catalog and only when
  the route is also registered in the local Portal manifest.
- It is not an engine, provider, payment, wallet, job, or delivery endpoint.
- The card status comes from the existing canonical readiness projection. A
  guarded card stays guarded; the family page must never claim a provider is
  ready or fabricate an output.
- An inventory-only route is intentionally omitted rather than made clickable.
  New Bot parity must first add a concrete Web route and a canonical adapter
  contract.
- The page can link to an existing draft/estimate workflow, read-only view, or
  guarded module. Browser cards do not bypass signed session, CSRF, ownership,
  bridge, or feature-confirm controls.

This closes navigation parity only. Engine/job parity remains governed by
`FEATURE_CONFIRM_CONTRACT.md` and the Bot/Core Bridge.

## Customer parity hubs

The customer command groups that are not single engine forms now have their
own signed Web routes instead of being silently collapsed into Dashboard:

| Web route | Bot command group | Boundary |
| --- | --- | --- |
| `/tools` | tools, models, recommendation and feature discovery | A searchable directory of registered Web workflows; it does not claim a provider is live. |
| `/studio` | media factory, creative flow, film, pipeline and production planning | Navigation between existing content/image/video/voice/subtitle workflows; it never creates a project/job itself. |
| `/media-workspace` | music/SFX brief, personal audio selection and music prompt semantics | Private Audio Asset Vault references, collections and deterministic local brief directions. It never searches a provider, streams audio, creates a music job, charges Xu or claims output delivery. |
| `/membership` | packages, member/VIP, rank and trial status | Metadata is read only from the canonical wallet/package bridge; grants and Xu effects remain Bot-owned. |
| `/status` | public AI/tool/Telegram/queue readiness commands | Displays only server-safe Web/Telegram/bridge readiness; no identity, secret, provider payload or control action is exposed. |
| `/growth/ai` | `growth_ai` | Growth Review Web-native: evaluates only six bounded metrics the signed account manually enters using the Bot-compatible deterministic score/rule tree. It never connects to a platform, calls AI/Bot/provider, reads canonical revenue, changes Xu/PayOS, creates a job or stores the input/result. The Bot's separate live `/growth_ai` conversation remains canonical. |
| `/campaign/report` | `campaign_report`, `export_report` | Builds a tightly allowlisted Bot command from a 1–90 day window, optional platform/campaign ID and TXT/CSV choice. Text/CSV output and any charge/refund decision remain in the canonical Telegram conversation. |

All customer parity hubs require the normal signed-session and linked-Telegram route gate.
They are catalog/navigation/read-only surfaces, not substitutes for an engine,
ledger, PayOS callback, provider dashboard or Bot-only state table.
