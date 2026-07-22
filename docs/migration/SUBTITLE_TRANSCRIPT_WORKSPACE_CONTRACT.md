# Subtitle, Transcript & Language Workspace — Web-native contract

## Mục đích và ranh giới

`/subtitle-studio` là workspace riêng tư để **biên tập thủ công** timeline
phụ đề, transcript review, bản dịch song ngữ và dubbing direction. Nó chuyển
những phần hữu ích của luồng Bot—subtitle, translate, ASR, SRT/VTT và dubbing
configuration—thành một editor Web có version history, thay vì giả lập một
engine media trong browser.

P0 này không nhận, đọc, stream hay xử lý **raw bytes** audio/video. Một signed
owner có thể chọn một **tham chiếu metadata** tới Asset Vault của chính họ khi
tạo project (`manual` hoặc `asset_reference`), sau khi tự xác nhận quyền sử
dụng. Tham chiếu đó chỉ lưu UUID opaque, lifecycle revision và attestation;
không lưu filename gốc, path, URL, hash, storage key, Telegram ID hay bytes.
Vì vậy, “ASR” chỉ là intent review/transcript nhập thủ công; “translate” là
text song ngữ do người dùng biên tập; và “dubbing” chỉ là direction/script đã
được review. Không state nào được gọi là `completed`, không có player,
preview, audio/video output, job, Xu, PayOS hoặc provider call.

| Surface | Authority | Không được làm |
| --- | --- | --- |
| `/subtitle-studio`, `/api/v1/subtitle-studio/*` | Web App, signed Web account | Gọi Bot/Core Bridge/provider, upload/stream media, đọc Asset Vault bytes, ASR/TTS/translate/render/mux, tạo job/charge/delivery |
| Legacy `/subtitle`, `/translate`, `/dubbing`, `/asr` | Existing guarded/Core compatibility surface | Bị thay bằng alias của native editor hoặc được coi là engine sẵn sàng |
| Bot provider/job/voice tables | Bot/provider | Bị copy thành Web ledger, provider state, job hoặc output state |

Legacy compatibility pages có thể hiện một **plain navigation link** tới form
`/subtitle-studio/new`, với một query `intent` cố định đã allowlist:

| Legacy route | New-project query |
| --- | --- |
| `/subtitle`, `/subtitle/create` | `?intent=subtitle` |
| `/translate` | `?intent=translation` |
| `/asr` | `?intent=asr_review` |
| `/dubbing` | `?intent=dubbing_direction` |

Query này chỉ chọn sẵn nhãn mục đích cho form project mới. Nó không mang theo
prompt, caption, upload, media, account state, Core Bridge result hay status
từ legacy flow; giá trị thiếu/sai luôn về `subtitle`. Đây không phải redirect
hay alias: legacy route và contract guarded/Core của nó vẫn giữ nguyên.

## Đối chiếu Bot tĩnh

Inventory tĩnh ghi nhận các command customer như `/translate`,
`/translate_text`, `/translate_file`, `/translate_audio`, `/translate_voice`,
`/dubbing_help`, `/subtitle_status` và `/subtitle_dub_status`; callback có
`vfinal|combo_asr`, `vfinal|subtitle_asr`, `vfinal|subtitle_manual`,
`vfinal|subtitle_script`, `vfinal|translate_*`, `videodub|subtitle_editor` và
những callback output/preview/link media. Các surface hiện đều là
`COPIED_GUARDED`, trừ tool test/admin smoke vốn `TELEGRAM_ONLY`.

| Semantics Bot | Tương đương Web-native | Boundary |
| --- | --- | --- |
| Tạo/chỉnh phụ đề, `subtitle_manual`, `subtitle_script` | Project và cue có timestamp/text/speaker/note | Manual authoring; không ASR hay burn subtitle vào video. |
| Translate text/file/subtitle, chọn ngôn ngữ | Cue giữ cặp source/translated text cùng language-pair metadata; project mới có thể tham chiếu metadata Asset Vault của chính owner | Người dùng tự biên tập. Không gửi nội dung hay file bytes tới translation provider. |
| ASR/combo ASR | Intent `asr_review` với transcript/timing được người dùng nhập hoặc chỉnh sửa | Không upload audio, không gọi speech-to-text, không tuyên bố transcript là máy nhận dạng. |
| Video dubbing, speed/type/voice setting | Intent `dubbing_direction` với script, timing intent, pronunciation và voice-direction note | Không TTS, clone, voice profile provider, mux hoặc export media. |
| SRT/VTT | Server validation và private text export từ cue do người dùng tự nhập | Export chỉ là văn bản do user author, có `execution=authoring_only`; không phải output engine/delivery. |
| Bot preview, output, job download, link/upload media, quote/charge/status | Không có surface native ở P0 | Giữ legacy guarded hoặc `TELEGRAM_ONLY`; không mở shortcut Web. |
| Admin public-open/close/status/curl và `/tool_test_*` | Không có endpoint workspace | Giữ admin compatibility guard/`TELEGRAM_ONLY`; không expose provider controls. |

