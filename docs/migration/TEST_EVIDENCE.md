# COPYFAST test evidence

This note records the local, non-live verification carried out for the two
separate COPYFAST branches. It is deliberately not a `LIVE PASS` claim.

## Passing focused verification

| Worktree | Command | Result |
| --- | --- | --- |
| Web App | `python -m pytest -q` | `11 passed` |
| Web App | `python -m compileall -q .` | passed |
| Web App | `node --check static/portal/portal.js`, `integration.js`, `service-worker.js` | passed |
| Bot bridge | `python -m pytest -q tests/test_webapp_core_bridge.py` | `6 passed` |
| Bot bridge | `python -m py_compile bot.py`, `local_worker.py`, `webapp_core_bridge.py` | passed |
| Static audit | `audit_bot_to_web.py` against the local P0 bridge worktree | 786 commands, 1,928 callback-data values; 100% classified; 0 unmapped routes; 0 missing bridge-route gap |

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
reports that are not part of the COPYFAST bridge diff. The bridge branch's
own tracked change is only `bot.py`; `webapp_core_bridge.py` and its test are
new additive files. No PayOS/wallet/ledger migration, webhook, or provider
call was added.

## Guardrails verified by tests

- Browser has no core token, HMAC secret, provider key, raw provider task ID,
  wallet ledger writer, or PayOS webhook.
- Admin HTML requires both a signed session and a current canonical bot role;
  a stale Web role cache is rejected.
- Telegram link codes are one-time and expiring; private bridge request IDs
  are signed nonces and replays are rejected.
- Provider/payment switches are disabled by default. A guarded route never
  fabricates a completed output or credits Xu.
- Asset delivery verifies ownership and completed output first; until the bot
  exposes a canonical temporary signed-delivery issuer, no result URL, file ID
  or local path is returned to the Web App.
