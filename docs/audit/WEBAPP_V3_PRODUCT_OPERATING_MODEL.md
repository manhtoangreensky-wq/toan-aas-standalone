# Web App V3 Product Operating Model & Architectural Truth
> **Task**: `P0.WEBAPP.V3.AUDIT.FINAL.ROADMAP.EXECUTION.SAFETY.CLOSURE`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Authoritative Base SHA**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`

---

## 1. Executive Summary & Source Truth Alignment

Following the live deployment of `V2-07` on production VPS (`tg.toanaas.vn`), a rigorous independent source code audit and runtime verification was conducted across the Web App codebase (`toan-aas-standalone`), Telegram Bot core (`bot`), and live systemd services.

The audit establishes the following empirical and architectural truths:

1. **`copyfast_video_studio.py` is Strictly Planning-Only (`INDEPENDENT_SOURCE_VERIFIED`)**:
   - Exact source measurements on Base SHA `8873e10f2279aec0fb312b70388b9073ba763f13`:
     - Total Lines: `10,215`
     - HTTP Decorator Routes: `39` (not 37)
     - Implementation Nature: Purely prompt composition and static scene planning (`PLANNING_ONLY=YES`).
     - Gaps: Zero job creation, zero provider calls, zero MP4 outputs, zero delivery receipts, and zero interaction with the SQLite wallet table.
2. **Canonical Worker Execution Architecture (`INDEPENDENT_SOURCE_VERIFIED`)**:
   - Current production execution uses:
     - SQLite `video_jobs`
     - `video_dispatch_outbox`
     - Lease/claim semantics via `services/remote_worker_api.py` and `remote_worker.py`
     - Endpoints: `POST /api/v1/worker/claim`, `POST /api/v1/worker/complete`, `POST /api/v1/worker/fail`
     - Workers are systemd-managed daemon processes on Ubuntu VPS.
     - **Celery and Redis Queue are NOT used** (`CELERY_CURRENTLY_USED=NO`, `REDIS_QUEUE_CURRENTLY_USED=NO`). P0-D integrates Web jobs with this existing canonical contract.
3. **Product Video Billing Contract (`INDEPENDENT_SOURCE_VERIFIED`)**:
   - Preflight / Quote calculation may occur before dispatch.
   - Customer wallet charge occurs **ONLY after successful final delivery** and canonical charge decision (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`).
   - Failed or recovered jobs incur zero charge (`FAILED_NO_CHARGE=0_XU`, `RECOVERY_NO_CHARGE=0_XU`). Pre-render debit or pre-render debit-then-refund models are strictly unverified and prohibited.
4. **Three Distinct Runtime Connectivity Categories (`READ_ONLY_RUNTIME_VERIFIED`)**:
   - `DEPLOY_RESTART_NGINX_502`: Infrastructure gateway outage during CI/CD auto-deploy `systemctl restart toanaas-web.service` (1-3s socket drop).
   - `BOT_CORE_ROUTE_MISSING`: Upstream Bot Core 127.0.0.1:8080 lacks `/internal/v1/admin/*` endpoints (returns upstream 404; Web bridge wraps into HTTP 200 guarded envelope). Not an Nginx 502.
   - `ACCOUNT_TELEGRAM_UNLINKED`: Application state 409 when user lacks linked Telegram ID. Not a gateway failure.
5. **Nginx Upstream Retry & Zero-Downtime Policy (`TARGET_DESIGN`)**:
   - Safe upstream retry is permitted ONLY for idempotent read requests (GET/HEAD with `error timeout http_502`).
   - `MUTATION_HTTP_RETRY_POLICY=NO_BLIND_REPLAY`: Financial, job creation, and state mutation POST requests must NOT be blindly replayed by Nginx. Replaying POST requests risks duplicating business side effects.
   - Principle: `HTTP_RETRY != BUSINESS_OPERATION_RETRY`. Mutation retry is permitted exclusively through endpoint-level proven idempotency semantics.
   - Zero-Downtime Target: Candidate solutions (graceful reload, socket handoff, multi-worker rolling replacement, upstream overlap, health-aware deployment) are evaluated in task P0-B1.
6. **Pricing & Packages Invariant (`INDEPENDENT_SOURCE_VERIFIED`)**:
   - Public routes `/api/v1/pricing` and `/api/v1/packages` use canonical bridge reads.
   - Invariant: `NO_LOCAL_EFFECTIVE_PRICING`, `NO_CLIENT_DERIVED_PRICING`, `NO_STATIC_EFFECTIVE_PRICE_FALLBACK`.
   - If bridge is unreachable, the system renders a truthful unavailable/guarded state; it never fabricates fallback prices.

---

## 2. The 10 Customer Product Families & Independence Contracts

Web App V3 groups all customer capabilities into **10 Distinct, Independent Product Families**:

```
[1. PRODUCT_VIDEO]                -> AI Product Video Studio (Multi-scene, E2E Render)
[2. VOICE]                        -> AI Voice & Speech Synthesis (TTS, Clone)
[3. MUSIC_AND_SFX]                -> Commercial Music & Foley SFX (BGM, Cue Sheets)
[4. SUBTITLE_DUBBING_TRANSLATION] -> Subtitles, Multilingual Dubbing & Burn-in
[5. VIDEO_EDIT]                   -> Manual Fast Video Tools (Trim, Crop, Merge, FFmpeg)
[6. PUBLISHING_AUTOMATION]        -> AutoPost (Scheduling, Multi-channel Orchestration)
[7. FREE_TOOLS]                   -> Free Utility Suite & Viral Prompts (Lead Magnets)
[8. IMAGE_TOOLS]                  -> AI Product Photography & Creative Visuals
[9. PROJECTS_MEDIA_LIBRARY]       -> Media Vault, Asset Storage & Version History
[10. ACCOUNT_WALLET_COMMERCE]     -> PayOS Topup, Balance Ledger, Telegram Pairing
```

### Independence & Non-Blocking Architecture (`TARGET_DESIGN`)
- **Voice Independence**: Voice synthesis does NOT depend on Product Video.
- **Music & SFX Independence**: Strictly separated from SubDub and Product Video.
- **SubDub Independence**: Implementable independently for uploaded/existing media (`SUBDUB_PRODUCT_IMPLEMENTATION != PRODUCT_VIDEO_DEPENDENT`). Integrates with Video Product and Video Edit later via Common Artifact Handoff.
- **Video Edit Independence**: Independent Manual Video Tools family. Fast local/server FFmpeg utility; never routes cheap local FFmpeg work through expensive paid AI providers.
- **Free Tools Separation**: Free Utilities is a distinct lead-magnet family, not merged into Video Edit.
- **AutoPost Independence**: AutoPost core depends on the `PUBLISHABLE_ASSET_HANDOFF_FOUNDATION`, NOT on any single producer. It consumes finished output from any producer through the common contract.

---

## 3. Product Video Studio: Gap Analysis & Target Pipeline

### 3.1 Gap Matrix (25 Lifecycle Points)
Comparing `copyfast_video_studio.py` against Telegram Bot core:

| Lifecycle Step | Telegram Bot Runtime | Web App Source (`copyfast_video_studio.py`) | Evidence Level & Status |
| :--- | :--- | :--- | :--- |
| **01. Brief & Prompt** | Interactive Telegram prompts | 39 decorator routes, text-only prompts | `INDEPENDENT_SOURCE_VERIFIED` (PARTIAL) |
| **02. Asset Upload** | Photo/video upload via TG media | Reference URLs only; no vault storage | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **03. Scene Composition** | Script decomposition via LLM | Static templates in Python code | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **04. Storyboard Order** | Sequential script array | In-memory array in browser DOM | `INDEPENDENT_SOURCE_VERIFIED` (PARTIAL) |
| **05. Preflight Quote** | Real-time quote before dispatch | Deterministic mock estimate endpoint | `INDEPENDENT_SOURCE_VERIFIED` (PARTIAL) |
| **06. Confirmation** | 2-step invoice confirmation | None (stops at text planning) | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **07. Job Creation** | Atomic insert in SQLite `video_jobs` | Zero job records created | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **08. Worker Dispatch** | `video_dispatch_outbox` lease/claim | None (zero worker invocation) | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **09. Execution Monitoring**| Polling scene progress | Mock event log | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **10. Final Stitching** | FFmpeg scene + audio assembly | None | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **11. Video Preview** | Video message in TG chat | None | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **12. Delivery Receipt** | Durable delivery receipt in DB | None | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |
| **13. Wallet Charge** | Charged ONLY after delivery | None (no wallet interaction) | `INDEPENDENT_SOURCE_VERIFIED` (MISSING) |

---

## 4. Manual Video Tools (Video Edit): Operational Model (`TARGET_DESIGN`)

`VIDEO_EDIT` provides direct, high-speed, local/server media processing without generative AI model latency or cost.

### 4.1 Scope of Operations
- **Trimming & Cutting**: Precise timestamp-based cut/trim without re-encoding (`-c copy`) where keyframes align.
- **Concatenation & Merging**: Stitching multiple clips with matching codecs.
- **Cropping & Aspect Resizing**: Padding or cropping to 9:16, 16:9, 1:1, 4:5.
- **Compression**: Web-optimized H.264/AAC compression.
- **Audio Manipulation**: Mute, audio replacement, audio extraction (MP4 $\rightarrow$ MP3/WAV).
- **Watermark & Branding**: Overlay transparent PNG logos at fixed anchor positions.
- **Thumbnail & Poster**: Extraction of specific high-resolution frames.
- **Speed Ramping**: 0.5x to 2.0x video playback adjustments.
- **Metadata Inspection**: Media probe (duration, bitrate, dimensions, codec, audio channels).

