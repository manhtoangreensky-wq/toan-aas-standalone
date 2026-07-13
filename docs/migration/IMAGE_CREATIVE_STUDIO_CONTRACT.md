# Image Creative Studio — Web-native authoring contract

## Mục đích và authority

Image Creative Studio là workspace riêng tư cho **art direction**: tổ chức
creative brief, style/negative direction, biến thể prompt, reference Asset
Vault, self-review và version history. Nó đưa phần lập ý tưởng hữu ích của
luồng ảnh Telegram vào một giao diện Web có cấu trúc, nhưng không biến Web App
thành một image engine hoặc một bản giả lập chat Telegram.

| Surface | Authority | Không được làm trong P0.COPYFAST24 |
| --- | --- | --- |
| `/image-studio`, `/api/v1/image-studio/*` | Standalone Web App, signed Web account | Render/tạo/sửa ảnh, tạo thumbnail/preview, upload binary, gọi Bot/Core Bridge/provider, job, Xu, PayOS, charge hoặc delivery |
| Legacy `/image/*` và feature compatibility | Existing legacy/deterministic surface | Bị alias thành Image Creative Studio hoặc dùng artboard để giả báo image đã tạo |
| `/image/edit` Image Operations | Independent deterministic Web-native operation | Bị gọi gián tiếp, chia sẻ lifecycle/output hoặc tự nhận mọi Asset Vault reference là input xử lý |
| Bot/provider image state | Bot/provider | Bị copy thành Web ledger, provider state, job/history hoặc output state |

Canonical Web routes là:

```text
/image-studio
/image-studio/new
/image-studio/{uuid}
```

Canonical API là **một namespace duy nhất**:

```text
/api/v1/image-studio/*
```

API dùng resource names `artboards` và nested `directions`, cùng các read-only
resources an toàn như `summary`, `policy`, `references` và `events`. Router
thực thi phải giữ prefix và danh từ này; không tạo alias `/image/*`,
`/api/v1/image`, `/api/v1/features/image` hoặc endpoint generic feature để
lén thực thi một direction. Concrete verb/path list phải được router và tests
chốt trong cùng PR, thay vì tài liệu này tự bịa endpoint chưa có.

## Đối chiếu Bot và phạm vi guarded

Inventory tĩnh có các command quản trị `/ai_image`, `/ai_image_edit`,
`/image_edit_public_open` và `/image_edit_public_close`; các luồng/callback
ảnh còn lại bao gồm create, edit, image-to-image, upscale, remove-background,
history, provider/model, quote/status và delivery. Những surface đó phụ thuộc
vào Telegram conversation state, provider/model readiness, job, wallet hoặc
delivery, nên không được coi là Web-native engine chỉ vì một artboard tồn tại.

| Semantics Bot | Tương đương Image Creative Studio | Boundary bắt buộc |
| --- | --- | --- |
| Image create/prompt/style | Artboard với creative brief, style/negative direction và Direction variants | Metadata để biên tập; không call model, không render ảnh. |
| Image edit/image-to-image | Direction chứa edit instruction và optional Asset Vault reference IDs | Không nhận bytes/URL, không thay đổi source hoặc tạo bản edit. |
| Upscale/remove background/retouch | Direction operation + acceptance note để lập kế hoạch | Vẫn guarded; không claim local/AI processing hay output. |
| History/retry/preview/download | Immutable artboard/direction version + audit-safe event | Không phải Bot job history, preview hay delivery history. |
| Provider/model/quote/charge/status | Không có native endpoint P0 | Giữ `COPIED_GUARDED` hoặc `TELEGRAM_ONLY`; không expose browser provider control. |
| Admin public-open/close | Không có write endpoint trong Studio | Giữ admin compatibility guard; Studio không thay đổi feature flag của Bot. |

Khi route native hydrate, nó phải chạy trước generic legacy Image matcher để
`/image-studio/...` không rơi vào workflow `/image/*`. Giao diện legacy vẫn
phải công khai đúng readiness/guard của nó; không được chuyển người dùng sang
Studio rồi hiển thị `completed`, preview hoặc download giả.

## Data model: artboard và direction

Mỗi record thuộc đúng một signed Web account. IDs là UUID opaque; tất cả các
snapshot/event đều owner-scoped. Các bảng additive được dùng cho P0:

```text
web_image_artboards
  id, account_id, project_id nullable, title, image_intent, language,
  aspect_ratio, output_format, creative_brief, style_direction,
  negative_direction, tags_json, lifecycle, revision, created_at,
  updated_at, archived_at

web_image_artboard_versions
  id, artboard_id, account_id, revision, snapshot_json, created_at

web_image_directions
  id, artboard_id, account_id, ordinal, title, operation, prompt_text,
  edit_instructions, composition_notes, negative_direction, asset_id nullable,
  reference_asset_id nullable, tags_json, state, revision, created_at,
  updated_at, archived_at

web_image_direction_versions
  id, direction_id, account_id, revision, snapshot_json, created_at

web_image_studio_events
  id, account_id, artboard_id, direction_id nullable, entity_type, action,
  revision, created_at
```

`project_id` is only a Web Project Center reference after a server-side owner
check. `asset_id` and `reference_asset_id` are opaque **Asset Vault metadata
references**, never a browser filename, filesystem path, storage key, hash,
signed URL, provider ID, Telegram file ID or a raw image blob.

An artboard represents one creative direction. A direction is a manually
authored variant under that artboard. `ordinal` controls display order and
must be transactionally unique among directions of an artboard. Version
snapshots are immutable and bounded; audit events retain action/revision/IDs
only, not briefs, prompts, notes or Asset Vault metadata.

