# `docflow` callback disposition and Web handoff contract

## Scope

This contract records the frozen Bot document callback family handled by
`handle_doc_tool_callback` in `bot.py`. It is a **source-disposition**
document, not proof that a Web page, document operation or output is equivalent
to a Telegram callback.

The Bot handler reads and mutates `USER_PENDING`: it keeps Telegram file IDs,
the chosen tool, file order, page prompt state and compression label. Its
`run` branch performs the Bot-side document execution/delivery path. The Web
does not import, read, clear, update or replay that state.

## Fixed Web boundary

`/document-workspace` is Web-owned authoring only. A plan may offer a
**navigation-only** handoff to one of the closed routes below:

| Plan intent | Separate Web route | What is deliberately not transferred |
| --- | --- | --- |
| `split` | `/documents/split` | Telegram PDF, page range, pending state, confirmation or output |
| `merge` | `/documents/merge` | Telegram file list/order, pending state, confirmation or output |
| `optimize` | `/documents/compress` | Bot `light`/`medium`/`strong` label, pending PDF or result |
| `image_to_pdf` | `/documents/image-to-pdf` | Telegram images/order, pending state or output |
| `pdf_to_images` | `/documents/pdf-to-images` | Telegram PDF, page choice or delivery |
| `pdf_to_word` | `/documents/pdf-to-word` | Telegram PDF, pending state or delivery |

Every destination starts a new tool flow. It must separately require the
signed Web session, fresh owner-scoped Asset Vault selection, feature gate,
CSRF for writes, idempotency and its own verified private delivery. The link
has no query string, plan UUID, Asset Vault UUID, file/blob/path, page range,
compression profile, token, receipt or hidden form submission.

`ocr`, `translate`, `convert`, `organize` and `other` remain guarded/guidance
in this handoff because their plan label does not identify a safe source/runtime
contract. A document plan never auto-runs any target tool.

## Callback classification

The frozen callback-data inventory contains **22 observed occurrences across
10 concrete callback values**. Repeated keyboard appearances are retained as
separate source evidence in `reports/migration`; the Web disposition is
identical per token. The handler also has `docflow|pop`, `docflow|back_received`
and `docflow|main` branches; they are documented below as handler-level source
states, but are not separate callback-data records in this frozen report.

| Bot callback | Bot source behavior | Web disposition |
| --- | --- | --- |
| `docflow|send_more` | Prompts for another Telegram attachment and retains it in `USER_PENDING`. | `TELEGRAM_PENDING_FILE_STATE`; no Web file handoff. |
| `docflow|reset_files` | Clears pending files/options before asking for a new file. | `TELEGRAM_PENDING_FILE_STATE`; no Web or Asset Vault mutation. |
| `docflow|pop` | Removes the latest pending Telegram file. | `TELEGRAM_PENDING_FILE_STATE`; no Web equivalent is claimed. |
| `docflow|clear` | Clears the pending document list/options. | `TELEGRAM_PENDING_FILE_STATE`; not a browser document operation. |
| `docflow|ask_pages` | Enters the Bot page-range prompt for its pending PDF. | `TELEGRAM_PENDING_PAGE_STATE`; `/documents/split` requires fresh source and page input. |
| `docflow|back` | Clears/redraws a Telegram message/menu. | `TELEGRAM_MESSAGE_NAVIGATION`; a fresh Web workspace is not restoration of Bot state. |
| Handler-only `docflow|pop`, `docflow|back_received`, `docflow|main` branches | Removes a pending file or redraws a Telegram pending-file summary/main menu. | `TELEGRAM_PENDING_FILE_STATE` / `TELEGRAM_MESSAGE_NAVIGATION`; no Web equivalent is claimed. |
| `docflow|compress|light`, `medium`, `strong` | Stores a Bot compression label on a pending Telegram PDF. | `PROFILE_SEMANTICS_MISMATCH`; Web PDF Optimize has one verified structural profile and does not reproduce these labels. |
| `docflow|confirm` | Validates Bot pending files/options and renders a Telegram confirmation. | `TELEGRAM_PENDING_CONFIRMATION`; no Web execution/charge confirmation. |
| `docflow|run` | Starts the Bot pending document execution/delivery branch. | `BOT_EXECUTION_DELIVERY_BOUNDARY`; no Workspace/plan/browser replay. |

Every row stays `NEEDS_FEATURE_DISPOSITION` in the static audit with
`NO_RUNTIME_CLAIM`. This is intentional: classifying a callback more precisely
must not raise static Web coverage or be presented as feature completion.

## Explicit non-goals

- No edit to `bot.py`, Bot `USER_PENDING`, Telegram message/file IDs, Bot
  document records or Bot test surfaces.
- No Core Bridge request, provider call, wallet/Xu logic, PayOS/webhook,
  browser secret or second output-delivery path.
- No prefilled Asset Vault ID, source URL, blob, file path, temporary download
  URL, output/job receipt or automatic form submit in a handoff link.
- No claim that a Bot local-engine success text proves a Web operation output.

See also [`DOCUMENT_WORKSPACE_CONTRACT.md`](DOCUMENT_WORKSPACE_CONTRACT.md)
and the individual Document Operations contracts for owner-scoped execution and
delivery rules.

Finite Bot command entrypoints that may open a new Document Operations page are
separately constrained by
[`DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md`](DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md).
That catalog never changes the `docflow|*` source-state dispositions above.
