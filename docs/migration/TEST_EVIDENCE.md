# COPYFAST test evidence

This note records the local, non-live verification carried out for the two
separate COPYFAST branches. It is deliberately not a `LIVE PASS` claim.

## Passing focused verification

| Worktree | Command | Result |
| --- | --- | --- |
| Web App | `python -m pytest -q` | `170 passed, 1 warning` |
| Web App | `python -m compileall -q .` | passed |
| Web App | `node --check static/portal/portal.js`, `integration.js`, `service-worker.js` | passed |
| Web App CI definition | `.github/workflows/webapp-quality.yml` locally mirrored and GitHub Actions | passed in an isolated clean environment using `requirements-dev.txt`: `194 passed, 1 warning`, covering asyncio and the explicitly compatible Trio backend. GitHub Actions runs `29196146374` and `29196144936` passed for commit `d96273d` after the checkout was changed to retain the parent commit required by the whitespace gate. The workflow installs the pinned test dependencies, compiles Python, checks three Portal JavaScript files, runs pytest and checks whitespace for each `main`/`feature/**` push and PR. |
| Mobile workspace dock | portal static contract + Node syntax check | passed: `70` portal safety contracts verify that the five-route dock is signed-session-only, keyboard/focus visible, safe-area aware and navigation-only (no fetch, provider, payment or browser-owned private state). Full Web suite passes with this surface enabled. |
| Workspace quick navigation | portal static contract + Node syntax check | passed: the signed-session command palette indexes registered customer routes, includes Admin routes only when the server-derived session is admin, traps focus, supports `Ctrl/Cmd + K` and Escape, and filters only locally. It performs no fetch, provider, payment, wallet or job action. |
| Web App | local Node check of Growth AI/Campaign report command builder | passed: fixed command, 1–90 day, platform, campaign-ID, goal and format allowlists accept canonical values and reject tampered input. |
| Bot bridge | `python -m pytest -q tests/test_webapp_core_bridge.py` | `16 passed` |
| Bot bridge | `python -m py_compile local_worker.py`, `webapp_core_bridge.py` | passed |
| Bot baseline | `python -m py_compile bot.py` | timed out after 124s in this local runtime; process stopped, no provider/import flow was executed |
| Static audit | `audit_bot_to_web.py` against the local P0 bridge worktree | 774 canonical commands, 1,925 callback-data values, 150 Web routes; 100% mapping coverage; 100% guarded-surface coverage; 0 unmapped routes; 30 static Bot bridge routes match 28 Web request shapes with 0 unmatched requests; the static Telegram callback contract is present with 0 reported gaps and both sides use the same body/timestamp/request-ID/path HMAC material shape. Preflight records requested baseline `b29d…` (where `webapp_core_bridge.py` is missing), audited bridge checkout `32d6…`, and the local-only drift (6 ahead / 0 behind) without fetching, merging or executing Bot code. The audit excludes clearly named noncanonical Bot drafts, reads only routes reachable from the signed `app.py` entrypoint, and propagates direct static admin guards so unmounted legacy decorators and neutral-named admin reports are not mistaken for customer parity. Personal Bot commands, Growth AI/campaign report, and the membership/status/tools/media command groups map to dedicated guarded/read-only Web hubs. |
| Portal visual smoke | local public landing and login at desktop and 390px mobile viewport | passed: the landing and unauthenticated login both hide the workspace sidebar/header without a layout gap, remain within the mobile viewport, expose no raw Telegram-ID field, and explain the Bot-adapter release gate when Telegram linking is not deployed. No live account, Telegram, provider, payment or Bot call was made. |
| Campaign Planner visual smoke | local mock account + signed one-time Telegram callback | passed: register/login, browser-bound Telegram completion, `/campaigns`, create plan, timeline/card render and `draft → review` self-review update all completed. The mock used a temporary local database and HMAC test credential only; no live Bot, provider, PayOS or production account was touched. |
| Content Calendar visual smoke | same local mock at desktop and 390px mobile viewport | passed: the account-owned scheduled plan appears in the month grid, links back to its planner card, and mobile exposes a deliberately horizontally scrollable seven-day grid without clipping the app shell. Calendar and Self-review Queue carry no publish, reminder, provider, admin-approval or payment action. |
| Manual top-up UX smoke | same local mock, bridge/payment disabled | passed: the portal cleanly separates PayOS QR handoff from manual VND/international guidance, exposes `/thucong` only as a Bot handoff, and renders pending/approval meanings without a Web bill, TXID, QR, bank-account, upload or credit action. |
| Dashboard Work Queue smoke | local signed account + HMAC-only Bot-link mock, desktop and 390px mobile viewport | passed: the Dashboard derives processing jobs, delivery-ready assets, failed jobs and `waiting_user` tickets only from owner-scoped canonical responses. Empty data stays an honest zero state; the panel creates no notification, job, ticket, payment, provider or browser-side delivery state. No live Bot, provider, PayOS or Railway request was made. |

