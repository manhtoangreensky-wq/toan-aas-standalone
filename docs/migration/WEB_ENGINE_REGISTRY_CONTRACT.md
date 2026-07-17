# Web Engine Registry contract

## Purpose

`copyfast_web_engine.py` classifies each catalog feature as `web_native`,
`bot_companion`, or `guarded`. It turns the static Bot migration inventory into
an honest Web/App product map without importing or running `bot.py`.

The only browser-facing data is:

```json
{
  "mode": "web_native | bot_companion | guarded",
  "execution_state": "ready | guarded"
}
```

This is display metadata, never a permission, quote, job, payment, output or
delivery contract.

## Meaning

| Mode | Boundary |
| --- | --- |
| `web_native` | A signed Web workspace or bounded deterministic private operation exists in this Web repository. |
| `bot_companion` | The Bot remains the canonical authority; a catalog card does not promise that a linked account can execute it. |
| `guarded` | No reviewed standalone engine adapter exists yet. |

For `web_native`, `execution_state` is `ready` only when the operation's
explicit Web maintenance gates are enabled. Other modes stay `guarded` in the
public catalog even when a bridge is configured.

## Boundaries

- The registry imports no Bot, Core Bridge, provider, wallet, PayOS, database,
  storage, environment, network or subprocess code.
- Browser data never contains internal handlers, endpoints, required flags,
  account/Telegram state, pricing, provider details or artifact paths.
- No catalog classification may be represented as successful job execution,
  payment, output creation or private delivery.
- Existing feature endpoints remain authoritative for signed session, CSRF,
  ownership, idempotency, output validation and canonical job rules.
- A global provider flag alone is insufficient to change a feature from
  `guarded`; the standalone adapter, storage, state, ownership, idempotency,
  artifact validation and its tests must be reviewed first.

## Initial Web-native scope

The registry identifies Web-owned projects, notes/reminders, authoring
studios, Asset Vault, support/workboard, and existing deterministic operations:
PDF merge/split/optimize, image-to-PDF, PDF-to-images, text-only PDF-to-DOCX,
image resize and deterministic enhance. OCR, AI image edit/upscale,
translation, TTS/voice clone, music, video, and provider-backed generation
remain guarded.
