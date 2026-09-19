# Web App V3 Rebased Master Plan & Transition Roadmap
> **Task**: `P0.WEBAPP.V3.AUDIT.AUTOPOST.SINGLE.AUTHORITY.FINAL.ALIGNMENT`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Authoritative Base SHA**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`
> **Total Bounded Implementation Tasks**: `15`

---

## 1. Executive Summary & Strategy Pivot

The previous linear sequence (`V2-08` through `V2-15`) suffered from structural limitations:
1. **Catalog Flattening**: Exposing 135 technical subroutines in a flat directory obscured core product offerings and caused user cognitive overload.
2. **Planning-Only Video Studio**: `copyfast_video_studio.py` (39 routes, 10,215 lines) remained a prompt generator with zero execution, zero worker dispatch, zero MP4 outputs, and zero wallet interaction (`INDEPENDENT_SOURCE_VERIFIED`).
3. **Canonical Worker Architecture**: Current production uses **SQLite `video_jobs` outbox lease/claim** via `services/remote_worker_api.py` and `remote_worker.py` on systemd. Celery and Redis Queue are not used (`INDEPENDENT_SOURCE_VERIFIED`).
4. **Billing Invariant**: Product Video charges the customer wallet **ONLY after successful final delivery** (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`). Pre-render debit models are unverified and prohibited (`INDEPENDENT_SOURCE_VERIFIED`).
5. **Nginx Upstream Retry Safety**: Blind replay of POST requests risks duplicating financial transactions or job creation. Safe upstream retry is permitted ONLY for idempotent reads (`error timeout http_502` for GET/HEAD). `MUTATION_HTTP_RETRY_POLICY=NO_BLIND_REPLAY`. Principle: `HTTP_RETRY != BUSINESS_OPERATION_RETRY`.
6. **Product Family Independence & Single AutoPost Authority**:
   - `VOICE` does not depend on Product Video.
   - `MUSIC_AND_SFX` does not depend on Product Video or SubDub.
   - `SUBDUB` is independently implementable for uploaded/existing media.
   - `VIDEO_EDIT` (Manual Video Tools) is an independent utility; cheap FFmpeg work is never routed through paid AI providers.
   - `FREE_TOOLS` is a distinct lead-magnet family.
   - `PUBLISHING_AUTOMATION` (AutoPost) has a **Single Canonical Execution Authority**: `manhtoangreensky-wq/bot`. Web App acts strictly as a control surface and read projection (no duplicate ledger, scheduler, or outbox in Web).

This master plan formally retires the old V2 sequence and establishes an evidence-driven, product-centric V3 roadmap organized into **15 Bounded Implementation Tasks**.

---

## 2. Legacy Task Disposition Matrix (V2-08 -> V2-15)

| Legacy Task ID | Original Title | Disposition | Target V3 Task | Rationale & Architectural Realignment |
| :--- | :--- | :--- | :--- | :--- |
| **V2-08** | Admin Customer Detail & Lifetime Analytics Workspace | **SPLIT & MOVED** | `P0-E: Admin Customer 360` & `P0-B1/B2: Runtime Connectivity` | Customer 360 profile, CRM leads, and support belong in unified Customer Workspace; financial mutations require canonical bridge adapter. |
| **V2-09** | Admin System Health, Log Explorer & Audit Telemetry Hub | **MOVED & CONSOLIDATED** | `P0-F: Admin Worker Fleet & System Telemetry` | Monitor live SQLite outbox lease/claim and systemd worker processes on VPS (`tg.toanaas.vn`). |
| **V2-10** | Customer Unified Media Studio (Voice, Video, Music, Subtitle) | **REPLACED & DECOMPOSED** | `P0-D: Video Studio`, `P1-A: Voice`, `P1-B: Music & SFX`, `P1-C: SubDub`, `P1-D: Video Edit` | Grouping 5 distinct product lines into one monolithic page violates family separation. Decomposed into independent product engines. |
| **V2-11** | Customer Multi-Scene Video Production Workflow | **MERGED** | `P0-D: End-to-End Product Video Studio` | Multi-scene storyboard composition is integral to the Video Studio pipeline, not a detached workflow. |
| **V2-12** | Customer Publishing, Webhook & Distribution Hub | **REPLACED & UPGRADED** | `P1-E: AutoPost Handoff Bridge Projection` & `P1-F: AutoPost Publishing Control Surface` | Upgraded to AutoPost dual-layer model: Web provides Handoff Bridge projection and rich Publishing Control Surface; canonical execution outbox/scheduler lives in Bot Core. |
| **V2-13** | Admin Catalog & Pricing Governance Center | **REPLACED** | `P0-C: Customer IA & 10 Product Catalog` | Replaced flat 135-feature catalog with governance over the 10 distinct customer product families. |
| **V2-14** | Admin Live Delivery Control & Worker Fleet Orchestrator | **MERGED** | `P0-F: Admin Worker Fleet & System Telemetry` | Merged into single operations control center. |
| **V2-15** | Final Quality, Performance & Production Hardening | **KEPT & EXPANDED** | `P2-A: Locale Purity & E2E Production Hardening` | Retained as final end-to-end verification gate across Web and cross-repo integration. |

