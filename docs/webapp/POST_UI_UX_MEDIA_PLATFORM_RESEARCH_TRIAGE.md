# Post-UI/UX Media Platform Research Triage

**Status:** Deferred architecture research.  This is a decision record, not
an implementation authorization.

**Applies to:** the standalone TOAN AAS Web App and a future customer/mobile
client.  The Telegram Bot is reference-only for this work and must not be
modified.

**Start condition:** Do not begin this roadmap until the current UI/UX work is
accepted for both the customer workspace and the internal admin workspace on
desktop and mobile.  Finishing a screen alone is not a start condition.

## Why this exists

The product-owner research supplied on 2026-07-29 describes useful production
patterns for video editing, multi-scene production, subtitle translation and
dubbing.  It must be applied selectively.  The current Web App already has
bounded Web-native planning and local-media modules, while several commercial
and Bot-owned paths remain guarded.  Replacing those boundaries wholesale,
or introducing infrastructure before there is evidence it is needed, would
make the product less reliable rather than more capable.

The source materials considered are:

- *Kiến trúc và mô hình vận hành cho sản phẩm chỉnh sửa video tích hợp vào
  chat-bot*;
- *Shared Semantic Master DAG*;
- *Kiến trúc sản xuất cho Local Video Editing và Product Video nhiều cảnh*.

They are owner-supplied research references.  They are not copied into this
repository and do not override a reviewed source contract.

## Decisions retained for the post-UI/UX roadmap

| Decision | Why it fits | Earliest safe use |
| --- | --- | --- |
| Immutable approved snapshot for a confirmed media job | Prevents a browser edit, a retry or a worker restart from changing the approved scene order, assets, prompt or output policy. | A new Web-native execution contract, after its ownership and billing boundary are reviewed. |
| Local-first, deterministic FFmpeg execution | Existing bounded Web media labs already use allow-listed arguments, private storage and `ffprobe`; a shared, reviewed runtime is safer than a second ad-hoc renderer. | Extend only a proven local capability with real fixtures and output validation. |
| Artifact validation before delivery | An output is not successful merely because a file exists.  Validate container, streams, duration/profile and full decode before making it downloadable or billable. | Every new executable media lane. |
| Durable stage state, idempotency and recovery lease | Job confirmation, final compose, delivery and any financial event need replay-safe state and one active recovery owner. | Jobs that can survive a request/process restart. |
| Shared semantic source master for subtitle/translation/dubbing | One aligned source transcript and one translation master reduce drift, duplicate ASR/translation cost and debugging effort.  Subtitle copy and spoken dub copy must stay distinct. | A V2 lane run only in shadow/replay with legal fixtures or owner-approved artifacts. |
| Profile-driven quality controls | Subtitle CPS/CPL, line length, timing, loudness and true peak differ by language and delivery target; fixed global values would be misleading. | New subtitle/dubbing render profiles. |
| Observability based on evidence | Job/stage counters, artifact hashes, validation reports, delivery receipts and recovery events make a production claim auditable. | Before enabling any long-running or paid Web-native execution lane. |

## Explicit non-decisions and guardrails

The following must **not** be introduced merely because they appear in the
research:

- Kafka, Kubernetes, WebRTC or GStreamer without a measured product need;
  FFmpeg remains the default for deterministic file jobs.
- Four independent ASR/translation/dubbing pipelines.  A future V2 must share
  the semantic master where the source data is compatible.
- VAD that deletes silence and changes the original video timeline.
- One universal subtitle-reading-speed or loudness constant for all languages
  and output targets.
- Automatic resubmission of a paid ASR, translation, TTS, render or provider
  request after acceptance is ambiguous.  Recovery may poll/retrieve the
  saved provider task, but may not create a replacement charged task blindly.
- Provider credentials, raw FFmpeg fragments, filesystem paths or bridge
  tokens in a browser request.
