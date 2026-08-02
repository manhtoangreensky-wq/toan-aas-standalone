# Image Prompt Composer Bot Style Catalogue Mapping — Design

## Purpose

Bring the useful visible image-style directions from the local Telegram Bot
into the Web-native Image Prompt Composer, without carrying over Telegram
callbacks, pending state, user IDs, image/file state, providers, jobs, wallet
or payment behaviour.

## Source evidence

The local Bot's pure helper `image_prompt_style_suggestions(goal_code, lang)`
exposes three human-readable directions for `product`, `ad`, and `cinematic`.
Its unknown/custom-goal fallback is the product catalogue.  Callback values
such as `imgtool|prompt_style|1` are transport details and are explicitly out
of scope for the Web contract.

## Contract

The existing Web request values remain the only public API:

```json
{
  "style_preset": "auto|suggestion_1|suggestion_2|suggestion_3|custom",
  "style": ""
}
```

- `auto` keeps the existing Web default resolver for backwards compatibility.
- `suggestion_1` through `suggestion_3` resolve server-side to the Bot's
  visible catalogue text for `product`, `ad`, or `cinematic` in Vietnamese or
  English.
- `custom` still accepts only customer-authored bounded text and keeps the
  originality guard.
- A Web `goal_code=custom` uses the Bot's product fallback only for the three
  server-owned suggestions.  It never accepts a Bot goal token or callback.

The response continues to expose the semantic preset plus the resolved style
text.  No Bot callback, state, user ID, provider/model, quote, job, asset,
wallet or payment field is introduced.

## Implementation boundary

Only `copyfast_image_studio.py` changes server resolution.  Portal rendering
continues to use the five existing semantic choices and shows the exact
server-resolved text in the result.  No database schema, migration, bridge,
provider, payment, Bot source or Telegram workflow changes.

## Verification

Focused API tests assert exact catalogue resolution for both languages,
including all three goal families and the custom-goal product fallback.  They
also prove `auto` remains unchanged, custom text remains custom, malformed
callback-shaped input is rejected, and the existing request-only boundary
does not mutate image/job/payment state.  Static portal tests retain the
no-callback boundary.