---

## 3. Rebased V3 Implementation Roadmap (15 Bounded Tasks)

```mermaid
flowchart TD
    subgraph Phase 0: Foundations, Connectivity & Video Studio (P0)
        P0A["P0-A: Theme Rebase to Light Teal/Mint & WCAG AA"]
        P0B1["P0-B1: Web 502, Zero-Downtime Deploy & Telegram UX (WEB)"]
        P0B2["P0-B2: Bot Canonical Read Endpoints (BOT)"]
        P0C["P0-C: Customer IA & 10 Product Catalog"]
        P0D["P0-D: End-to-End Product Video Studio (Outbox & E2E)"]
        P0E["P0-E: Admin Customer 360 & Operations Hub"]
        P0F["P0-F: Admin Worker Fleet & VPS Telemetry"]

        P0A --> P0C
        P0B1 -. Cross-Repo .- P0B2
        P0B1 --> P0E
        P0B2 --> P0E
        P0C --> P0D
        P0B1 --> P0D
        P0E --> P0F
    end

    subgraph Phase 1: Independent Product Engines & Distribution Core (P1)
        P1A["P1-A: AI Voice & Speech Synthesis Studio"]
        P1B["P1-B: Music & Foley SFX Studio"]
        P1C["P1-C: SubDub & Multilingual Translation Suite"]
        P1D["P1-D: Video Edit & Manual Fast Video Tools"]
        P1E["P1-E: AutoPost Handoff Bridge Projection"]
        P1F["P1-F: AutoPost Publishing Control Surface"]
        P1G["P1-G: Internal Admin Mobile App (5-Tab Web)"]

        P0A --> P1A
        P0A --> P1B
        P0A --> P1C
        P0A --> P1D
        P0C --> P1E
        P1E --> P1F
        P0F --> P1G
    end

    subgraph Phase 2: Production Hardening & Global Verification (P2)
        P2A["P2-A: Locale Purity, E2E Regression & Production Hardening"]

        P1A --> P2A
        P1B --> P2A
        P1C --> P2A
        P1D --> P2A
        P1F --> P2A
        P1G --> P2A
    end
```

---

### 3.1 Phase 0: Foundations, Connectivity & Flagship Video Studio (7 Tasks)

#### [P0-A] Visual System Rebase to Light Teal / Mint & Contrast Hardening
- **TASK_ID**: `P0.WEBAPP.V3-A.TEAL.MINT.THEME.REBASE`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Purge forced navy blue tokens (`--portal-customer-blue-rail: #075985`, `--portal-blue-dark-*`) from `portal-theme.css`. Implement canonical Light Teal / Mint tokens (`#f3fbfc`, `#ffffff`, `#0d9488`, `#14b8a6`, `#073a45`, `#e6f7f6`). Fix active/pressed state contrast to meet WCAG AA ($\ge 4.5:1$). Enforce motion budget (120–180ms ease-out, `prefers-reduced-motion`).
- **DEPENDENCIES**: None.
- **SIDE_EFFECT_CLASS**: `CSS_DESIGN_TOKENS_ONLY`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: Zero navy blue rail overrides; 100% WCAG AA contrast compliance in automated audits.

