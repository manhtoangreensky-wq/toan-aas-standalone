# Web App V3 Rebased Master Plan & Transition Roadmap
> **Task**: `P0.WEBAPP.V3.AUDIT.CANONICAL.ARCHITECTURE.TRUTH.CLOSURE`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Authoritative Base SHA**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`

---

## 1. Executive Summary & Strategy Pivot

The previous linear sequence (`V2-08` through `V2-15`) suffered from structural limitations:
1. **Catalog Flattening**: Exposing 135 technical subroutines in a flat directory obscured core product offerings and caused user cognitive overload.
2. **Planning-Only Video Studio**: `copyfast_video_studio.py` (39 routes, 10,215 lines) remained a prompt generator with zero execution, zero worker dispatch, zero MP4 outputs, and zero wallet interaction (`INDEPENDENT_SOURCE_VERIFIED`).
3. **Invented Execution Claims**: Prior documents assumed Celery/Redis; source verification confirms canonical execution uses **SQLite `video_jobs` outbox lease/claim** via `services/remote_worker_api.py` and `remote_worker.py` on systemd (`INDEPENDENT_SOURCE_VERIFIED`).
4. **Billing Invariant**: Product Video charges the customer wallet **ONLY after successful final delivery** (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`). Pre-render debit models are unverified and prohibited (`INDEPENDENT_SOURCE_VERIFIED`).
5. **Theme & Contrast Regressions**: Forced navy blue tokens (`#075985`, `#0b2545`) compromised brand identity and broke WCAG AA contrast rules in active/pressed states.
6. **Publishing Separation**: Publishing (AutoPost) is a downstream orchestrator consuming finished artifacts, not a sub-feature of video rendering.

This master plan formally retires the old V2 sequence and establishes an evidence-driven, product-centric V3 roadmap organized into **12 Bounded Implementation Tasks**.

---

## 2. Legacy Task Disposition Matrix (V2-08 -> V2-15)

| Legacy Task ID | Original Title | Disposition | Target V3 Task | Rationale & Architectural Realignment |
| :--- | :--- | :--- | :--- | :--- |
| **V2-08** | Admin Customer Detail & Lifetime Analytics Workspace | **SPLIT & MOVED** | `P0-E: Admin Customer 360` & `P0-B1/B2: Runtime Connectivity` | Customer 360 profile, CRM leads, and support belong in unified Customer Workspace; financial mutations require canonical bridge adapter. |
| **V2-09** | Admin System Health, Log Explorer & Audit Telemetry Hub | **MOVED & CONSOLIDATED** | `P0-F: Admin Worker Fleet & System Telemetry` | Monitor live SQLite outbox lease/claim and systemd worker processes on VPS (`tg.toanaas.vn`). |
| **V2-10** | Customer Unified Media Studio (Voice, Video, Music, Subtitle) | **REPLACED & DECOMPOSED** | `P0-D: Video Studio`, `P1-A: Voice`, `P1-B: Music & SFX`, `P1-C: SubDub` | Grouping 4 distinct product lines into one monolithic page violates family separation. Decomposed into independent product engines. |
| **V2-11** | Customer Multi-Scene Video Production Workflow | **MERGED** | `P0-D: End-to-End Product Video Studio` | Multi-scene storyboard composition is integral to the Video Studio pipeline, not a detached workflow. |
| **V2-12** | Customer Publishing, Webhook & Distribution Hub | **REPLACED & UPGRADED** | `P1-D: AutoPost Publishing Automation` | Upgraded to full AutoPost specification (Common Publishable Artifact, durable schedule, multi-channel receipts, publish-only retry). |
| **V2-13** | Admin Catalog & Pricing Governance Center | **REPLACED** | `P0-C: Customer IA & 10 Product Catalog` | Replaced flat 135-feature catalog with governance over the 10 distinct customer product families. |
| **V2-14** | Admin Live Delivery Control & Worker Fleet Orchestrator | **MERGED** | `P0-F: Admin Worker Fleet & System Telemetry` | Merged into single operations control center. |
| **V2-15** | Final Quality, Performance & Production Hardening | **KEPT & EXPANDED** | `P2-A: Locale Purity & E2E Production Hardening` | Retained as final end-to-end verification gate across Web and cross-repo integration. |