## Full bot-suite baseline result

`python -m pytest -q` completed with **1,321 passed and 3 failed**. The three
failures are not changed by the bridge diff:

1. `tests/test_core.py::test_operations_v1a_tax_prep_and_accounting_exports`
   is an existing finance/tax export expectation in the frozen local P0
   snapshot: the export query filters compliance notes by `created_at`, while
   the test expects a note to appear for its `effective_from`/`effective_to`
   period. COPYFAST must not modify finance, PayOS, wallet, or ledger logic
   merely to alter this unrelated result.
2. `tests/test_p0_4_hard_reset_audio_video_flow.py::test_payos_not_touched`
3. `tests/test_p0_5_audio_video_addon_button_logic.py::test_no_forbidden_payment_files_touched`

The latter two tests compare their changed-file list to `origin/main`, while
the user-selected local P0 baseline is intentionally divergent from that
remote (`HEAD...origin/main` was `1` ahead and `657` behind during this run).
They therefore see historical remote-difference files such as prior PayOS
reports that are not part of the COPYFAST bridge diff. The bridge changes are
additive (`bot.py` link entrypoints plus `webapp_core_bridge.py` and focused
tests); no PayOS/wallet/ledger migration, webhook, or provider call was added.

## Guardrails verified by tests

- Browser has no core token, HMAC secret, provider key, raw provider task ID,
  wallet ledger writer, or PayOS webhook.
- `WEBAPP_COPYFAST_ENABLED` stops bridge-backed feature, upload, job, wallet
  and asset work before identity/network calls; `WEBAPP_ADMIN_ERP_ENABLED`
  independently guards Admin bridge calls. The portal reflects those flags in
  its capabilities rather than offering a dead action.
- Customer pages require a signed session and route an unlinked account to
  onboarding. Login preserves only a validated same-origin return path; no
  raw identity or arbitrary redirect URL is trusted from the browser.
- Every Admin ERP HTML **and JSON** endpoint requires both a signed session
  and a current canonical bot role; a stale Web role cache is rejected.
- Telegram Login OIDC is disabled unless BotFather Client ID/Secret and the
  Railway flag are configured. Its authorization code, PKCE verifier, nonce,
  ID token and raw profile ID stay server-side; fixed JWKS/RS256 verification
  produces only an HMAC-protected external identity. When that account later
  links the Bot, the signed Bot identity must match or the request is
  rejected. Existing Bot-linked accounts with the same signed Telegram user
  can use Telegram Login without a duplicate Web account.