#### [P0-B1] Web Runtime 502, Zero-Downtime Deploy & Telegram Linking (WEB)
- **TASK_ID**: `P0.WEBAPP.V3-B1.RUNTIME.DEGRADATION.UX`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Web runtime recovery: investigate zero-downtime service replacement (graceful reload, socket handoff, multi-worker rolling replacement). Safe upstream retry for idempotent reads only (`error timeout http_502` for GET/HEAD); strict prohibition of blind mutation replay (`MUTATION_HTTP_RETRY_POLICY=NO_BLIND_REPLAY`). Resolve `ACCOUNT_TELEGRAM_UNLINKED` (409) application state by rendering a friendly Telegram deep-linking card with 6-digit OTP pairing UI. Bridge consumer contract for resilient envelope handling.
- **DEPENDENCIES**: None.
- **SIDE_EFFECT_CLASS**: `WEB_RUNTIME_AND_CLIENT_UX`
- **OWNER_GATE**: Zero blind POST replay; deployment change review.
- **PASS_GATE**: Zero Nginx 502 on idempotent reads during restarts; unlinked accounts display pairing card; zero blind POST replay.

#### [P0-B2] Bot Core Canonical Admin Read Endpoints (BOT)
- **TASK_ID**: `P0.BOT.V3-B2.ADMIN.CANONICAL.READ.ENDPOINTS`
- **REPOSITORY**: `manhtoangreensky-wq/bot` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Implement missing authenticated read-only admin endpoints in `bot.py`:
  - `GET /internal/v1/admin/wallet`
  - `GET /internal/v1/admin/revenue`
  - `GET /internal/v1/admin/refunds`
  - `GET /internal/v1/admin/users`
  Enforce authentication via internal loopback token / shared HMAC.
- **DEPENDENCIES**: None.
- **SIDE_EFFECT_CLASS**: `BOT_READ_ONLY_ENDPOINTS`
- **OWNER_GATE**: Bot repository PR authorization.
- **PASS_GATE**: Bot Core returns HTTP 200 with authentic JSON for all 4 admin endpoints.

#### [P0-C] Customer Information Architecture & 10 Product Hubs
- **TASK_ID**: `P0.WEBAPP.V3-C.CUSTOMER.IA.10.PRODUCTS`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Rebuild customer sidebar into 13 canonical items grouped into 4 functional tiers. Reorganize 135 catalog features into 10 distinct product families. Implement primary product landing cards with quick-start templates, asset history, and direct studio links. Secondary tool discovery drawers with search, tag filters, and usage counters.
- **DEPENDENCIES**: `P0-A`.
- **SIDE_EFFECT_CLASS**: `CUSTOMER_NAVIGATION_AND_DOM`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: Customer navigation conforms strictly to the 13-item contract; all features accessible without catalog clutter.