Bot inventory còn cho thấy `ASR_PROVIDER`, `TRANSLATE_PROVIDER`, ShopAIKey
audio transcription/translation/dubbing endpoints, Key4U/Minimax/Fish Audio
và các `*_jobs`/`voice_profiles` là authority ngoài Web. Chúng không xuất hiện
trong schema, ENV hay imports của module này.

## Data model đã chọn

Tất cả ID là UUID opaque, mọi bản ghi có `account_id`, `created_at`,
`updated_at`, `revision`; text riêng tư không đi vào audit detail hoặc receipt
idempotency.

```text
web_subtitle_projects
  id, account_id, project_id nullable, title, source_language,
  target_language nullable, caption_format (srt|vtt),
  intent (subtitle|translation|asr_review|dubbing_direction), context,
  source_mode (manual|asset_reference), source_asset_id nullable,
  source_asset_lifecycle_revision nullable, source_rights_confirmed,
  source_attested_at nullable,
  tags_json, lifecycle (draft|review|approved|archived), revision,
  created_at, updated_at, archived_at

web_subtitle_project_versions
  id, project_id, account_id, revision, snapshot_json, created_at

web_subtitle_cues
  id, project_id, account_id, ordinal, start_ms, end_ms,
  speaker nullable, source_text, translated_text nullable, notes nullable,
  state (active|archived), revision, created_at, updated_at, archived_at

web_subtitle_cue_versions
  id, cue_id, account_id, revision, snapshot_json, created_at

web_subtitle_studio_events
  id, account_id, project_id nullable, cue_id nullable,
  entity_type, action, revision, created_at
```

`project_id` chỉ được liên kết sau owner check với Project Center. Một cue giữ
cặp source/translated text cùng timing, giúp review song ngữ và dubbing
direction không cần copy text qua provider khác. `source_asset_id` là UUID
opaque nội bộ, chỉ hợp lệ khi cùng `account_id`, `state='active'`, lifecycle
revision khớp và MIME/extension nằm trong allowlist. Không có cột raw
`media_url`, storage path/key, original filename, SHA/hash, Telegram/provider
ID, provider request/response, voice ID, audio URL, output URL, job ID, Xu,
charge hoặc payment.

Ràng buộc trọng yếu:

- `UNIQUE(project_id, ordinal)` cho cue; archived cue đi vào ordinal range
  tách biệt, reorder dùng transaction với ordinal tạm thời để không va chạm.
- Cue active có `0 <= start_ms < end_ms`, duration tối đa có giới hạn và
  timestamps không overlap trong project. Tất cả text/label/tag bounded; tối
  đa 500 cues/project; giới hạn này giữ response owner-scoped và text export
  trong budget an toàn của P0.
- Version snapshot immutable và bounded; event chỉ lưu action/revision/IDs,
  không sao chép transcript/dịch/script.
- `source_mode=manual` chỉ canonical khi bốn cột source còn lại là
  `NULL`/`NULL`/`0`/`NULL`. Với `asset_reference`, server owner-scope đúng một
  Asset Vault item active,
  kiểm tra cặp MIME/extension chính xác (`mp4`, `mov`, `webm`, `mp3`, `wav`,
  `m4a`, `ogg`, `txt`, `srt`, `vtt`) và ghi metadata projection tối thiểu.
  Reference không được retarget qua update/restore; lifecycle mismatch hoặc
  archive trở thành unavailable, không leak nguồn của account khác.
- Persisted source shape là fail-closed: `asset_reference` phải có UUID chuẩn,
  lifecycle revision integer dương, rights integer đúng `1` và UTC ISO
  attestation; mọi mode/field legacy hoặc direct-DB mismatch khác trả
  `language_source.mode=guarded` với metadata redacted. Project/cue writer và
  lifecycle writer từ chối `WEB_SUBTITLE_LANGUAGE_SOURCE_GUARDED`, nên không
  thể âm thầm rewrite record đó thành `manual`.

## Lifecycle, API và response boundary

```text
draft ──submit──> review ──self-review──> approved ──archive──> archived
  ^                    |                    |                       |
  └──── reopen ────────┴────────────────────┴──── restore ───────────┘

active cue ──archive──> archived ──restore──> active
```

`approved` chỉ là self-review metadata; nó không phải approval ASR, translation,
TTS, render, payment hay publish. Sửa content khi project ở `review` phải reopen
về `draft`; `approved` khóa child mutations cho đến khi reopen. Archive parent
khóa toàn bộ cue mutation/reorder/estimate/export ở server.

