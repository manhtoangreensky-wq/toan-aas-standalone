# Image Prompt Composer Variant Catalogue Parity — Design

## Purpose

Make the three text-only Image Prompt Composer variants match the local Bot's
pure sales, premium-brand and viral/social catalogue.  This is a content
parity slice only; it does not select a variant as an execution input, create
media, or change the existing Memory save contract.

## Source and mapping

The Bot helper `image_prompt_variants(result, lang)` returns exactly three
strings in a fixed order.  The Web keeps the same public result shape:

1. sales/product-led direction;
2. premium brand direction;
3. viral/social direction.

The Web resolver receives only already validated `subject`, server-resolved
`style`, normalized `ratio`, and `vi|en` language.  It copies the visible
textual direction, never Bot callbacks, pending/result state, Telegram file
IDs, user IDs, provider tier, job, wallet, payment or delivery data.

## Boundary

`_compose_image_prompt` remains request-only and produces a draft response
with `image_created=false`, `job_created=false`, `payment_started=false` and
all existing no-execution facts unchanged.  The variants remain part of the
server-validated response and the Memory Center save continues to preserve a
full recomputed draft; no selected-variant parameter is introduced here.

## Verification

Focused API tests send a signed CSRF request in both languages and assert
the complete three-item list exactly.  Existing tests retain strict schema,
originality, no persistence, Memory ownership/idempotency and static
no-callback checks.