#### [P0-D] End-to-End Product Video Studio (Canonical Worker & Billing Integration)
- **TASK_ID**: `P0.WEBAPP.V3-D.PRODUCT.VIDEO.STUDIO.E2E`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Upgrade `copyfast_video_studio.py` from prompt-planner into a full-featured video production studio. Multi-scene storyboard grid: drag-and-drop scene ordering, aspect ratio preview, bulk scene edits. Preflight quote: capability check and price calculation via canonical bridge. Job creation: atomic insert into canonical SQLite `video_jobs` outbox via bridge (`video_dispatch_outbox` lease/claim). Live scene progress polling, HTML5 MP4 player, signed download link. Enforce billing invariant: customer wallet charge occurs ONLY after successful final delivery (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`, `FAILED_NO_CHARGE=0_XU`).
- **DEPENDENCIES**: `P0-A`, `P0-B1`, `P0-B2`, `P0-C`.
- **SIDE_EFFECT_CLASS**: `CANONICAL_JOB_DISPATCH_AND_WALLET_CHARGE`
- **OWNER_GATE**: Preflight quote check; wallet charge strictly post-delivery (`FAILED_NO_CHARGE=0_XU`).
- **PASS_GATE**: User can compose a 3-scene video, confirm quote, trigger job run in SQLite outbox, play generated MP4 in-browser, and verify post-delivery wallet deduction.

#### [P0-E] Admin Customer 360, CRM Leads & Audited Operations Hub
- **TASK_ID**: `P0.WEBAPP.V3-E.ADMIN.CUSTOMER.360.OPERATIONS`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Unified Customer 360 view: account profile, balance, lifetime spending, active jobs, Telegram pairing status. CRM lead management pipeline: contact requests, consultation tickets, conversion status. Audited manual topup operations: 3-layer reconciliation proofs, draft approvals, and idempotent credit invocation via bridge. Enforce boundary: all actions confined strictly to `ADMIN_PRODUCT_CONTROL` (no raw SQL, no arbitrary balance modification).
- **DEPENDENCIES**: `P0-B1`, `P0-B2`.
- **SIDE_EFFECT_CLASS**: `ADMIN_OPERATIONAL_CONTROLS`
- **OWNER_GATE**: Confined to `ADMIN_PRODUCT_CONTROL`; no raw SQL, no arbitrary balance mutation.
- **PASS_GATE**: Admin can inspect customer 360 records, manage CRM leads, and issue audited topup approvals.

#### [P0-F] Admin Worker Fleet Telemetry & Live VPS Control
- **TASK_ID**: `P0.WEBAPP.V3-F.ADMIN.WORKER.FLEET.TELEMETRY`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Monitor canonical worker fleet: query SQLite `video_dispatch_outbox` lease/claim states and claim heartbeats (`services/remote_worker_api.py`). Monitor systemd worker processes on VPS (`tg.toanaas.vn`). Dead-letter queue (DLQ) recovery: view failed tasks with error diagnostics. Enforce queue mutation policy: `QUEUE_REDISPATCH_OWNER_GATED=YES` (re-queue/retry mutations require canonical adapter, audit receipt, and fresh Owner authorization).
- **DEPENDENCIES**: `P0-B1`, `P0-B2`.
- **SIDE_EFFECT_CLASS**: `READ_ONLY_TELEMETRY_WITH_GATED_MUTATION`
- **OWNER_GATE**: `QUEUE_REDISPATCH_OWNER_GATED=YES` (Queue mutations require canonical adapter, audit receipt, and fresh Owner authorization).
- **PASS_GATE**: Real-time worker telemetry; DLQ inspection with audited re-queue gate.

---

### 3.2 Phase 1: Independent Product Engines & Distribution Core (7 Tasks)

#### [P1-A] AI Voice & Speech Synthesis Studio
- **TASK_ID**: `P1.WEBAPP.V3-G.VOICE.AUDIO.STUDIO`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: Independent Voice Studio: speaker selection library, emotional inflection controls, audio preview player, waveform visualizer, MP3/WAV downloads.
- **DEPENDENCIES**: `P0-A` (Strictly independent of Product Video).
- **SIDE_EFFECT_CLASS**: `AUDIO_SYNTHESIS_PRODUCER`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: Real-time voice synthesis and audio playback.

#### [P1-B] Music & Foley Sound Effects (SFX) Studio
- **TASK_ID**: `P1.WEBAPP.V3-H.MUSIC.SFX.STUDIO`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: Independent Music & SFX Studio: BGM generation, Foley SFX library, volume ducking parameters, audio stem mixer.
- **DEPENDENCIES**: `P0-A` (Strictly independent of Product Video and SubDub).
- **SIDE_EFFECT_CLASS**: `MUSIC_AND_SFX_PRODUCER`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: BGM generation and Foley cue sheet binding.

#### [P1-C] SubDub & Multilingual Translation Suite
- **TASK_ID**: `P1.WEBAPP.V3-I.SUBDUB.TRANSLATION.SUITE`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: Independent SubDub Suite for uploaded or existing media: auto-transcription SRT/VTT timeline editor, multilingual audio dubbing sync, subtitle burn-in. (Integrates with Video Product and Video Edit later via Common Artifact Handoff).
- **DEPENDENCIES**: `P0-A` (Strictly independent of Product Video for core implementation).
- **SIDE_EFFECT_CLASS**: `SUBTITLE_AND_DUBBING_PROCESSOR`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: Audio transcription, subtitle timeline editing, and burn-in rendering.

#### [P1-D] Video Edit & Manual Fast Video Tools
- **TASK_ID**: `P1.WEBAPP.V3-J.VIDEO.EDIT.MANUAL.TOOLS`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: Independent Manual Video Tools family: trim/cut, concat/merge, crop/resize/aspect, compress, mute/audio replace, watermark/logo, thumbnail/poster, format conversion, speed, audio/frame extraction, probe/metadata. Distinguish `LOCAL_SAFE_OPERATION` vs `CANONICAL_JOB_REQUIRED`. Zero routing of cheap FFmpeg work through paid AI providers.
- **DEPENDENCIES**: `P0-A` (Strictly independent of AI Video Product).
- **SIDE_EFFECT_CLASS**: `FAST_MEDIA_PROCESSING_UTILITY`
- **OWNER_GATE**: Zero routing of local FFmpeg operations through paid AI provider APIs.
- **PASS_GATE**: Fast local/server FFmpeg operations with instant preview and download.

#### [P1-E] AutoPost Handoff Bridge Projection
- **TASK_ID**: `P1.WEBAPP.V3-K.AUTOPOST.HANDOFF.BRIDGE.PROJECTION`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Web consumes canonical Bot PublishableAsset and Handoff APIs (`POST /internal/v1/autopost/handoff`). Renders asset selection UI, provenance display, and lineage metadata. Acts strictly as a read projection and bridge client; does NOT maintain a second authoritative handoff registry or asset ledger.
- **DEPENDENCIES**: `P0-C` (Precedes full publishing control surface).
- **SIDE_EFFECT_CLASS**: `BRIDGE_CONSUMER_AND_PROJECTION_METADATA`
- **OWNER_GATE**: Canonical Bot API consumption; no duplicate Web registry.
- **PASS_GATE**: Web renders selectable asset list with lineage/provenance from Bot API.

#### [P1-F] AutoPost Publishing Control Surface & Scheduling UX
- **TASK_ID**: `P1.WEBAPP.V3-L.AUTOPOST.PUBLISHING.CONTROL.SURFACE`
- **REPOSITORY**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **PURPOSE**: Web control surface for social post creation, draft editing, caption generation, multi-channel selection (TikTok, YouTube Shorts, FB Reels), calendar view, clip grids, batch operations, and trigger retry calls via Bot AutoPost API (`POST /internal/v1/autopost/schedule`, `POST /internal/v1/autopost/retry`). Web App does NOT hold an execution outbox, scheduler, or lease worker.
- **DEPENDENCIES**: `P1-E` (AutoPost Handoff Bridge Projection), Bot PR #1080 foundation.
- **SIDE_EFFECT_CLASS**: `SOCIAL_PUBLISHING_CONTROL_SURFACE`
- **OWNER_GATE**: Publish-only retry must never rerun producer; all state writes call canonical Bot API.
- **PASS_GATE**: Rich calendar and batch UX scheduling posts via Bot Core API and displaying execution receipts.

#### [P1-G] Internal Admin Mobile-Optimized Web App (5-Tab Architecture)
- **TASK_ID**: `P1.WEBAPP.V3-M.ADMIN.MOBILE.RESPONSIVE.APP`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: Responsive 5-tab bottom navigation (`Trang chủ`, `Công việc`, `Tạo nhanh`, `Nội bộ`, `Cá nhân`), touch-friendly slide-in inspection sheets, quick emergency controls on mobile.
- **DEPENDENCIES**: `P0-E`, `P0-F`.
- **SIDE_EFFECT_CLASS**: `ADMIN_MOBILE_UX`
- **OWNER_GATE**: Standard PR review.
- **PASS_GATE**: Full 5-tab responsive navigation and inspection sheets on mobile viewports.

---

### 3.3 Phase 2: Production Hardening & Global Verification (1 Task)

#### [P2-A] Locale Purity, End-to-End Verification & Production Readiness
- **TASK_ID**: `P2.WEBAPP.V3-N.LOCALE.E2E.PRODUCTION.HARDENING`
- **REPOSITORY**: `toan-aas-standalone`
- **PURPOSE**: 100% bilingual locale completeness check (Zero raw English in VI, zero VI in EN, zero raw translation keys). Playwright end-to-end regression suite across desktop and mobile viewports. Lighthouse performance audit ($\ge 90$ across Performance, Accessibility, Best Practices, SEO). Read-only cross-system integration acceptance between Web and Bot.
- **DEPENDENCIES**: All P0 and P1 tasks.
- **SIDE_EFFECT_CLASS**: `VERIFICATION_AND_PRODUCTION_SIGN_OFF`
- **OWNER_GATE**: Complete E2E pass, zero lint/locale failures, Lighthouse $\ge 90$.
- **PASS_GATE**: 100% quality gate pass and production deployment readiness.

---

## 4. Single-Agent & Anti-Overengineering Governance Rules
1. **Single-Agent by Default**: All tasks executed sequentially by 1 agent from A to Z.
2. **Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`)**: Changes must be surgical and focused strictly on the assigned task scope.
3. **No Speculative Frameworks (`YAGNI=ON`)**: Do not introduce heavy frontend frameworks (React/Vue/Next.js). Maintain existing vanilla modern JS and performant CSS structure.
4. **Early Stop (`EARLY_STOP=ON`)**: Stop calling tools immediately once verification tests pass.
5. **Owner Safety Gates**: Zero financial mutations during tests, zero table drops, zero unverified API calls, VPS-only deployment truth.
