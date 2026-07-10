# COPYFAST test evidence

This note records the local, non-live verification carried out for the two
separate COPYFAST branches. It is deliberately not a `LIVE PASS` claim.

## Passing focused verification

| Worktree | Command | Result |
| --- | --- | --- |
| Web App | `python -m pytest -q` | `18 passed` |
| Web App | `python -m compileall -q .` | passed |
| Web App | `node --check static/portal/portal.js`, `integration.js`, `service-worker.js` | passed |
| Bot bridge | `python -m pytest -q tests/test_webapp_core_bridge.py` | `12 passed` |
| Bot bridge | `python -m py_compile bot.py`, `local_worker.py`, `webapp_core_bridge.py` | passed |
| Static audit | `audit_bot_to_web.py` against the local P0 bridge worktree | 786 commands, 1,928 callback-data values, 132 Web routes; 100% classified; 0 unmapped routes; 0 missing bridge-route gap |

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
- Uploads reject path traversal, unsupported MIME/signatures and oversized
  payloads twice (Web and bot). Raw bytes live only in bot-owned staging and
  feature inputs can reference only ownership-checked upload IDs.
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
- Provider/payment switches are disabled by default. A guarded route never
  fabricates a completed output or credits Xu.
- Asset delivery verifies ownership and completed output first; until the bot
  exposes a canonical temporary signed-delivery issuer, no result URL, file ID
  or local path is returned to the Web App.