---

## 3. Rebased V3 Implementation Roadmap (12 Bounded Tasks)

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

    subgraph Phase 1: Independent Product Engines & AutoPost (P1)
        P1A["P1-A: AI Voice & Speech Synthesis Studio"]
        P1B["P1-B: Music & Foley SFX Studio"]
        P1C["P1-C: SubDub & Multilingual Translation Suite"]
        P1D["P1-D: AutoPost Publishing & Distribution Hub"]
        P1E["P1-E: Internal Admin Mobile App (5-Tab Web)"]

        P0A --> P1A
        P0A --> P1B
        P0D --> P1C
        P0D --> P1D
        P1C --> P1D
        P0F --> P1E
    end

    subgraph Phase 2: Production Hardening & Global Verification (P2)
        P2A["P2-A: Locale Purity, E2E Regression & Production Hardening"]

        P1A --> P2A
        P1B --> P2A
        P1C --> P2A
        P1D --> P2A
        P1E --> P2A
    end
```

---

### 3.1 Phase 0: Foundations, Connectivity & Flagship Video Studio (P0)

#### [P0-A] Visual System Rebase to Light Teal / Mint & Contrast Hardening
- **Task ID**: `P0.WEBAPP.V3-A.TEAL.MINT.THEME.REBASE`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Purge forced navy blue tokens (`--portal-customer-blue-rail: #075985`, `--portal-blue-dark-*`) from `portal-theme.css`.
  - Implement canonical Light Teal / Mint tokens (`#f3fbfc`, `#ffffff`, `#0d9488`, `#14b8a6`, `#073a45`, `#e6f7f6`).
  - Fix all active/pressed state contrast failures to meet WCAG AA ($\ge 4.5:1$ text, $\ge 3:1$ graphical).
  - Enforce motion budget (120–180ms ease-out, zero layout thrash, `prefers-reduced-motion`).
- **Dependencies**: None.
- **Exit Criteria**: Zero navy blue rail overrides; 100% WCAG AA contrast compliance in automated audits.

#### [P0-B1] Web Runtime 502, Zero-Downtime Deploy & Telegram Linking (WEB)
- **Task ID**: `P0.WEBAPP.V3-B1.RUNTIME.DEGRADATION.UX`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Implement zero-downtime deploy reload on Web App (Nginx `proxy_next_upstream error timeout http_502 non_idempotent;`, uvicorn graceful reload).
  - Resolve `ACCOUNT_TELEGRAM_UNLINKED` (409) application state by rendering a friendly Telegram deep-linking card with 6-digit OTP pairing UI.
  - Bridge consumer contract: resilient envelope handling for degraded states.
- **Dependencies**: None.
- **Exit Criteria**: Zero Nginx 502 during deploy restarts; unlinked accounts display actionable linking workflow.

#### [P0-B2] Bot Core Canonical Admin Read Endpoints (BOT)
- **Task ID**: `P0.BOT.V3-B2.ADMIN.CANONICAL.READ.ENDPOINTS`
- **Repository**: `manhtoangreensky-wq/bot` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Implement missing authenticated read-only admin endpoints in `bot.py`:
    - `GET /internal/v1/admin/wallet`
    - `GET /internal/v1/admin/revenue`
    - `GET /internal/v1/admin/refunds`
    - `GET /internal/v1/admin/users`
  - Enforce authentication via internal loopback token / shared HMAC.
- **Dependencies**: None.
- **Exit Criteria**: Bot Core returns HTTP 200 with truthful JSON for all 4 admin endpoints.