- Telegram link codes are one-time and expiring. The bot-to-Web callback has
  a directional bearer token, HMAC-bound body/timestamp/request ID and a
  persistent nonce retained through the accepted clock-skew window; private
  bridge requests also reject replays. Callback JSON is bounded and parsed
  only after HMAC verification, and its audit record uses the signed callback
  request ID. A successful Bot callback records pending proof only: the exact
  signed browser session that created the code must finish a CSRF-protected
  completion before a canonical Telegram identity is bound. A different or
  logged-out browser session cannot inspect or complete the pending link.
  The Portal distinguishes Web-only setup from an actually observed, accepted
  signed Bot callback without exposing a Telegram ID, code, account, request
  ID or secret. The Portal also requires the explicit non-secret
  `WEBAPP_TELEGRAM_BOT_LINK_ENABLED=true` release gate before issuing a
  customer code, so a Web-only release cannot advertise a Bot link the
  deployed Bot does not yet understand. Disabling the gate also rejects a
  valid in-flight signed callback without consuming its one-time code.
- The static preflight records the actual local Bot checkout and its
  ahead/behind relation to the frozen baseline. In the current audit, the
  callback bridge exists only in a separate checkout six commits ahead of
  `b29…`; this is evidence of a deployment boundary, not a claim that the
  production Bot already has the callback. No Bot source or runtime was
  changed in the Web-only work.
- Growth AI and Campaign Report now offer professional filter forms in the
  signed Web portal, but they only copy a closed-schema command for the user
  to submit to Bot. Web accepts no free command text, does not calculate
  metrics/revenue, issue a report file, charge Xu or decide refunds.
- Every private-bridge retry now signs a fresh server-side nonce while keeping
  the canonical idempotency key. Nested runtime/provider credentials, task IDs
  and filesystem paths are recursively redacted before an envelope reaches a
  browser.
- Web idempotency reserves payment, upload, ticket, feature-confirm and
  future Admin-write keys atomically before a bridge call. A concurrent retry
  receives an in-progress guard instead of creating another canonical call.
- Admin write endpoints are locally CSRF/admin-gated and disabled by the
  explicit `WEBAPP_ADMIN_WRITES_ENABLED=false` default; the customer-facing
  Admin ERP stays read-only until a separate canonical write adapter is
  approved.
- Production session detection is consistent across `APP_ENV`, `ENVIRONMENT`
  and Railway environment markers; startup fails without a real production
  session secret and always emits Secure cookies. Credentialed CORS rejects
  wildcards and non-HTTPS remote origins.
- Linking a Telegram identity records the initiating session and revokes every
  other session for that Web account, so stale sessions cannot inherit a newly
  bound canonical identity. A canonical Telegram identity cannot be linked to
  two Web accounts.
- The Web onboarding screen starts the existing one-time link flow, renders
  only its temporary code/deep link, and re-checks signed server status. It
  neither accepts a raw Telegram ID nor alters the established PayOS webhook.
- Uploads reject path traversal, unsupported MIME/signatures and oversized
  payloads twice (Web and bot). Raw bytes live only in bot-owned staging and
  feature inputs can reference only ownership-checked upload IDs.
- The Web API mirrors the browser's minimum intake contract before a feature
  payload reaches Bot: it rejects forged identity/Xu/provider/job/output
  fields, malformed staging IDs, missing file staging/voice-clone consent,
  missing target language and invalid merge/split document requests. This is
  defense in depth only; Bot remains authoritative for file ownership, MIME,
  pricing, job creation, ledger writes and delivery.
- Draft → estimate → confirm keeps only sanitized scalar form values and
  canonical staging IDs in in-memory portal state. It never persists raw files
  or secrets in localStorage, and re-rendering cannot silently turn a quote
  into an empty request.
- A page with form fields no longer exposes a duplicate hero CTA that could
  submit an empty action. Feature/customer writes now originate from the
  validated form that collects its current fields, staged uploads and quote
  fingerprint.
- Quote-capable Chat, TTS and image workflows can start at estimate when their
  bot helper has no planning-draft adapter. Confirm is offered only after a
  matching canonical estimate; changing text or files forces a new estimate,
  and matching feature submissions are single-flight with a stable key.
