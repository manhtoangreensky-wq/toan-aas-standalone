# COPYFAST test evidence

This note records the local, non-live verification carried out for the two
separate COPYFAST branches. It is deliberately not a `LIVE PASS` claim.

## Passing focused verification

| Worktree | Command | Result |
| --- | --- | --- |
| Web App | `python -m pytest -q` | `27 passed` |
| Web App | `python -m compileall -q .` | passed |
| Web App | `node --check static/portal/portal.js`, `integration.js`, `service-worker.js` | passed |
| Bot bridge | `python -m pytest -q tests/test_webapp_core_bridge.py` | `16 passed` |
| Bot bridge | `python -m py_compile local_worker.py`, `webapp_core_bridge.py` | passed |
| Bot baseline | `python -m py_compile bot.py` | timed out after 124s in this local runtime; process stopped, no provider/import flow was executed |
| Static audit | `audit_bot_to_web.py` against the local P0 bridge worktree | 786 commands, 1,928 callback-data values, 133 Web routes; 100% classified; 0 unmapped routes; 0 missing bridge-route gap |
| Portal visual smoke | local dashboard at desktop and 390px mobile viewport | prior launchpad smoke passed; the current Web-only Job/Onboarding/Admin refresh was not re-run because this session's browser policy refused the local URL. Syntax checks and presentation-contract tests passed instead. |

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
- Every Admin ERP HTML **and JSON** endpoint requires both a signed session
  and a current canonical bot role; a stale Web role cache is rejected.
- Telegram link codes are one-time and expiring. The bot-to-Web callback has
  a directional bearer token, HMAC-bound body/timestamp/request ID and a
  persistent nonce; private bridge requests also reject replays.
- The Web onboarding screen starts the existing one-time link flow, renders
  only its temporary code/deep link, and re-checks signed server status. It
  neither accepts a raw Telegram ID nor alters the established PayOS webhook.
- Uploads reject path traversal, unsupported MIME/signatures and oversized
  payloads twice (Web and bot). Raw bytes live only in bot-owned staging and
  feature inputs can reference only ownership-checked upload IDs.
- Draft → estimate → confirm keeps only sanitized scalar form values and
  canonical staging IDs in in-memory portal state. It never persists raw files
  or secrets in localStorage, and re-rendering cannot silently turn a quote
  into an empty request.
- Pricing, packages and Admin read-only surfaces are returned from bot helper
  functions/tables; the portal never substitutes the feature registry as a
  price table.
- Content, prompt, caption/hashtag, hook/script, storyboard and image-planning
  drafts use provider-free helper functions imported by `bot.py`; the Web UI
  labels them as planning drafts and never presents them as delivered engine
  output. Estimates use canonical bot pricing helpers and charge no Xu.
- Video product/quick/text/image-to-video planning uses the bot's contextual
  prompt helper; multiscene/long planning uses its storyboard helper. Video
  estimates require a canonical tier and scene count, then use the bot's scene
  discount calculation rather than a browser-side formula.
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
- Job polling calls only the signed Web API. Active jobs retry transient bridge
  failures with bounded backoff and leave the canonical status unchanged rather
  than presenting a client-side completion.
- Bridge job/asset metadata remains ownership-scoped, but a reported
  `output_available` value is not artifact validation or delivery proof. The
  portal now labels it separately from delivery and never renders a download,
  preview, provider URL or operator endpoint until a canonical temporary
  signed-delivery contract exists.