- A Web-owned duplicate of the Bot wallet/Xu ledger, PayOS webhook, canonical
  Bot job record or Telegram identity authority.

## Authority boundary to resolve before implementation

The current production contract says that the Bot remains canonical for its
own identity, wallet/Xu, PayOS, provider and historical job paths.  The
product direction also calls for a genuinely capable Web/App product rather
than a Telegram-shaped shell.  These statements can coexist only if a future
design explicitly separates ownership:

1. Existing Bot-owned records remain unchanged and are never copied into a
   second mutable ledger.
2. A Web-native service may own a newly designed, isolated media-job namespace
   only after an authority matrix covers identity, assets, job state, delivery,
   billing and support.
3. Any later account/link or bridge integration is an adapter with an explicit
   contract; it is not permission to replay Bot session state or mutate Bot
   records.
4. The customer Web, mobile app and optional Telegram adapter should consume a
   platform-neutral orchestration API, not each other's UI state.

Until that matrix is approved, the current guarded boundaries remain the
source of truth.

## Sequenced post-UI/UX work

### 0. Readiness and ownership audit

Inventory the existing Web-native media modules, feature flags, storage
topology, executable binaries, request limits, assets and existing Bot bridge
boundaries.  Publish one authority/state map before changing a runtime.

### 1. Close one truthful local execution lane

Choose one already-supported, low-risk operation rather than a broad "video
studio" rewrite.  Add approved snapshot input, bounded FFmpeg compilation,
real media fixtures, `ffprobe` plus full-decode validation, owner-only
temporary download and a receipt that describes exactly what happened.

### 2. Build the semantic DAG in shadow mode

For subtitle/translation/dubbing, produce stage manifests and QC reports from
fixtures or approved retained artifacts with provider calls and wallet
mutations disabled.  Keep V1 behavior intact.  Do not expose a public action
until the shadow output and artifact lineage have been reviewed.

### 3. Add resumable orchestration only where needed

Introduce immutable checkpoints, per-stage idempotency keys and an exclusive
lease for the selected long-running job.  Verify restart cases before adding
more features: after an accepted scene, before final compose, after compose
and before delivery/receipt.

### 4. Expand lanes deliberately

Reuse the same source/translation master for subtitle, translation, dubbing
and combo output.  Keep subtitle adaptation and dub-script adaptation as two
different derived artifacts.  Apply language/output profiles and publish QC
warnings rather than presenting uncertain output as complete.

### 5. Consider provider and commercial adapters last

Only after a local lane is observably safe may a provider adapter be designed.
It needs an explicit user confirmation, saved external task ID, signed
webhook/poll deduplication, monotonic terminal state, cost guard and
delivery-first accounting.  Enabling a provider never enables a new PayOS
webhook or duplicate ledger.

### 6. Reuse the stable API for mobile

The future mobile app is a customer companion for capture, upload/status and
notifications; internal administration remains a separately protected app
surface.  Both must use the same signed, owner-scoped API and artifact policy,
not a copied Telegram callback flow.

## Required acceptance gates for every later implementation PR

- No `bot.py` change, no live provider request, no live PayOS mutation and no
  new production webhook during local/design work.
- Feature flag defaults remain safe/off until a reviewed release gate exists.
- Tests cover duplicate confirmation, restart/recovery, invalid output,
  cross-account access and delivery/receipt duplication.
- A job may become `completed` only after the promised artifact passes its
  validation policy.  Any guarded or uncertain state remains visibly guarded.
- A PR must name the one capability it makes real; planning previews cannot
  silently become execution claims.
- Deployment and progressive rollout are separate from the design/fixture
  milestone and require their own owner approval.

## Relationship to the current UI/UX phase

The UI/UX phase continues first: clean teal/cyan customer and admin surfaces,
clear route hierarchy, responsive behavior, accessibility and meaningful
motion.  This document is intentionally a parked architecture backlog so the
interface work is not interrupted by an unreviewed media-engine rewrite.