## Lifecycle and exact boundary facts

```text
draft ──submit──> review ──self-review──> approved ──archive──> archived
  ^                    |                    |                       |
  └──── reopen ────────┴────────────────────┴──── restore ───────────┘
active direction ──archive──> archived ──restore──> active
```

`approved` is only a self-review marker for an art direction. It is not
approval to generate, edit, process, publish, quote, charge or deliver an
image. An artboard in `review` or `approved` must be explicitly reopened
before content edits; an archived artboard freezes every child mutation,
reorder and deterministic review action at the server. Archiving a direction
does not erase its version history. Restoring a version always creates a new
revision; it never overwrites history.

Every successful read, mutation, lifecycle receipt and deterministic review
response must keep these exact facts in its `data` envelope:

```json
{
  "execution": "authoring_only",
  "provider_called": false,
  "image_created": false,
  "output_created": false,
  "job_created": false,
  "payment_started": false,
  "wallet_mutated": false,
  "payment_processed": false,
  "media_uploads": false,
  "browser_media_url": false,
  "preview_available": false,
  "output_delivery": "guarded"
}
```

Extra fields are allowed only when they cannot contradict these facts. The UI
validates this full boundary before rehydrating a success state and must not offer a
player, thumbnail/preview URL, image download, generated Asset Vault item,
job card, payment receipt or `completed` state. A deterministic estimate, if
implemented, may count text/directions for review only and retains this same
boundary.

## Asset Vault reference-only policy

Studio accepts an Asset Vault reference only when the caller owns an **active,
verified image metadata record**. The server resolves the opaque UUID and
returns only minimal display-safe metadata needed for a picker; it does not
stream, copy, decode, transform, expose or persist the blob in the Studio.

- Browser sends opaque IDs, never bytes, multipart files, file paths,
  `file:`/`data:` URLs, image URLs, provider links, storage keys or hashes.
- A cross-account, archived, non-image or missing Asset Vault record gives the
  same safe not-found/guarded result and reveals no filename or metadata.
- References are non-executing: selecting one does not upload it, charge,
  create an output, stage a Bot input or permit an Image Operations call.
- The Asset Vault file remains independent and immutable. Archiving/deleting a
  reference must not mutate artboard history; the UI renders the relationship
  as unavailable metadata rather than fabricating a preview.
- No public asset link, browser cache, URL reveal, blob conversion or image
  extraction belongs to this module.

## Security, privacy, configuration and PWA

`WEBAPP_IMAGE_STUDIO_ENABLED` controls availability of this workspace. Its
default-enabled authoring state is safe: setting it to `true` enables only the
signed-account metadata workspace described here; it never enables an image
provider, Bot bridge, Asset Vault upload, Image Operations, job, payment or
delivery path.

- Signed session and server-side account ownership are mandatory for every
  summary, artboard, direction, version, event, Project reference and Asset
  Vault reference. Cross-account UUIDs return opaque not-found results.
- Each mutation requires CSRF, request ID, account-scoped idempotency key and
  optimistic `expected_revision`. Reusing a key for different canonical
  payloads is a conflict; replay receipts are scrubbed to IDs/state/revision
  and the exact boundary facts above.
- Raw JSON write bodies are capped at **128 KiB before parsing**. Text,
  tags, directions and version snapshots must be independently bounded.
  Read/write rate scopes are separate and private API responses use
  `Cache-Control: no-store, private`.
- Reject unsafe controls/markup execution vectors; URL/path/data URI/provider,
  Bot/job/media handles; secret/token/private key/password/OTP; card/CVV;
  payment proof/bill/TXID/QR; and unbounded rich text. Browser validation is
  convenience only; server repeats all enforcement.
- No request may contain a provider credential, webhook signature, Core Bridge
  bearer/HMAC secret, payment secret or direct external fetch target.
- PWA caches public shell only. It must exclude `/image-studio`,
  `/api/v1/image-studio`, Asset Vault private APIs/downloads and all private
  record data from precache and runtime cache.

## Explicit non-goals

- No AI/provider image create/edit/image-to-image/upscale/remove-background,
  inpainting, retouch, face processing, prompt execution, model selection or
  external fetch.
- No Bot/Core Bridge/Telegram call, provider status, worker queue, job retry,
  quote, Xu ledger, PayOS order/webhook, manual top-up or refund.
- No upload, raw media persistence, public preview/gallery, thumbnail render,
  image output/download/export, asset delivery or browser-canvas output.
- No claim that guarded Bot image workflows became available or were migrated
  to standalone Web execution.

## P0 verification checklist

- Route/API namespace is isolated from `/image/*`; native hydration precedes
  legacy matching and PWA has no private cache path.
- Feature flag off is guarded/no-store; flag on still returns only the exact
  authoring boundary facts and never widens execution authority.
- Anonymous, CSRF, body-cap and rate-limit failures do not create a record;
  owner isolation covers artboards, directions, versions, events, Project and
  Asset Vault reference IDs.
- Create/update/lifecycle/reorder/archive/restore/restore-version semantics
  enforce idempotency, revision conflict, immutable history and parent freeze.
- Asset Vault tests prove opaque ID-only reference, active image owner check,
  no source bytes/URL/path/hash leakage and no mutation of the referenced file.
- Static/API tests assert no Bot/Core Bridge/provider/HTTP client/subprocess,
  job/wallet/PayOS imports; no output/preview/download/`completed` state; and
  the UI checks `execution=authoring_only`, `provider_called=false`,
  `image_created=false`, `output_created=false` before showing a safe result.
