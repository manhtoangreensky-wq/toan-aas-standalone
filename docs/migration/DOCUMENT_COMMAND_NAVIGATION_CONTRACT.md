# Fresh Web navigation for Document command entrypoints

## Purpose

The frozen Telegram Bot has finite customer command entrypoints for document
tools. This contract maps only the reviewed commands below to a **fresh,
signed Web-native navigation surface**. It does not copy, deserialize, bridge
or infer a Bot document workflow.

The target is always a customer page, never a raw `/api/v1/...` write endpoint.
After navigation, the Web App starts its own owner-scoped flow: the signed
account chooses a fresh Asset Vault source, the server validates it, and any
write separately requires CSRF and an account-scoped idempotency key. A file
or output is available only after the existing private-delivery verification
for that operation succeeds.

## Reviewed finite command catalog

| Frozen Bot command | Fresh Web page | Independent Web boundary |
| --- | --- | --- |
| `/doc_tools` | `/documents` | Document tool directory; the customer selects a Web-native tool. |
| `/pdf_to_word` | `/documents/pdf-to-word` | Text-bearing PDF to verified private DOCX; it does not promise OCR or layout preservation. |
| `/compress_pdf` | `/documents/compress` | One verified PDF optimization workflow; it does not reproduce Bot `light`/`medium`/`strong` labels. |
| `/split_pdf` | `/documents/split` | Fresh private PDF and page range selection. |
| `/merge_pdf` | `/documents/merge` | Fresh owner-scoped PDF source/order selection. |
| `/image_to_pdf` | `/documents/image-to-pdf` | Fresh private image selection/order and bounded image decoding. |
| `/ocr_pdf` | `/documents/pdf-ocr` | Bounded local private PDF OCR to verified TXT, not a raw API or browser OCR flow. |

These mappings are classified as `NAVIGATION_ONLY`, with
`FRESH_SIGNED_WEB_DOCUMENT_NAVIGATION` and `NO_RUNTIME_CLAIM`. Navigation is
not evidence that a Bot command completed, an engine ran, an output exists, or
a delivery is valid.

## State and authority boundary

No value from the Bot command or its later conversation state is carried in a
Web URL, form, local storage, session, request body or hidden browser action.
In particular, the Web does **not** receive or replay:

- Telegram identity, message/chat/file IDs, Bot `USER_PENDING`, file list or
  order, filename/path/blob, source URL, page range or compression profile;
- Bot confirmation, quote, charge, Xu/wallet record, PayOS order/webhook,
  provider state, job/worker state, output receipt or Telegram delivery;
- a preselected Asset Vault ID, temporary download URL, browser secret or
  background submit.

Every mapped page remains owned by the standalone Web App. It obtains its
source only through its own signed, server-side ownership checks and preserves
the individual operation's rate limits, feature gates, output verification and
private download rules.

## Explicit exclusions

- `/translate_file` stays outside this catalog. Translation, language choice,
  source validation and delivery require their own asset/runtime contract; the
  existing guarded subtitle/translation workspace is not a safe replay of a
  Bot file command.
- `/pdf_to_images` and `/ocr_image` already have independent Web pages, but
  they are not reclassified by this contract because this batch only repairs
  the reviewed stale/misaligned Document command entrypoints above.
- `docflow|*` callbacks remain governed by
  [`DOCFLOW_CALLBACK_CONTRACT.md`](DOCFLOW_CALLBACK_CONTRACT.md). They retain
  their source-state dispositions and cannot inherit a command navigation
  mapping.
- No change is made to `bot.py`, Core Bridge, provider calls, Bot jobs, Xu,
  PayOS, webhooks, Railway configuration or production execution.

## Verification

- Static audit tests assert every finite entrypoint resolves to the exact
  customer page with `NAVIGATION_ONLY` and never a raw operation API.
- Callback disposition tests assert the Bot `docflow|*` state machine remains
  isolated from the Web navigation catalog.
- Existing Document Operation portal contracts continue to prove signed Web
  ownership, CSRF/idempotency, no bridge/provider/payment execution and
  verified private delivery.