- Feature forms use the actual canonical naming/constraints for video context
  and storyboard, Voice Vault, subtitle/dubbing and document flows. Client
  preflight checks prevent invalid media, missing consent, non-contiguous PDF
  ranges and invalid document combinations from entering staging; the bridge
  remains the final authority.
- Translation, dubbing and document translation now expose the complete
  22-code P0 target-language list and enforce that same canonical allowlist in
  the browser and Web API. Feature inputs are capped at the Bot's maximum of
  eight staging IDs before the browser uploads excess files or a bridge call
  is attempted.
- The content Storyboard form now sends the exact planning inputs read by the
  Bot P0 helper (`template`, `platform`, `format`, `duration`, `style`, `goal`
  and `notes`), while Image-to-Image requires an owned staged source image
  instead of silently behaving like text-to-image.
- Pricing, packages and Admin read-only surfaces are returned from bot helper
  functions/tables; the portal never substitutes the feature registry as a
  price table.
- Content, prompt, caption/hashtag, hook/script, storyboard and image-planning
  drafts use provider-free helper functions imported by `bot.py`; the Web UI
  labels them as planning drafts and never presents them as delivered engine
  output. Estimates use canonical bot pricing helpers and charge no Xu.
- The shared content/prompt form no longer exposes an inert output-language
  selector: its current P0 helpers only return Vietnamese planning drafts.
  Image Create no longer stages an unused reference image; aspect ratio is
  displayed as a future-engine preference, separate from the limited canonical
  draft suggestions returned by the current Bot helper.
- Video product/quick/text/image-to-video planning uses the bot's contextual
  prompt helper; multiscene/long planning uses its storyboard helper. Video
  estimates require a canonical tier and scene count, then use the bot's scene
  discount calculation rather than a browser-side formula.
- Image-to-Video now supplies the contextual helper's `platform` and `goal`
  fields. AI Song supplies its canonical prompt mode and cannot silently quote
  a default 30-second song when the user selected a per-second duration.
  Dubbing selects only ownership-scoped Voice Vault profile IDs rather than
  accepting an arbitrary provider voice name from the browser.
- Voice Vault returns only ownership-checked profile metadata; provider voice
  IDs, Telegram file IDs and preview references are redacted. TTS/clone quotes
  use the bot helpers, and clone intake requires an owned audio sample plus
  explicit consent before a future job adapter can run it.
- Music/SFX drafts use bot copyright checks and provider-free prompt helpers;
  standalone music/SFX quotes retain their distinct bot pricing rules. Library
  search, Suno creation and audio render stay guarded.
- Subtitle, translation, dubbing and document routes now validate staged input
  and show canonical estimates/status only. They do not invoke ASR,
  translation, FFmpeg or local document output delivery until a canonical
  job/asset/signed-delivery adapter exists.
- Provider/payment switches are disabled by default. A guarded route never
  fabricates a completed output or credits Xu.
- A global feature-job flag is only a circuit breaker. Even after it is
  explicitly enabled, Web confirm requires the exact feature key in
  `WEBAPP_FEATURE_JOB_ADAPTERS`; unknown, read-only, admin and unrelated
  feature keys remain guarded in both the server and Portal UI.
- Payment UI consumes a future canonical response only: checkout links must be
  HTTPS PayOS URLs, and the Web App can poll a canonical payment ID but never
  creates a webhook, finalizes payment or credits Xu. Ticket/payment submits
  use in-memory single-flight idempotency keys to avoid duplicate clicks.
- Job polling calls only the signed Web API. Active jobs retry transient bridge
  failures with bounded backoff and leave the canonical status unchanged rather
  than presenting a client-side completion.
- Bridge job/asset metadata remains ownership-scoped, but a reported
  `output_available` value is not artifact validation or delivery proof. The
  portal now labels it separately from delivery and never renders a download,
  preview, provider URL or operator endpoint until a canonical temporary
  signed-delivery contract exists.
- Job Center surfaces only redacted canonical estimates, ledger amounts,
  refund/error categories and status explanations. Asset metadata can state
  that output validation occurred while still requiring a signed delivery URL;
  it never turns `download_ready` metadata into a client-side download.
