# AI Chat Workspace — Web-native contract

## Scope

`/chat`, `/chat/new`, and `/chat/{thread_id}` are a signed-account
Conversation Workspace. They store only Web-owned authoring records:

- a thread with title, objective, local authoring profile, tags, optional
  Project/Prompt Library UUID references, pin state, lifecycle and revision;
- context cards (`brief`, `constraint`, `reference`, `instruction`); and
- human-authored turns (`prompt`, `note`, `decision`); and
- an owner-scoped Chat Run receipt with its customer-authored user message.

`focus`, `deep`, and `pro` are local editing profiles. They are not Bot
Chat Pro/Deep modes, model aliases, quotas, provider choices, or permissions.

## Explicit boundary

Authoring APIs declare `execution: authoring_only` and false values for AI
execution, provider/Bot calls, assistant reply creation, output/job,
wallet/payment mutation, browser upload/media URL, stream, and delivery. The
Chat Run APIs return an explicit `execution.mode: web_native_chat_run`
capability object instead: it accepts a customer-authored message and records
the real `draft → queued → guarded` lifecycle, but still declares provider
execution and assistant reply availability false.

The UI must present this as “Đã lưu tin nhắn — AI execution đang được bảo vệ”,
not as a model result. `WEBAPP_CHAT_EXECUTION_ENABLED` is false by default;
even if an operator sets it true, this module fails closed with
`WEB_CHAT_EXECUTION_ADAPTER_UNAVAILABLE` until a separately reviewed adapter
exists.

The workspace does not import or invoke `ai_assistant.py`, Gemini, the Core
Bridge, PayOS, wallet logic, provider SDKs, Telegram identity, Bot transcript,
or job/delivery code. It must never fabricate an assistant reply, typing
indicator, result, quote, charge, preview, download, or success state.

## API and lifecycle

Read API: `summary`, `policy`, `references`, `threads`, detail, events and an
`execution-status` capability endpoint. It truthfully advertises that a
Web-native guarded receipt can be submitted, while provider and assistant
execution remain unavailable. Writes require a signed session, CSRF,
server ownership checks, optimistic revision, idempotency key, audit event and
an opaque/redacted receipt:

```text
POST  /api/v1/chat-workspace/threads
PATCH /api/v1/chat-workspace/threads/{id}
POST  /api/v1/chat-workspace/threads/{id}/lifecycle
POST  /api/v1/chat-workspace/threads/{id}/restore-version
POST  /api/v1/chat-workspace/threads/{id}/contexts
PATCH /api/v1/chat-workspace/threads/{id}/contexts/{context_id}
POST  /api/v1/chat-workspace/threads/{id}/contexts/{context_id}/state
POST  /api/v1/chat-workspace/threads/{id}/turns
POST  /api/v1/chat-workspace/threads/{id}/turns/{turn_id}/state
POST  /api/v1/chat-workspace/threads/{id}/runs
GET   /api/v1/chat-workspace/threads/{id}/runs
GET   /api/v1/chat-workspace/threads/{id}/runs/{run_id}
```

`POST /runs` accepts `{client_message, expected_revision, idempotency_key}`.
It is CSRF-protected and persists only the caller's own `user` message. The
direct response can echo that message to the signed caller; the durable
idempotency replay receipt is redacted. The module creates no assistant
message. There is intentionally no cancel endpoint while no queue/worker can
acknowledge cancellation safely.

Thread lifecycle is `draft → review → ready`, with explicit returns to
`draft` and archive/restore paths checked by the server. Only Draft permits
metadata, context and turn changes. Restoring a version creates a new
revision; it does not delete history or child records.

`GET /threads` is owner-scoped, filterable by lifecycle and a safe text query,
and paginated. The Web UI requests 50 metadata-only cards at a time; the API
accepts a bounded page size of 1–100, returns an explicit `pagination`
object, and clamps an out-of-range offset to the last valid page. Refreshes
and writes preserve the current library page/filter. Search text is never a
browser draft or URL state.

## Data and safety

The additive SQLite tables are `web_chat_threads`,
`web_chat_thread_versions`, `web_chat_context_cards`, `web_chat_turns`, and
`web_chat_workspace_events`, `web_chat_messages`, `web_chat_runs`, and
`web_chat_run_events`. All rows include `account_id`; references are
re-checked on create/update/restore and when a thread becomes active again.
Archived records count toward bounded storage, preventing archive/create
growth.

An account can retain at most 500 threads, each with at most 80 context cards
and 100 revisions. A thread can retain at most 500 Chat Run receipts. Because
a new thread begins at revision 1 and every human
turn writes a revision, the maximum possible retained human-authored turns is
99; the UI and API use that truthful ceiling rather than claiming an
unreachable larger number.

Free text rejects control characters, credentials, OTP/card/payment evidence,
Bot/provider/job/file handles, executable markup, URL/scheme/blob and raw
local/UNC paths. A future citation, upload, model or execution adapter needs
its own reviewed contract rather than reusing these text fields.

Private `/chat` and `/api/v1/chat-workspace` paths are excluded from the PWA
cache. The browser keeps no conversation data in localStorage and refreshes
from the server after each redacted mutation receipt.

## Known guarded gap

Real AI execution is intentionally unavailable in this module. It requires a
separate Web engine/adapter contract with model selection, consent, cost,
quota, safety, output validation, audit, retention and delivery semantics.
That future work must remain independent from the historical Telegram Bot.