### 4.2 Local vs Job Execution Boundary (`TARGET_DESIGN`)
- `LOCAL_SAFE_OPERATION`: Client-side WebAssembly / lightweight server FFmpeg stream processing for instant tasks (trim < 60s, extract audio, probe metadata).
- `CANONICAL_JOB_REQUIRED`: Complex re-encoding, large batch concatenations, or high-bitrate exports create background jobs in the Media Vault queue.
- **Cost Invariant**: Cheap FFmpeg tasks must NEVER be routed through paid AI provider APIs.

---

## 5. AutoPost & Common Publishable Artifact Architecture

### 5.1 System Role & Ownership Boundaries (`TARGET_DESIGN`)
AutoPost is an **orchestrator downstream of asset generation**. It consumes finished media artifacts and handles their review, scheduling, dispatch, and delivery receipts.

```
[WHAT AUTPOST OWNS]
- Multi-channel orchestration (TikTok, YouTube Shorts, Facebook Reels)
- Preview & approval workflows
- Durable schedule persistence across server restarts
- Channel-specific adapter dispatch & rate limiting
- Platform receipt binding (post_id, platform_url)
- Publish-only retry loop (with exponential backoff)
- Complete publication audit log

[WHAT AUTPOST DOES NOT OWN]
- Product Video rendering (owned by Product Video Studio)
- Video Edit trimming/cropping (owned by Video Edit Tools)
- Subtitle transcription or audio dubbing (owned by SubDub Engine)
```

### 5.2 Common Publishable Artifact Contract (`TARGET_DESIGN`)
Any producer handing off media to AutoPost must conform to this immutable contract. Raw user-entered Job IDs are strictly prohibited as handoff authority:

```json
{
  "asset_id": "ast_01j8x8m9k2a4b7c1d3e5f6g7h8",
  "owner_id": "usr_99182",
  "source_product": "PRODUCT_VIDEO | VIDEO_EDIT | SUBDUB | EXISTING_FINISHED_VIDEO",
  "source_job_id": "job_01j8x8m9... | null",
  "parent_asset_id": "ast_01j8x000... | null",
  "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "media_type": "video/mp4",
  "duration_ms": 32400,
  "width": 1080,
  "height": 1920,
  "artifact_state": "READY",
  "processing_completed_at": "2026-09-19T10:15:00Z",
  "caption_candidate": "Trải nghiệm dưỡng trắng chuyên sâu cùng Tinh Chất ToanAAS #skincare #beauty",
  "canonical_storage_ref": "vault://videos/2026/09/ast_01j8x8m9.mp4",
  "publish_eligible": true,
  "publish_blockers": []
}
```

### 5.3 Multi-Step Processing Model (Optional DAG/Recipe) (`DESIGN_PROPOSAL`)
The publishing workflow supports an optional pipeline recipe. Chaining is strictly optional; there is no mandatory Product $\rightarrow$ Edit $\rightarrow$ SubDub pipeline:

```mermaid
flowchart LR
    A[Product Video] -->|Optional| B[Video Edit]
    B -->|Optional| C[SubDub]
    A -->|Direct| D[Review & Approval]
    B -->|Direct| D
    C -->|Direct| D
    E[Existing Video] -->|Direct| D
    D --> F[Durable Schedule]
    F --> G[Publish Dispatcher]
```

**Anti-Rerun Rule**: Retrying a failed publication step must **NEVER rerun a completed producer**. If YouTube upload fails with a network timeout, only the publication attempt is retried; the upstream video render remains untouched.

### 5.4 Durable Publishing Core & State Machine (`TARGET_DESIGN`)
Entities: `publication`, `publication_attempt`, `schedule`, `outbox`, `receipt`.

Lifecycle States:
```
[PLANNED] -> [APPROVED] -> [SCHEDULED] -> [CLAIMED/DISPATCHING]
   |             |              |                    |
   v             v              v                    v
[CANCELLED]  [CANCELLED]   [CANCELLED]      [PLATFORM_PROCESSING]
                                                     |
                                        +------------+------------+
                                        |                         |
                                        v                         v
                                   [PUBLISHED]           [FAILED_RETRYABLE]
                                        |                         |
                               (Receipt Recorded)         (Retry Counter < Max)
                                                                  |
                                                                  v
                                                            [FAILED_FINAL]
```

- **Invariant**: `HTTP_200 != PUBLISHED`. A post is only considered published when a verified platform receipt identifier is bound and recorded.
- **Idempotency**: Every publication attempt carries a unique idempotency key based on `(publication_id, channel_id, scheduled_time)`.

### 5.5 Video Split / Batch Contract (`DESIGN_PROPOSAL`)
For workflows converting one long master video into multiple short social posts:
- Structure: **Parent Batch** managing $N$ **Child Publication Units**.
- Each child independently owns: clip asset, aspect preview, caption, approval status, target channel, scheduled slot, platform receipt, and retry state.
- **Fault Isolation**: Failure of Child Clip #3 does not affect, pause, or duplicate Child Clips #1, #2, or #4.
