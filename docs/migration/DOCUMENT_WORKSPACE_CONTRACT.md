# Document & PDF Workspace — Web-native contract

## Mục đích, authority và ranh giới

`/document-workspace` là workspace riêng tư để người dùng lập **brief tài
liệu/PDF**, chia nhỏ các bước xử lý, gắn metadata Asset Vault, self-review và
giữ version history. Nó đưa phần workflow hữu ích của menu PDF/Word trong Bot
vào Web có cấu trúc, nhưng không biến browser hoặc API này thành converter,
OCR engine, translator, Bot bridge hay một kênh giao file thứ hai.

P0.COPYFAST25 là authoring-only. `approved` là self-review của brief/plan,
không phải xác nhận file đã được xử lý. Không có state `queued`, `processing`
hoặc `completed` trong Workspace, không tạo preview, binary output, private
download, job, Xu, wallet, PayOS, webhook hay provider request.

| Surface | Authority | Không được làm trong P0.COPYFAST25 |
| --- | --- | --- |
| `/document-workspace`, `/api/v1/document-workspace/*` | Standalone Web App, signed Web account | Đọc/upload bytes, OCR/translate/convert/render, gọi Bot/Core Bridge/provider, tạo job, charge, output, preview hoặc delivery. |
| `/documents/*`, `/api/v1/document-operations/*` | Existing bounded Web-native deterministic tools | Bị gộp lifecycle/output vào Workspace, bị auto-submit từ plan hoặc bị gọi với URL/blob/path do Workspace giữ. |
| Telegram document flow, `internal_documents`, Bot Xu/payment/job state | Bot | Bị copy vào schema Web, làm browser authority hoặc dùng làm fallback cho Workspace. |

Canonical UI routes:

```text
/document-workspace
/document-workspace/new
/document-workspace/{uuid}
```

Canonical API prefix duy nhất:

```text
/api/v1/document-workspace/*
```

Native route hydration phải chạy trước generic legacy matcher để
`/document-workspace/...` không rơi vào `/documents/*` cũ. Không tạo alias
`/documents/workspace`, `/api/v1/documents`, `/api/v1/features/documents` hay
generic feature endpoint có thể lén execute plan.

## Đối chiếu Bot tĩnh và phân loại bắt buộc

Audit chỉ đọc `D:\TOANAAS\bot telegram\bot.py` ở frozen baseline. Inventory
tĩnh ghi nhận các customer command `doc_tools`, `pdf_to_word`, `image_to_pdf`,
`pdf_to_images`, `compress_pdf`, `split_pdf`, `merge_pdf`, `ocr_image`,
`ocr_pdf`, `translate_file`; các tool test liên quan; callback/menu `main_docs`,
`hint_doc_*`, `docflow|*`; và các bề mặt admin/internal document. Bot không
có document background job canonical nào cần được chuyển sang Workspace.

