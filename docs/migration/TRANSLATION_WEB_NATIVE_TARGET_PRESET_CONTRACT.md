# Translation Target Preset — Web-native contract

## Purpose

`/subtitle-studio/new?intent=translation` offers a small, closed chooser for
manual bilingual authoring. It makes the Web-native translation draft easier
to begin in Vietnamese, English and Chinese; it is not an implementation of
the Bot target-language callback.

| Pair key | Source label | Target label |
| --- | --- | --- |
| `vi-en` | `vi` | `en` |
| `en-vi` | `en` | `vi` |
| `vi-zh` | `vi` | `zh` |
| `zh-vi` | `zh` | `vi` |
| `en-zh` | `en` | `zh` |
| `zh-en` | `zh` | `en` |

The optional query `pair` is interpreted only when the route is exactly `/subtitle-studio/new`,
there is exactly one raw decoded `intent` parameter with the exact value `translation`, and
there is exactly one raw decoded `pair` parameter with one of the closed values in the table.
Uppercase, whitespace-padded, duplicate relevant parameters, absent, malformed, unknown,
non-exact or wrong-route values preserve the manual `source_language` and `target_language`
fields. Extra unrelated parameters remain allowed.
It is a local form preference only: it never changes the Web UI locale, a Bot locale,
an automatic translation setting or a Bot session.

## Request projection

The browser converts the closed `translation_pair` select into the existing
Web-native project request fields:

```json
{
  "intent": "translation",
  "source_language": "vi",
  "target_language": "en"
}
```

The browser rejects a missing or unknown select value before it reaches the
existing signed, CSRF-protected and idempotent project-create API. Direct
project creation elsewhere retains the existing manual language-label fields;
this is a convenience control for the fresh translation intake, not a schema
restriction or an execution authority.

## Non-goals and guard

This contract does not carry a Telegram message, callback value, pending
source, Telegram identity, file bytes, provider request, job ID, quote, Xu,
PayOS record, output or delivery URL. It does not call Core Bridge, provider,
job, payment or wallet APIs. It creates only a new owner-scoped Subtitle Studio
authoring project; user-authored cue text and translation drafts remain manual.

The Bot `tr_target|…` family remains
`CORE_CANONICAL_TRANSLATION_GUARDED`. It may consume Bot-local pending source
state and enter provider/job/payment/delivery paths, so it cannot inherit the
Web selector or be claimed as runtime parity.
