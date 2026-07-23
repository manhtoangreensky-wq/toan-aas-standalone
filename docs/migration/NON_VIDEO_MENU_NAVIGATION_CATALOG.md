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
| `menu|main_profile`, `menu|hint_profile` | `/account` | signed customer | opens the independently signed Web account; no Telegram profile, referral identity, reward record or Bot context |
| `menu|hint_ai_prompt` | `/prompt-studio` | signed Web-native customer | starts a fresh prompt brief; no model/provider call from navigation |
| `menu|main_memory`, `freehub|docs`, `freehub|notes` | `/notes` | signed Web-native customer | opens a fresh Memory Center; no Bot notes, quota, add-on, Free Hub or Telegram context |
| `menu|hint_note`, `menu|hint_search_note`, `memory|create`, `memory|list`, `memory|search`, `memory|delete_start` | `/notes` | signed Web-native customer | starts independent Web create/search/archive flows; no Bot pending text, query, note ID or mutation is replayed |
| `menu|hint_remind` | `/reminders` | signed Web-native customer | opens independent Web reminders; no Bot reminder, Telegram identity or notification delivery is transferred |
| `menu|guide_credits` | `/wallet` | canonical read | no checkout, Xu write, pricing change or webhook |
| `menu|main_topup`, `menu|hint_naptien` | `/wallet/topup` | canonical payment bridge guard | customer navigation only; no Bot amount/order, manual top-up, Xu credit, PayOS settlement or webhook replay |
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

## Separately guarded Feedback → Support Desk entry

The following nine exact Bot feedback entries may only open a fresh signed
`/support` form. They are private static-audit source evidence, not public
browser callbacks. No raw callback or category is carried in a route, query,
fragment, form, storage, API request or Web support record; the customer must
explicitly choose a Web category and submit a new owner-scoped case.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `feedback|start` | `/support` | signed Web-native customer | opens a blank support intake; no Bot feedback pending/text/classifier/ticket/admin-alert state |
| `feedback|cat|payment_topup`, `feedback|cat|package_combo`, `feedback|cat|refund` | `/support` | signed Web-native customer | opens a blank Web support intake; no payment/refund request, bill/TXID, Xu, PayOS, ledger or automatic action |
| `feedback|cat|image_error`, `feedback|cat|video_error`, `feedback|cat|document_pdf` | `/support` | signed Web-native customer | opens a blank support intake; no image/video/document source, provider, job, output or execution action; `video_error` is only a support taxonomy label |
| `feedback|cat|feature_request`, `feedback|cat|other` | `/support` | signed Web-native customer | opens a blank support intake; no Bot selected category, pending text, ticket/lead/attachment, notification or delivery state |

`feedback|cancel`, all unknown/case/suffix/extra-segment values and every
dynamic `feedback|cat|{*}` template remain fail-closed source-review records.
They cannot reset a Web form or inherit `/support`.

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

## Separately guarded Admin ERP category navigation

The following exact administrator-only Bot menu values can open only a fresh,
canonical-role-checked Admin ERP read route. They live in the private static
auditor, not in the customer-facing menu catalog. A destination does not carry
the Telegram identity or role, Bot menu/pending context, command text,
finance/provider snapshot, package/user selector, payment/Xu/ledger/PayOS
state, job/runtime state, secret or any write authority into Web.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `menu|admin`, `menu|admin_overview` | `/admin` | signed canonical admin read | opens a fresh ERP overview; no Bot overview/finance snapshot or Admin command is replayed |
| `menu|operator` | `/admin` | signed canonical admin read | opens a fresh ERP overview; the separately authorized Web Support Operations route is not inherited, and no Bot operator command, automation or runtime action is replayed |
| `menu|finance` | `/admin/finance` | signed canonical admin read | opens Finance & Revenue independently; no Bot period, ledger, payment, Xu, PayOS or export data |
| `menu|admin_packages` | `/admin/packages` | signed canonical admin read | opens the Web package read surface; no package code/user, grant/revoke, entitlement, order or checkout state |
| `menu|admin_provider`, `menu|admin_provider_status` | `/admin/providers` | signed canonical admin read | opens providers read metadata only; no Bot status snapshot, secret, test, freeze or unfreeze action |
| `menu|admin_provider_usage` | `/admin/provider-cost` | signed canonical admin read | opens provider-cost metadata only; no Bot usage snapshot, secret, test, freeze, billing or runtime action |

Any case variant, suffix, `menu|admin_confirm_*`, `menu|admin_provider_test`,
freeze/smoke/provider custom action, dynamic finance/tax action or unreviewed
`menu|admin_*` value remains fail-closed. It cannot inherit these Admin routes
or become a browser-side control.

## Separately guarded Tax Readiness & Accounting Guidance

The following finite administrative buttons remain private to the static
auditor. They only open a fresh, literal guidance page after the canonical
signed-admin route check. They do not pass a Telegram identity, Bot command
text, finance row, tax profile, period, calculation, report, CSV/file, payment
reference, Xu ledger, PayOS state, provider state, archive row or delivery
state to the browser.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `menu|finance_help`, `menu|finance_tax`, `menu|tax_checklist`, `menu|tax_custom_help` | `/admin/finance/tax-readiness` | signed canonical admin read | fresh command/checklist guidance only; no Bot command text, calculation, finance read, export/file, tax profile/compliance mutation, payment/ledger/provider action or runtime claim |

The four literals above are the complete allow-list. Every other
`menu|finance_*` or `menu|tax_*` value, including case variants, suffixes,
period selectors and export actions, remains fail-closed and cannot inherit
this route.

## Separately guarded Postback Readiness

The exact Bot `menu|hint_postback_setup` callback is a private administrator
hint, not a browser configuration action. It opens only a fresh, static
`/admin/growth/postback-readiness` guidance route after canonical signed-admin
authorization. It transfers no Telegram identity, Bot hint context, connection
material, credential, network value, affiliate/job reference, event,
attribution, revenue, reward, payout, wallet/Xu, payment/PayOS, provider or
runtime state to the Web App.

| Bot source action | Web destination | Web authority | Boundary preserved |
| --- | --- | --- | --- |
| `menu|hint_postback_setup` | `/admin/growth/postback-readiness` | signed canonical admin guidance | fresh preparation/handoff guidance only; no configuration, connection material, event receipt/test/replay, affiliate/job read, attribution/reward/payout, financial/provider action or runtime claim |

The corresponding Bot `/postback_setup` command remains a canonical
source-review record. It cannot inherit this guidance route, an Admin Growth
directory, a bridge module or a browser-side configuration/event control.

## Separately guarded Billing navigation

`menu|billing` is deliberately outside the customer catalog and only appears
in the static auditor's private finite registry. It may open a fresh
`/admin/payments` read route only after canonical signed-admin authorization;
it does not transfer a Telegram admin identity, Bot billing/manual-payment
menu, pending deposit, payment reference, wallet/Xu ledger, PayOS/webhook
state, provider state or write authority to the browser. The detailed record
is generated in `BILLING_MENU_CALLBACK_CONTRACT.md`.

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
- `menu|tax_estimate`, `menu|tax_config`, period-specific tax estimate/export
  actions, `finance_compliance*`, `archive|dept|tax_invoice`, every other
  `menu|finance_*` or `menu|tax_*` value and `menu|clear_stale_jobs_help` remain
  outside this catalog. They need separate canonical finance/job/private-file
  contracts and never inherit a browser route from a namespace or label.
- Translation, payment/admin writes, provider controls and any other dynamic
  menu template remain source-state/authority reviewed or `TELEGRAM_ONLY`;
  none receive a fallback browser route.