| Bề mặt Bot | Phân loại P0 Web | Tương đương/ranh giới Web |
| --- | --- | --- |
| `/doc_tools`; `menu|main_docs`, `menu|doc_tools`; `menu|hint_doc_pdf_to_word`, `hint_doc_image_to_pdf`, `hint_doc_compress_pdf`, `hint_doc_split_pdf`, `hint_doc_merge_pdf` | **Native authoring** | Hub Document Workspace cho brief và Plan có operation label. Không nhận Telegram file hoặc tự xử lý file. |
| `docflow|send_more`, `reset_files`, `pop`, `clear`, `ask_pages`, `compress|light|medium|strong`, `confirm`, `run`, `back`, `main` | **Native authoring** cho ý nghĩa workflow, không copy callback | Editor dùng form/revision/lifecycle Web; không tái tạo pending state 10 phút, input Telegram, callback payload hay lời hứa “run”. Page scope/compression note chỉ là instructions. |
| `menu|hint_doc_save_document`, `save_document` trong doc flow | **Existing native separate** | Asset Vault/Memory Center là owner của upload và lưu file. Workspace chỉ chọn metadata Asset Vault đã tồn tại; không thay thế Asset Vault hay storage quota. |
| `/pdf_to_word`, `/image_to_pdf`, `/pdf_to_images`, `/compress_pdf`, `/split_pdf`, `/merge_pdf` | **Existing deterministic separate tool** | Dùng các page `/documents/pdf-to-word`, `/documents/image-to-pdf`, `/documents/pdf-to-images`, `/documents/compress`, `/documents/split`, `/documents/merge` và `/api/v1/document-operations/*` hiện có. Workspace có thể hiển thị link điều hướng rõ ràng, nhưng không auto-call, không chia sẻ operation ID/output/state và không nói plan đã thực thi. `/merge_pdf` của Bot từng planned vẫn được xử lý bằng Web operation độc lập có boundary riêng. |
| `/ocr_image` | **Existing deterministic separate tool** | `/documents/ocr` và `/api/v1/document-operations/ocr-image` là OCR ảnh owner-scoped độc lập. Workspace chỉ điều hướng rõ ràng, không auto-call hay chia sẻ operation ID/output/state. |
| `/ocr_pdf` | **Existing bounded Web-native separate tool** | `POST /api/v1/document-operations/ocr-pdf` nhận một PDF Asset Vault owner-scoped, chỉ khi `WEBAPP_DOCUMENT_OCR_PDF_ENABLED` và local PDFium/Tesseract đều sẵn sàng. Nó tạo TXT private đã xác minh hoặc guarded; không đọc plan Workspace, không charge và không gọi Bot/provider. Xem `PDF_OCR_CONTRACT.md`. |
| `/translate_file` và file-translate callback/target flow | **Guarded/Telegram-only execution** | Workspace có label `translate`, language/target-language và instructions do user viết. Không gửi tài liệu sang translation provider và không nhận file output. Subtitle/Language Workspace vẫn là module riêng cho text/subtitle authoring. |
| `/tool_test_doc_tools`, `/tool_test_pdf_to_word`, `/tool_test_image_to_pdf`, `/tool_test_pdf_to_images`, `/tool_test_compress_pdf` | **TELEGRAM_ONLY** | Đây là Bot/admin smoke/readiness surface; không expose provider/package test hoặc runtime probe trong browser. |
| `/internal_docs`, `/search_internal_doc`, callback `archive|*`, table Bot `internal_documents` | **TELEGRAM_ONLY / admin-only** | Kho hồ sơ nội bộ dùng Telegram file ID, department/retention/admin policy. Không import table, records, file ID hay quyền admin đó vào customer Workspace. |
| `/admin_docs`, `/admin_doc_ip`, `/admin_doc_risk`, `/admin_doc_checklist`, `/admin_doc_b2c`, `/admin_doc_b2b`, `/admin_doc_nda`, `/admin_doc_tax`, `/admin_doc_converter`, `/admin_doc_sources` | **TELEGRAM_ONLY / admin-only** | Tài liệu vận hành, risk, legal, provider/converter readiness không phải customer workflow và không tạo browser control plane mới. |
| `support|consult_type|document`, `ticket|cat|document_pdf`, `feedback|cat|document_pdf` | **Existing native separate** | Support Desk/Tickets giữ taxonomy hỗ trợ. Workspace không chứa ticket, payment proof, customer data cross-account hay escalation. |
| Bot `doc_send_file`, `doc_charge_after_success`, `DOC_COSTS`, Telegram download/reply file, provider/package status | **Guarded/Telegram-only** | Không gọi/đọc/sao chép ledger, provider readiness, Telegram ID, temporary path, output link hoặc successful-charge semantics. |

Bot local helper hiện tạo output và có thể charge sau delivery. P0 Web không
copy phần đó. Các Document Operations Web hiện có là implementation độc lập
với private Asset Vault, idempotency, parser/decoder/output verification và
attachment delivery; chúng cũng không phải child job của Workspace.

## Data model Web-owned

Tất cả ID là UUID opaque. Mọi row chứa `account_id`; snapshot/version/event
chỉ đọc được qua signed Web account sở hữu record. Schema additive đã chọn:

```text
web_document_workspaces
  id, account_id, project_id nullable, title, document_type,
  source_summary, objective, language, target_language nullable,
  tags_json, lifecycle (draft|review|approved|archived), revision,
  created_at, updated_at, archived_at

web_document_workspace_versions
  id, workspace_id, account_id, revision, snapshot_json, created_at

web_document_plans
  id, workspace_id, account_id, ordinal, title,
  operation (organize|split|merge|optimize|image_to_pdf|pdf_to_images|
             pdf_to_word|ocr|translate|convert|other),
  instructions, source_asset_id nullable, reference_asset_id nullable,
  tags_json, state (active|archived), revision,
  created_at, updated_at, archived_at

web_document_plan_versions
  id, plan_id, account_id, revision, snapshot_json, created_at

web_document_workspace_events
  id, account_id, workspace_id, plan_id nullable,
  entity_type, action, revision, created_at
```