#### [P0-C] Customer Information Architecture & 10 Product Hubs
- **Task ID**: `P0.WEBAPP.V3-C.CUSTOMER.IA.10.PRODUCTS`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Rebuild customer sidebar into 13 canonical items grouped into 4 functional tiers.
  - Reorganize 135 catalog features into 10 distinct product families.
  - Implement primary product landing cards with quick-start templates, asset history, and direct studio links.
  - Secondary tool discovery drawers with search, tag filters, and usage counters.
- **Dependencies**: `P0-A`.
- **Exit Criteria**: Customer navigation conforms strictly to the 13-item contract; all features accessible without catalog clutter.

#### [P0-D] End-to-End Product Video Studio (Canonical Worker & Billing Integration)
- **Task ID**: `P0.WEBAPP.V3-D.PRODUCT.VIDEO.STUDIO.E2E`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Upgrade `copyfast_video_studio.py` from prompt-planner into a full-featured video production studio.
  - Multi-scene storyboard grid: drag-and-drop scene ordering, aspect ratio preview, bulk scene edits.
  - Preflight quote: capability check and price calculation via canonical bridge.
  - Job creation: atomic insert into canonical SQLite `video_jobs` outbox via bridge (`video_dispatch_outbox` lease/claim).
  - Monitoring & Delivery: live scene progress polling, HTML5 MP4 player, signed download link.
  - Billing invariant: verify customer wallet charge occurs ONLY after successful final delivery (`FINAL_DELIVERY_REQUIRED_BEFORE_CHARGE=YES`, `FAILED_NO_CHARGE=0_XU`).
- **Dependencies**: `P0-A`, `P0-B1`, `P0-B2`, `P0-C`.
- **Exit Criteria**: User can compose a 3-scene video, confirm quote, trigger job run in SQLite outbox, play generated MP4 in-browser, and verify post-delivery wallet deduction.

#### [P0-E] Admin Customer 360, CRM Leads & Audited Operations Hub
- **Task ID**: `P0.WEBAPP.V3-E.ADMIN.CUSTOMER.360.OPERATIONS`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Unified Customer 360 view: account profile, balance, lifetime spending, active jobs, Telegram pairing status.
  - CRM lead management pipeline: contact requests, consultation tickets, conversion status.
  - Audited manual topup operations: 3-layer reconciliation proofs, draft approvals, and idempotent credit invocation via bridge.
  - Enforce boundary: all actions confined strictly to `ADMIN_PRODUCT_CONTROL` (no raw SQL, no arbitrary balance modification).
- **Dependencies**: `P0-B1`, `P0-B2`.
- **Exit Criteria**: Admin can inspect customer 360 records, manage CRM leads, and issue audited topup approvals.

#### [P0-F] Admin Worker Fleet Telemetry & Live VPS Control
- **Task ID**: `P0.WEBAPP.V3-F.ADMIN.WORKER.FLEET.TELEMETRY`
- **Repository**: `toan-aas-standalone` (ONE_REPO, ONE_BRANCH, ONE_PR)
- **Scope**:
  - Monitor canonical worker fleet: query SQLite `video_dispatch_outbox` lease/claim states and claim heartbeats (`services/remote_worker_api.py`).
  - Monitor systemd worker processes on VPS (`tg.toanaas.vn`).
  - Dead-letter queue (DLQ) recovery: view failed tasks with error diagnostics; single-click task re-dispatch to outbox.
- **Dependencies**: `P0-B1`, `P0-B2`.
- **Exit Criteria**: Real-time visibility into outbox claim depth and worker status; DLQ recovery actionable from UI.

---

### 3.2 Phase 1: Independent Product Engines & AutoPost (P1)

#### [P1-A] AI Voice & Speech Synthesis Studio
- **Task ID**: `P1.WEBAPP.V3-G.VOICE.AUDIO.STUDIO`
- **Repository**: `toan-aas-standalone`
- **Scope**: Voice selection library, emotional inflection controls, audio preview player, waveform visualizer, MP3/WAV downloads.
- **Dependencies**: `P0-A` (Independent of Product Video).