- Ticket filters and customer-visible ticket excerpts operate only on the
  ownership-scoped response; the Admin table continues to omit ticket body,
  username, attachment IDs and provider details. Admin backup/export routes
  resolve to the existing read-only canonical adapters rather than inventing
  an export or backup write action.
- The top-up portal does not confuse the bot's service-package catalog with
  Xu top-up denominations. Until a dedicated top-up catalog adapter exists,
  it opens the configured linked Telegram bot and copies only the canonical
  `/naptien` (PayOS QR động) or `/thucong` (manual reconciliation) command;
  it never displays bank details, static QR data, bill uploads, OTPs or a
  browser-side approval action.
- The manual top-up handoff now explains the Bot-owned sequence and labels
  `pending_admin_review`, `approved` and `rejected` as process states without
  claiming Web can read a bill/TXID or manual-deposit record. The current P0
  bridge has no owner-scoped, redacted manual-deposit history adapter, so the
  only Web-side signal after approval is the canonical wallet history.
- Campaign Planner is an explicitly Web-owned planning board, not a Bot
  campaign mirror. `GET/POST/PATCH /api/v1/campaigns` and the local self-review
  transition require a signed session, CSRF, per-account ownership and
  idempotency. The database/audit contract never stores the plan title or
  destination URL in audit detail; the server does not fetch destination URLs,
  publish, schedule automation, call a provider, create a job, change Xu or
  touch PayOS. Its state `approved` means only ready in the personal Web plan,
  never staff/canonical approval; there is no `published` state.
- A customer may query an ownership-checked payment order code through the
  signed Web API **for PayOS orders only**. Pending orders use bounded
  signed-GET polling only; polling neither calls PayOS nor changes a
  wallet/ledger state. The legacy billing,
  manual-topup and webhook routes are asserted unmounted so there is no second
  PayOS creator, webhook, order store or Xu writer in `app.py`.
- The public home is a responsive product entry surface: an anonymous visitor
  sees only static studio/workflow/security copy and safe local login links;
  a signed user is redirected to onboarding or Dashboard. It makes no API,
  provider, wallet or identity action and does not replace the signed Portal.
- Video finalization and mux now have an explicit navigator matching the Bot
  `vfinal` branches (voice, music, subtitle/dubbing, logo, preview/export).
  It only links to registered workflows and Job/Asset views; watermark/mux
  stays guarded until the Bot exposes a canonical job, validation and private
  delivery adapter.
- Personal Bot functions that remain Bot-owned now have protected, explicit
  companion pages instead of being silently collapsed into Dashboard: Notes &
  Memory, Reminders, Referrals, Rewards, Community and Bot Guide. They preserve
  the signed Web-session/onboarding gate and offer only an allowlisted command
  copy plus an optional `t.me` handoff derived from the public `BOT_USERNAME`.
  They neither mirror Bot data nor move canonical Telegram identity, wallet or
  job state into the browser.
- Guarded feature workspaces now offer only six reviewed, zero-argument Bot
  entry commands by family: `/film`, `/image_tools`, `/create_media`,
  `/music`, `/translate` and `/doc_tools`. The Portal never appends a prompt,
  staged upload ID, Telegram identity, quote, Xu amount, session or token; all
  other family entrypoints—including Voice—remain on the safe generic Bot menu
  until a customer-safe command and canonical bridge adapter exist.
- Dashboard includes a responsive **Work Queue** rather than forcing customers
  to infer next actions from a long route list. It reads only the already
  owner-scoped jobs/assets/tickets bridge projections: queued/processing jobs,
  assets with a real delivery contract, failed jobs, and `waiting_user`
  tickets. Ticket hydration is optional, so a guarded ticket read cannot hide
  wallet, job, asset or readiness metadata; no count creates a Web-side
  notification, ticket, retry, refund, provider call, payment or delivery URL.