`project_id` phải được owner-check với Project Center trước khi liên kết.
`UNIQUE(workspace_id, ordinal)` bảo vệ thứ tự plan; reorder dùng transaction
và ordinal tạm thời để không va chạm. Version snapshot là immutable và bounded;
event/audit chỉ chứa IDs, action, revision và timestamp, không nhân bản
`source_summary`, `objective`, `instructions`, filename/path, provider response
hay bất kỳ text/file nhạy cảm nào.

Không được có cột hoặc JSON field cho raw source/output bytes, storage key,
filesystem path, data URI, remote URL, Telegram file/chat/message ID, Bot job,
provider request/response, OCR/translation text output, wallet Xu, payment,
PayOS order/webhook hoặc download URL.

## Lifecycle và Plan semantics

```text
draft ──submit──> review ──self-review──> approved ──archive──> archived
  ^                    |                    |                       |
  └──── reopen ────────┴────────────────────┴──── restore ───────────┘

active plan ──archive──> archived ──restore──> active
```

- `draft`, `review`, `approved`, `archived` là lifecycle của authoring record;
  không đồng nghĩa xử lý file.
- `approved` chỉ là self-review; không là provider approval, conversion success,
  output acceptance, charge, publish hay delivery. Child plan mutation chỉ được
  cho phép khi parent lifecycle có rule rõ ràng; `archived` luôn khóa mọi plan
  mutation/reorder/estimate ở server cho đến khi restore.
- `operation` là closed planning label, không phải command. `ocr`, `translate`,
  `convert` có thể dùng để mô tả yêu cầu nhưng không mở engine.
- `estimate` chỉ kiểm tra deterministic metadata, lifecycle, revision và plan
  completeness. Nó không parse asset, đếm trang thật, đọc file hoặc báo chi
  phí/thời gian provider.
- Reorder nhận đúng tập plan `active` của một workspace một lần; cross-workspace
  hoặc archived ID bị reject. `source_asset_id`/`reference_asset_id` không thể
  được dùng để thực thi operation sau này chỉ bằng sửa request trên browser.

## API contract

API này dùng standard envelope `ok`, `status`, `message`, `data`,
`error_code`. Mọi response, bao gồm guarded/failure/read-only, phải kèm
boundary flags sau:

```json
{
  "execution": "authoring_only",
  "provider_called": false,
  "ocr_called": false,
  "translation_called": false,
  "output_created": false,
  "job_created": false,
  "payment_started": false,
  "wallet_mutated": false,
  "payment_processed": false
}
```

Concrete endpoint family đã chốt:

```text
GET   /api/v1/document-workspace/summary
GET   /api/v1/document-workspace/policy
GET   /api/v1/document-workspace/references
GET   /api/v1/document-workspace/workspaces?state=&q=&limit=
POST  /api/v1/document-workspace/workspaces
GET   /api/v1/document-workspace/workspaces/{workspace_id}
PATCH /api/v1/document-workspace/workspaces/{workspace_id}
POST  /api/v1/document-workspace/workspaces/{workspace_id}/lifecycle
POST  /api/v1/document-workspace/workspaces/{workspace_id}/restore-version
POST  /api/v1/document-workspace/workspaces/{workspace_id}/plans
PATCH /api/v1/document-workspace/workspaces/{workspace_id}/plans/{plan_id}
POST  /api/v1/document-workspace/workspaces/{workspace_id}/plans/{plan_id}/archive
POST  /api/v1/document-workspace/workspaces/{workspace_id}/plans/{plan_id}/restore
POST  /api/v1/document-workspace/workspaces/{workspace_id}/plans/{plan_id}/restore-version
POST  /api/v1/document-workspace/workspaces/{workspace_id}/plans/reorder
GET   /api/v1/document-workspace/workspaces/{workspace_id}/estimate
GET   /api/v1/document-workspace/events?limit=
GET   /api/v1/document-workspace/history
```

Không có `run`, `execute`, `upload`, `download`, `preview`, `render`, `ocr`,
`translate`, `convert`, `quote`, `confirm payment` hoặc provider endpoint dưới
namespace này. Nếu user bấm một link sang Document Operations, đó là navigation
mới sang route/tool độc lập và phải lấy signed session/CSRF/idempotency riêng;
Workspace không được truyền operation receipt, mutable source URL hay hidden
execution token.

## Asset reference boundary

`GET /references` chỉ trả safe metadata để chọn. Plan persist **chỉ**
`source_asset_id` và `reference_asset_id` là UUID opaque; browser không gửi
filename, MIME, bytes, blob, file path, `storage_key`, `file://`, data URI,
remote URL, Telegram handle hoặc provider handle.