#### [P1-B] Music & Foley Sound Effects (SFX) Studio
- **Task ID**: `P1.WEBAPP.V3-H.MUSIC.SFX.STUDIO`
- **Repository**: `toan-aas-standalone`
- **Scope**: Strictly separated from SubDub. Background music (BGM) generation, Foley SFX library, volume ducking, audio stem mixer.
- **Dependencies**: `P0-A` (Independent of Product Video and SubDub).

#### [P1-C] SubDub & Multilingual Translation Suite
- **Task ID**: `P1.WEBAPP.V3-I.SUBDUB.TRANSLATION.SUITE`
- **Repository**: `toan-aas-standalone`
- **Scope**: Strictly separated from Music. Auto-transcription SRT/VTT timeline editor, multilingual speech dubbing, subtitle burn-in. Consumes finished videos or standalone uploads.
- **Dependencies**: `P0-A`, `P0-D` (for video asset handoff).

#### [P1-D] AutoPost — Publishing Automation, Scheduling & Multi-Channel Distribution
- **Task ID**: `P1.WEBAPP.V3-J.AUTPOST.PUBLISHING.HUB`
- **Repository**: `toan-aas-standalone`
- **Scope**:
  - Consumes Common Publishable Artifacts from Product Video, Video Edit, SubDub, or existing user media.
  - AutoPost owns: orchestration, review, approval, schedule, publish, receipt, publish-only retry, and audit.
  - Multi-channel adapters (TikTok, YouTube Shorts, Facebook Reels) with durable schedule persistence across server restarts.
  - Enforce: `HTTP_200 != PUBLISHED`; platform receipt binding required.
  - Retry publication step must NEVER rerun upstream video rendering.
  - Video split/batching: parent batch managing independent child publication units.
- **Dependencies**: `P0-D` and Common Publishable Artifact contract.

#### [P1-E] Internal Admin Mobile-Optimized Web App (5-Tab Architecture)
- **Task ID**: `P1.WEBAPP.V3-K.ADMIN.MOBILE.RESPONSIVE.APP`
- **Repository**: `toan-aas-standalone`
- **Scope**: Responsive 5-tab bottom navigation (`Trang chủ`, `Công việc`, `Tạo nhanh`, `Nội bộ`, `Cá nhân`), touch-friendly slide-in inspection sheets, quick emergency controls on mobile.
- **Dependencies**: `P0-E`, `P0-F`.

---

### 3.3 Phase 2: Production Hardening & Global Verification (P2)

#### [P2-A] Locale Purity, End-to-End Verification & Production Readiness
- **Task ID**: `P2.WEBAPP.V3-L.LOCALE.E2E.PRODUCTION.HARDENING`
- **Repository**: `toan-aas-standalone`
- **Scope**:
  - 100% bilingual locale completeness check (Zero raw English in VI, zero VI in EN, zero raw translation keys).
  - Playwright end-to-end regression suite across desktop and mobile viewports.
  - Lighthouse performance audit ($\ge 90$ across Performance, Accessibility, Best Practices, SEO).
  - Read-only cross-system integration acceptance between Web and Bot.
- **Dependencies**: All P0 and P1 tasks.

---

## 4. Single-Agent & Anti-Overengineering Governance Rules
1. **Single-Agent by Default**: All tasks executed sequentially by 1 agent from A to Z.
2. **Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`)**: Changes must be surgical and focused strictly on the assigned task scope.
3. **No Speculative Frameworks (`YAGNI=ON`)**: Do not introduce heavy frontend frameworks (React/Vue/Next.js). Maintain existing vanilla modern JS and performant CSS structure.
4. **Early Stop (`EARLY_STOP=ON`)**: Stop calling tools immediately once verification tests pass.
5. **Owner Safety Gates**: Zero financial mutations during tests, zero table drops, zero unverified API calls, VPS-only deployment truth.
