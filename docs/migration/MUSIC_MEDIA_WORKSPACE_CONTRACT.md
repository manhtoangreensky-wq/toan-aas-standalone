# Audio Library & Briefing — Web-native contract

## Purpose and boundary

`/media-workspace` is a private workspace for organising music/SFX creative
briefs and existing Audio Asset Vault references. It translates useful Bot
semantics—brief, mood/context, copyright guard, music/SFX organisation—into a
professional Web flow without copying Telegram state or pretending a provider
engine is available.

| Surface | Authority | It never does |
| --- | --- | --- |
| `/media-workspace`, `/api/v1/media-workspace/*` | Standalone Web App / signed Web account | Calls Bot, provider, Key4U, Suno, PayOS, wallet/Xu, raw audio URL or Telegram file ID |
| Frozen Bot `/music*`, `/suggest_music`, `/select_uploaded_audio` flows | Telegram Bot | Becomes a Web provider catalog, public player, job or delivery contract |
| `web_media_*` tables | Standalone Web App | Stores a Bot identity, canonical ledger/payment record, provider request, storage path or generated output |
| Existing Asset Vault download | Standalone Web App / owner-scoped attachment | Becomes a public URL, stream, preview or browser/PWA cache entry |

The local Bot reference is frozen at
`b29d0d474974075f4cba963d2c510f49d2d1b3e4` and is read-only. In particular,
the Bot's `/music_prompt`, `/music_library`, `/sfx_library`, `/play_music`,
`/select_uploaded_audio` and `/suggest_music` semantics were examined, but
their external provider/Telegram-state behavior is not copied into this Web
module.

## Parity map

| Frozen Bot semantic | Web-native equivalent | Status / boundary |
| --- | --- | --- |
| Music/SFX prompt direction | Collection creative brief plus deterministic local composer | Implemented. Composer returns exactly three text directions with `execution=local_deterministic_draft_only`; it never calls an engine. |
| Upload/select personal audio | Attach an existing active, owner-scoped Audio Asset Vault item | Implemented. No URL fetch, new upload, file ID or provider preview field exists here. |
| Play/download state | Existing private Asset Vault attachment route | Implemented only as an owner-checked download link. There is no `<audio>`, streaming, waveform or public delivery. |
| Music/SFX organisation | Collections, tags, favorite, attribution/license metadata, planning Project link and version history | Implemented as Web-owned authoring metadata. A Project link does not promise package/export or engine inclusion. |
| Bot copyright marker checks | Same compact marker guard for named artist/song/melody/voice imitation requests | Implemented. It is a policy marker, not copyright clearance or a generation decision. |
| Jamendo/Freesound/provider search and expiring previews | None | `GUARDED`; no provider credentials, URLs or preview state enter Web. |
| AI music/Suno/song creation, enhance, translate, mux/render | None | `GUARDED`; no job, Xu charge, payment, output or success label is created. |

## Lifecycle and API

```text
active ──archive──> archived
archived ──restore──> active
active ──update / restore-version──> active, revision + 1
active ──attach/update/detach Asset Vault reference──> active, revision + 1
```

Metadata revisions are immutable and bounded to 100 per collection. At the
history ceiling, archive/restore remains possible but transparently records no
new snapshot rather than trapping the owner in an unrecoverable archive state.
Audio references do not roll back with metadata versions.

```text
GET   /api/v1/media-workspace/summary
GET   /api/v1/media-workspace/policy
GET   /api/v1/media-workspace/audio-assets
GET   /api/v1/media-workspace/collections?limit=&state=&q=&tag=&prompt_mode=
POST  /api/v1/media-workspace/collections
GET   /api/v1/media-workspace/collections/{collection_id}
PATCH /api/v1/media-workspace/collections/{collection_id}
POST  /api/v1/media-workspace/collections/{collection_id}/archive
POST  /api/v1/media-workspace/collections/{collection_id}/restore
POST  /api/v1/media-workspace/collections/{collection_id}/duplicate
POST  /api/v1/media-workspace/collections/{collection_id}/restore-version
POST  /api/v1/media-workspace/collections/{collection_id}/compose
POST  /api/v1/media-workspace/collections/{collection_id}/items
PATCH /api/v1/media-workspace/collections/{collection_id}/items/{item_id}
POST  /api/v1/media-workspace/collections/{collection_id}/items/{item_id}/detach
GET   /api/v1/media-workspace/events
```

All mutations other than the purely deterministic `compose` require CSRF,
owner-scoped idempotency and optimistic `expected_revision`. Successful
mutations use `status=draft`, never `completed`, and include
`execution=authoring_only`. Attach/update/detach additionally identify the
only delivery boundary as `asset_vault_attachment_only`.

## Security and privacy

- Every collection, version, item, event, Project and Asset Vault lookup is
  bound to signed `account_id`. A UUID never grants access.
- Only active `.mp3`, `.wav`, `.m4a` or `.ogg` files with the matching
  canonical Asset Vault content type may be attached. Raw URLs, paths,
  Telegram IDs, provider IDs, previews and uploads are absent from schema.
- Inputs reject unsafe controls, secrets/tokens/passwords/private keys,
  OTP/CVV/card-like strings and manual payment evidence. The server applies
  the Bot-derived imitation policy again; browser checks are convenience only.
- Idempotency receipts live 24 hours and retain only replay-safe IDs,
  lifecycle/revision metadata and status. They never duplicate a brief,
  description, excerpt, rights note, attribution or license note.
- JSON writes have a 64 KiB raw ASGI cap before FastAPI/Pydantic parsing,
  including chunked requests. Overages return no-store `413` with
  `WEB_MEDIA_WORKSPACE_BODY_TOO_LARGE`.
- Private API responses are `no-store`; the PWA caches the public shell only
  and never `/api/v1/media-workspace`, Asset Vault or private download routes.

## Configuration and verification

```text
WEBAPP_MUSIC_MEDIA_WORKSPACE_ENABLED=true
WEBAPP_ASSET_VAULT_ENABLED=true       # required to attach/download audio
WEBAPP_SESSION_DB_PATH=<persistent database path in production>
```

The workspace defaults to authoring enabled, but it does not make Audio Asset
Vault storage durable by itself. Production durability still needs the
configured Railway persistent volume. Focused contracts cover the high-risk
paths: signed session/CSRF, owner isolation, pre-parser body cap, receipt
privacy/replay, valid active audio only, raw-source rejection, policy guard,
local-only composer and private delivery metadata. Provider, PayOS and
Telegram live tests remain explicitly out of this module.