Resolver server-side phải cùng lúc kiểm tra UUID shape, signed account ownership
và `state='active'`. Closed type pairs được phép là:

| Extension | Canonical MIME |
| --- | --- |
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.txt` | `text/plain` |
| `.jpg`, `.jpeg` | `image/jpeg` |
| `.png` | `image/png` |
| `.webp` | `image/webp` |

Mọi pair khác, archived/unavailable row, other-account UUID, duplicate
`source_asset_id == reference_asset_id`, storage-key substitution hoặc absent
Asset Vault boundary đều fail safe. Workspace không mở asset bytes, preview,
thumbnail hoặc download: Asset Vault và Document Operations tự giữ các
capability riêng của chúng.

Khi reference cũ biến mất/archived sau khi snapshot đã được lưu, history có thể
chỉ trả `{ "id": "…", "available": false }`; không được tiết lộ filename,
path, state hay metadata của account khác.

## Security, privacy, configuration và PWA

- Mọi read, version, history, event, Project/Asset reference và estimate yêu
  cầu signed session và server-side ownership. Cross-account UUID trả opaque
  not-found/guarded response như nhau, không leakage account/file metadata.
- Mọi write cần CSRF, request ID, owner-scoped idempotency key giữ tối đa 24 giờ
  và `expected_revision`. Reuse key với payload/fingerprint khác trả `409`;
  receipt không giữ text private/asset metadata nhạy cảm.
- JSON body bị chặn tại ASGI trước parser (tối đa 128 KiB). Các title, tags,
  source/objective/instructions/language và snapshot đều có validation size,
  control-char, depth/list-length limits. Browser validation chỉ là UX; server
  lặp lại toàn bộ check.
- Reject secrets/token/private key/OTP/password, payment/card/CVV/transaction
  proof, URL/path/data URI, provider/Bot/job marker và unbounded rich text ở
  workspace metadata/instructions. Text được render escaped plain text, không
  được follow như link/file source.
- Separate read/write rate-limit scopes, `Cache-Control: no-store, private`
  cho private API, sanitized errors, structured audit action không có content,
  CSRF/IDOR/revision/idempotency checks là mandatory.
- `WEBAPP_DOCUMENT_WORKSPACE_ENABLED` default `true` chỉ vì đây là harmless
  authoring. Explicit `false` phải guard toàn bộ native API/route. Nó **không**
  bật `WEBAPP_DOCUMENT_OPERATIONS_ENABLED`, `WEBAPP_IMAGE_TO_PDF_ENABLED`,
  `WEBAPP_PDF_TO_WORD_ENABLED` hay `WEBAPP_PDF_TO_IMAGES_ENABLED`.
- Service worker chỉ cache public shell. Nó phải exclude `/document-workspace`,
  `/api/v1/document-workspace/*`, `/documents/*`,
  `/api/v1/document-operations/*`, Asset Vault/private files, wallet/payment
  và admin routes. Không cache version/history/asset metadata hay private form
  response.
- Không introduce browser secret, CORS provider call, Core Bridge bearer token,
  second PayOS webhook, Xu ledger, Bot table migration hoặc worker/FFmpeg/import
  into this module.

## P0 verification checklist

- Route/API native works only under signed account; anonymous, CSRF, disabled
  flag, body-cap and rate-limit failures are safe and `no-store`.
- Workspace/plan IDOR, cross-workspace plan ID, cross-account Project/Asset
  UUID, archived reference and unsafe MIME/extension combinations reveal no
  text/path/metadata.
- Create/update/lifecycle/restore/archive/reorder implement expected revision,
  immutable version, account-scoped 24-hour idempotency and exact active-plan
  set semantics; parent archive freezes all changes.
- `references` exposes metadata only for active owner-scoped closed type pairs;
  no raw upload, blob, preview, temporary URL or download leaks through this
  API.
- UI labels `ocr`, `translate` and conversion labels as **plan only**; it has
  no success/output card. Existing `/documents/*` buttons are visibly separate
  tools and never auto-run from a Workspace plan.
- Response/UI contract asserts all authoring boundary flags are false for
  provider/OCR/translation/output/job/payment/wallet. No Bot, Core Bridge,
  provider, PayOS, worker, FFmpeg or document-operation execution import is
  permitted in the new Workspace module.
- PWA regression confirms the private native route/API are excluded from cache;
  browser refresh does not replay mutations or expose a prior account's data.
