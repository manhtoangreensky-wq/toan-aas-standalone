# Non-video menu navigation catalog

This is the first ordered batch of the P0 `menu` disposition. It maps only
finite, source-reviewed Bot buttons that can open a **fresh** signed Web
workspace without importing Bot context. The private callback identifiers live
only in the static migration auditor; the browser receives the separate,
closed `menu_capabilities` catalog from `/api/v1/catalog`.

Every row is `NAVIGATION_ONLY`. It is not a claim that a Bot conversation,
file, provider call, job, Xu balance mutation, PayOS checkout, entitlement or
output has been copied into the browser.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `menu|guide_quick_start` | `/features` | signed Web-native customer | opens the intent-led Guided Start/catalog; no Bot guide prose, child callback, conversation or execution state |
| `menu|main_ai` | `/chat` | signed Web-native customer | starts an empty Web chat workspace; no Telegram conversation/context |
| `menu|hint_ai_prompt` | `/prompt-studio` | signed Web-native customer | starts a fresh prompt brief; no model/provider call from navigation |
| `menu|main_memory`, `freehub|docs`, `freehub|notes` | `/notes` | signed Web-native customer | opens a fresh Memory Center; no Bot notes, quota, add-on, Free Hub or Telegram context |
| `menu|hint_note`, `menu|hint_search_note`, `memory|create`, `memory|list`, `memory|search`, `memory|delete_start` | `/notes` | signed Web-native customer | starts independent Web create/search/archive flows; no Bot pending text, query, note ID or mutation is replayed |
| `menu|hint_remind` | `/reminders` | signed Web-native customer | opens independent Web reminders; no Bot reminder, Telegram identity or notification delivery is transferred |
| `menu|guide_credits` | `/wallet` | canonical read | no checkout, Xu write, pricing change or webhook |
| `menu|hint_pricing` | `/pricing` | signed customer | reference-only navigation; no order or payment action |
| `menu|hint_doc_pdf_to_word` | `/documents/pdf-to-word` | signed Web-native customer | Web Asset Vault source; no Telegram file or pending confirmation |
| `menu|hint_doc_image_to_pdf` | `/documents/image-to-pdf` | signed Web-native customer | Web Asset Vault source/order; no Telegram upload queue |
| `menu|hint_doc_compress_pdf` | `/documents/compress` | signed Web-native customer | Web-owned compression workflow; no Telegram profile/choice |
| `menu|hint_doc_split_pdf` | `/documents/split` | signed Web-native customer | Web-owned source/page selection; no Telegram page range |
| `menu|hint_doc_merge_pdf` | `/documents/merge` | signed Web-native customer | signed owner chooses Web Asset Vault order |
| `menu|hint_doc_save_document` | `/asset-vault` | signed Web-native customer | Web private vault only; not Bot storage quota/add-on settlement |
| `menu|hint_image_tools`, `menu|guide_image_ai` | `/image-studio` | signed Web-native customer | opens a new Web image workspace; no Bot image state/provider call |
| `menu|image_prompt_start` | `/image/prompt-composer` | signed Web-native customer | creates a fresh prompt direction; no pending Telegram image |
| `menu|image_edit_start` | `/image/edit` | signed Web-native customer | independently selects owner-scoped Asset Vault input |
| `menu|image_upscale_start` | `/image/upscale` | signed Web-native customer | retains the Web runtime guard; does not call a provider by navigation |
| `menu|guide_music_add` | `/media-workspace` | signed Web-native customer | opens Web audio briefing/library; no Bot product context or media cache |
| `menu|guide_faq` | `/support` | signed customer | starts owner-scoped Web support; no raw Telegram ID, Bot chat/support/refund state or automatic action |
| `menu|memory_storage_cleanup` | `/account/workspace-care` | signed Web-native customer | opens navigation-only Web guidance; no Bot storage cleanup, quota, add-on, TTL, archive or delete action is replayed |

## Separately guarded System & Data navigation

The following finite administrative buttons remain private to the static
auditor. They only open a fresh route after its server-side authority check;
they do not pass a Telegram admin identity, Bot system menu, command, runtime
payload, database path, backup artifact, archive row, secret, provider state,
payment, Xu or job state to the browser.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `menu|system`, `menu|system_data_status_help` | `/admin/system` | signed canonical admin read | system navigation only; no settings/data write or Bot state replay |
| `menu|system_runtime_help`, `menu|system_health_help` | `/admin/runtime` | signed canonical admin read | runtime read route only; no healthcheck, restart, worker/provider or deploy action |
| `menu|system_backup_help` | `/admin/backups` | signed canonical admin read | metadata route only; no create/delete/restore/download backup action |
| `menu|internal_archive` | `/admin/internal-documents` | signed Web-local admin | independent Web private archive; no Bot archive record/file ID/Telegram attachment is replayed |

## Explicitly deferred

- `menu|guide_video_ai` and `menu|guide_guided_video` remain explicit
  `GUIDED_VIDEO_MENU_DEFERRED` / `NEEDS_FEATURE_DISPOSITION` records with
  `VIDEO_MENU_LAST`; they do not fall back to Dashboard or a generic Web Video
  route. The requested video-menu implementation is last and requires its own
  finite source catalog.
- All remaining `menu|main_video`, `menu|video_*` and video execution actions
  remain outside this batch for the same reason.
- `menu|memory_storage_status` and `menu|memory_storage_addon` remain
  `TELEGRAM_ONLY`: the former reads canonical Bot quota/add-on state and the
  latter enters the Bot storage/PayOS settlement flow. Neither is a Web Notes,
  Asset Vault or wallet route.
- `menu|memory_storage_cleanup` opens only the signed Web Workspace Care
  directory. It remains guidance: the Bot action gives no delete capability,
  and the Web route does not clean Bot storage, inspect quota or map to archive
  or Asset Vault retention.
- `menu|billing`, every `menu|tax_*` action and `menu|clear_stale_jobs_help`
  remain outside this catalog. They need separate canonical finance/job
  contracts and never inherit a browser route from a namespace or label.
- Translation, payment/admin writes, provider controls and any other dynamic
  menu template remain source-state/authority reviewed or `TELEGRAM_ONLY`;
  none receive a fallback browser route.