```text
GET   /api/v1/subtitle-studio/summary
GET   /api/v1/subtitle-studio/policy
GET   /api/v1/subtitle-studio/references
GET   /api/v1/subtitle-studio/references/language-sources?limit=&offset=
GET   /api/v1/subtitle-studio/projects?state=&q=&limit=
POST  /api/v1/subtitle-studio/projects
GET   /api/v1/subtitle-studio/projects/{project_id}
PATCH /api/v1/subtitle-studio/projects/{project_id}
POST  /api/v1/subtitle-studio/projects/{project_id}/lifecycle
POST  /api/v1/subtitle-studio/projects/{project_id}/restore-version
POST  /api/v1/subtitle-studio/projects/{project_id}/import
GET   /api/v1/subtitle-studio/projects/{project_id}/export?format=srt|vtt
POST  /api/v1/subtitle-studio/projects/{project_id}/cues
PATCH /api/v1/subtitle-studio/projects/{project_id}/cues/{cue_id}
POST  /api/v1/subtitle-studio/projects/{project_id}/cues/{cue_id}/archive
POST  /api/v1/subtitle-studio/projects/{project_id}/cues/{cue_id}/restore
POST  /api/v1/subtitle-studio/projects/{project_id}/cues/{cue_id}/restore-version
POST  /api/v1/subtitle-studio/projects/{project_id}/cues/reorder
GET   /api/v1/subtitle-studio/projects/{project_id}/estimate
GET   /api/v1/subtitle-studio/events?limit=
```

Every endpoint must return the standard envelope and include:

```json
{
  "execution": "authoring_only",
  "provider_called": false,
  "asr_called": false,
  "tts_called": false,
  "dubbing_called": false,
  "translation_called": false,
  "output_created": false,
  "source_bytes_read": false,
  "bot_called": false,
  "bridge_called": false,
  "job_created": false,
  "download_created": false,
  "payment_started": false,
  "payment_processed": false,
  "wallet_mutated": false
}
```

`estimate` is deterministic timestamp/text checks only. `export` serializes
active, validated, user-authored cues as text in a private `no-store` envelope;
it must never mark a project completed or claim media delivery.

## Security, privacy và configuration

- Signed session and server-side account ownership are mandatory for every
  read, version, event, Project reference and text export. Cross-account UUIDs
  return the same opaque not-found result.
- Language Source Intake queries Asset Vault only with `id + account_id +
  state='active'`; it projects only safe metadata (`id`, display name,
  extension, canonical content type, bounded byte size, state, updated time,
  lifecycle revision). Missing, foreign, archived and invalid references share
  a generic failure. It never imports an Asset Vault stream/open/download
  helper, creates a preview URL, or exposes original filename, project ID,
  storage key/path or hash.
- Every mutation requires CSRF, request ID, account-scoped 24-hour idempotency
  key and optimistic `expected_revision`. Reusing a key with another payload is
  `409`; receipts retain only replay-safe IDs/state/revision/boundary flags.
- Enforce a raw ASGI JSON body cap of 128 KiB before parser, a 96 KiB UTF-8
  bound for both pasted import text and generated private export text,
  independent read/write rate scopes, `no-store` for all private API/export responses and
  `WEBAPP_SUBTITLE_STUDIO_ENABLED=true` (default enabled only for
  authoring). PWA caches public shell only and excludes both route/API/export.
- Reject unsafe control characters, raw URLs/paths/data URIs and provider/Bot/job
  markers in project metadata/notes, plus secrets/tokens/passwords/private
  keys/OTP, card/CVV/payment evidence and unbounded rich text everywhere.
  Cue text may contain a spoken/displayed URL but is always rendered as escaped
  plain text, never followed as a media source. Browser validation is
  convenience; server repeats it.
- No cross-origin provider call, no browser secret, no bridge token, no
  Webhook/PayOS/ledger and no second delivery channel are introduced.

## P0 verification checklist

- Anonymous/CSRF/body-cap/rate-limit failures are safe and no-store; IDOR and
  cross-project cue IDs reveal no text or IDs.
- Revision/idempotency collision, immutable versions and archive-parent freeze
  are tested; approved content cannot be mutated without explicit reopen.
- Timing validation catches negative/reversed/overlapping/duplicate ordinal
  cues; reorder is atomic and submits the exact active ID set once.
- Translation source/target text belongs to the same owner/project; language
  values are bounded canonical metadata, not a promise of machine translation.
- Language Source Intake is tested for anonymous/CSRF failure, owner scope,
  safe metadata projection, exact MIME/extension pairs, archived/lifecycle
  mismatch, immutable reference on update/restore, malformed persisted-source
  guard/no-normalization, minimal idempotency receipt hydration, no
  bytes/preview/download path and private PWA exclusion.
- ASR/dubbing UI/API tests assert `provider_called=false`, no provider/FFmpeg/
  Core Bridge imports, no output/player/preview/job success state and private
  PWA cache exclusion.
- Draft SRT/VTT export is tested as literal manual content only, with ownership,
  no-store and no `completed`/delivery implication. Provider, Bot, Telegram,
  PayOS and real-media tests remain outside this module.
