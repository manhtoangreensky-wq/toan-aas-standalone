# Web App V3 Rebased Master Plan & Transition Roadmap
**Scope:** TOAN AAS Web App (`toan-aas-standalone`)
**Program:** `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
**Task:** `P0.WEBAPP.V3.FULL.PRODUCT.IA.UX.ADMIN.REBASE.AUDIT`
**Status:** Canonical Roadmap Specification (`OWNER-GOVERNED`)
**Base Commit:** `8873e10f2279aec0fb312b70388b9073ba763f13`

---

## 1. Executive Summary & Strategy Pivot

The previous linear sequence (`V2-08` through `V2-15`) suffered from structural limitations:
1. **Flat Code Catalog vs Real Products:** Lumping 135 technical subroutines into a single flat directory concealed the core product offerings and overwhelmed customers.
2. **Planning-Only Video Studio:** `copyfast_video_studio.py` remained a text-only prompt generator with zero execution, zero provider dispatch, and zero MP4 outputs.
3. **Disconnected Admin Model:** Admin pages operated as isolated prototypes without complete customer <-> admin entity linkage and lacked alignment with the 21 internal business domains proven in enterprise operations.
4. **Theme & Contrast Regressions:** Forced navy blue rail and buttons broke brand identity and violated WCAG AA contrast standards.
5. **Runtime 502 Failures:** Service reload downtime during deploy, missing Bot admin routes, and unlinked Telegram account states caused gateway errors.

This master plan formally retires the old V2 sequence and establishes an evidence-driven, product-centric V3 roadmap.

---

## 2. Legacy Task Disposition Matrix (V2-08 -> V2-15)

| Legacy Task ID | Original Title | Disposition | Target V3 Task | Rationale & Architectural Realignment |
| :--- | :--- | :--- | :--- | :--- |
| **V2-08** | Admin Customer Detail & Lifetime Analytics Workspace | **SPLIT & MOVED** | `P0-E: Admin Customer 360` & `P0-B: Runtime Connectivity` | Customer 360 profile, CRM leads, and support belong in unified Customer Workspace; financial mutations require 2-man authorization gate. |
| **V2-09** | Admin System Health, Log Explorer & Audit Telemetry Hub | **MOVED & CONSOLIDATED** | `P0-F: Admin Worker Fleet & System Telemetry` | Merge log explorer and health monitoring directly with VPS worker fleet telemetry (`tg.toanaas.vn`). |
| **V2-10** | Customer Unified Media Studio (Voice, Video, Music, Subtitle) | **REPLACED & DECOMPOSED** | `P0-D: Video Studio E2E`, `P1-A: Voice Audio`, `P1-B: Music Subtitle` | Combining 4 major product families into a single monolithic page creates cognitive overload and bloated DOM. Decomposed into dedicated product workspaces. |
| **V2-11** | Customer Multi-Scene Video Production Workflow | **MERGED** | `P0-D: End-to-End Product Video Studio` | Multi-scene storyboard composition is integral to the Video Studio, not a disjointed workflow. Merged into one unified execution pipeline. |
| **V2-12** | Customer Publishing, Webhook & Distribution Hub | **MOVED to P1** | `P1-C: Automated Publishing & Social Distribution` | Downstream distribution belongs in Phase 1, prioritizing real MP4 video generation first. |
| **V2-13** | Admin Catalog & Pricing Governance Center | **REPLACED** | `P0-C: Customer IA & 10 Product Catalog` | Replaced flat 135-feature catalog with governance over the 10 distinct customer product families. |
| **V2-14** | Admin Live Delivery Control & Worker Fleet Orchestrator | **MERGED** | `P0-F: Admin Worker Fleet & System Telemetry` | Merged into single operations control center. |
| **V2-15** | Final Quality, Performance & Production Hardening | **KEPT & EXPANDED** | `P2-A: Locale Purity & E2E Production Hardening` | Retained as final end-to-end verification gate. |

---

## 3. Rebased V3 Implementation Roadmap (Prioritized Backlog)

```mermaid
flowchart TD
    subgraph Phase 0: Foundations & Core Engines (P0)
        P0A["P0-A: Teal/Mint Theme Rebase & Contrast (CSS)"] --> P0C["P0-C: Customer IA & 10 Product Catalog"]
        P0B["P0-B: Zero-Downtime Deploy & Bot Route Parity"] --> P0E["P0-E: Admin Customer 360 & Operations"]
        P0C --> P0D["P0-D: End-to-End Product Video Studio (Execution)"]
        P0E --> P0F["P0-F: Admin Worker Fleet & VPS Telemetry"]
    end

    subgraph Phase 1: Product Expansion & Mobile Admin (P1)
        P0D --> P1A["P1-A: AI Voice & Audio Engine Studio"]
        P0D --> P1B["P1-B: Music, SFX & Subtitle Suite"]
        P0D --> P1C["P1-C: Automated Publishing & Distribution"]
        P0F --> P1D["P1-D: Internal Admin Mobile App (5-Tab Web)"]
    end

    subgraph Phase 2: Production Hardening (P2)
        P1A --> P2A["P2-A: Locale Purity & Production Readiness"]
        P1B --> P2A
        P1C --> P2A
        P1D --> P2A
    end
```

---

### 3.1 Phase 0: Foundations, Connectivity & Flagship Video Studio (P0)

#### [P0-A] Visual System Rebase to Light Teal / Mint & Contrast Hardening
- **Task ID:** `P0.WEBAPP.V3-A.TEAL.MINT.THEME.REBASE`
- **Scope:**
  - Purge forced navy blue tokens (`--portal-customer-blue-rail`, `--portal-blue-dark-*`) from `portal-theme.css`.
  - Implement canonical Light Teal / Mint tokens (`#f3fbfc`, `#ffffff`, `#0d9488`, `#14b8a6`, `#073a45`, `#e6f7f6`).
  - Fix all active/pressed state contrast failures to meet WCAG AA (>= 4.5:1 text, >= 3:1 graphical).
  - Enforce motion budget (120–180ms ease-out, zero layout thrash, `prefers-reduced-motion`).
- **Dependencies:** None.
- **Exit Criteria:** Zero blue-rail overrides, 100% WCAG AA contrast compliance in automated audits.

#### [P0-B] Runtime 502 Remediation, Zero-Downtime Deploy & Bot Route Parity
- **Task ID:** `P0.WEBAPP.V3-B.RUNTIME.CONNECTIVITY.BOT.BRIDGE`
- **Scope:**
  - Implement Nginx upstream retry (`proxy_next_upstream error timeout http_502;`) and uvicorn graceful reload to eliminate deploy downtime.
  - Implement missing Bot Admin Core routes in `bot.py`: `/internal/v1/admin/wallet`, `/revenue`, `/refunds`, `/customers`.
  - Fix unlinked Telegram account state (`409 ACCOUNT_TELEGRAM_UNLINKED`) with user-friendly Telegram deep-linking card and OTP pairing.
- **Dependencies:** None.
- **Exit Criteria:** Zero 502 errors during deployment; admin financial tabs return live data; unlinked accounts display actionable linking workflow.

#### [P0-C] Customer Information Architecture Rebuild & 10 Product Catalog
- **Task ID:** `P0.WEBAPP.V3-C.CUSTOMER.IA.10.PRODUCTS`
- **Scope:**
  - Rebuild customer sidebar into 13 canonical items grouped into 4 functional tiers.
  - Group 135 legacy features under the 10 customer product families.
  - Implement primary product landing cards with quick-start templates, asset history, and direct studio links.
  - Implement secondary tool discovery drawer with search, tag filters, and usage counters.
- **Dependencies:** `P0-A`.
- **Exit Criteria:** Customer navigation conforms strictly to the 13-item contract; all 135 features accessible without catalog clutter.

#### [P0-D] End-to-End Product Video Studio (Real Pipeline & Execution)
- **Task ID:** `P0.WEBAPP.V3-D.PRODUCT.VIDEO.STUDIO.E2E`
- **Scope:**
  - Upgrade `copyfast_video_studio.py` from prompt-planner into a full-featured video production studio.
  - Multi-scene storyboard builder: timeline strip, drag-and-drop scene ordering, duration controls, bulk scene editing.
  - Commercial preflight: capability check, provider resolution, pricing calculator, and quota validation.
  - Real job dispatch: create job record in SQLite, dispatch task to background worker, deduct Xu ledger balance upon confirmation.
  - Real MP4 preview & delivery: poll job status, render streaming video player, download links, and export receipts.
- **Dependencies:** `P0-A`, `P0-B`, `P0-C`.
- **Exit Criteria:** User can compose a 3-scene video, confirm commercial invoice, trigger actual job run, deduct Xu, and play generated MP4 in-browser.

#### [P0-E] Admin Operations Hub & Customer 360 Workspace
- **Task ID:** `P0.WEBAPP.V3-E.ADMIN.CUSTOMER.360.OPERATIONS`
- **Scope:**
  - Unified Customer 360 view: account profile, balance, lifetime spending, active jobs, Telegram connection status.
  - CRM lead management pipeline: contact requests, consultation status, notes.
  - 2-Man manual wallet adjustment interface with mandatory reason code and immutable audit logging.
- **Dependencies:** `P0-B`.
- **Exit Criteria:** Admin can view complete customer history, filter CRM leads, and issue audited balance adjustments.

#### [P0-F] Admin Worker Fleet, System Telemetry & Live VPS Control
- **Task ID:** `P0.WEBAPP.V3-F.ADMIN.WORKER.FLEET.TELEMETRY`
- **Scope:**
  - Live VPS service monitor: status of `toanaas-bot.service`, `toanaas-web.service`, `nginx.service`.
  - Celery/Worker fleet status, queue backlog depth, processing throughput, and failure rate.
  - Dead-letter queue (DLQ) viewer with single-click job retry or refund.
- **Dependencies:** `P0-B`.
- **Exit Criteria:** Real-time visibility into VPS services without SSH terminal; DLQ recovery actionable from UI.

---

### 3.2 Phase 1: Expanded Product Engines & Internal Mobile App (P1)

#### [P1-A] AI Voice & Audio Engine Studio
- **Task ID:** `P1.WEBAPP.V3-G.VOICE.AUDIO.STUDIO`
- **Scope:** Voice selection library, emotional inflection controls, instant audio preview, waveform visualizer, export to MP3/WAV.
- **Dependencies:** `P0-D`.

#### [P1-B] Music, SFX & Subtitle/Dubbing Suite
- **Task ID:** `P1.WEBAPP.V3-H.MUSIC.SUBTITLE.SUITE`
- **Scope:** BGM generation, Foley SFX library, auto-transcription SRT/VTT editor, multilingual audio dubbing synchronization.
- **Dependencies:** `P0-D`.

#### [P1-C] Automated Social Publishing & Distribution Hub
- **Task ID:** `P1.WEBAPP.V3-I.PUBLISHING.DISTRIBUTION.HUB`
- **Scope:** Multi-platform posting scheduler (TikTok, YouTube, Facebook Reels), webhook triggers, postback analytics.
- **Dependencies:** `P0-D`.

#### [P1-D] Internal Admin Mobile-Optimized Web App (5-Tab Architecture)
- **Task ID:** `P1.WEBAPP.V3-J.ADMIN.MOBILE.RESPONSIVE.APP`
- **Scope:** Responsive 5-tab bottom navigation (`Trang chủ`, `Công việc`, `Tạo nhanh`, `Nội bộ`, `Cá nhân`), touch-friendly slide-in inspection drawers, quick emergency controls on mobile.
- **Dependencies:** `P0-E`, `P0-F`.

---

### 3.3 Phase 2: Production Hardening & Global Readiness (P2)

#### [P2-A] Locale Purity, End-to-End Verification & Production Readiness
- **Task ID:** `P2.WEBAPP.V3-K.LOCALE.E2E.PRODUCTION.HARDENING`
- **Scope:**
  - 100% bilingual purity verification (Zero raw English in VI, zero VI in EN, zero raw translation keys).
  - Comprehensive Playwright/Cypress end-to-end regression tests across desktop and mobile viewports.
  - Performance audit: Lighthouse score >= 90 across Performance, Accessibility, Best Practices, and SEO.
- **Dependencies:** All P0 and P1 tasks.

---

## 4. Single-Agent & Anti-Overengineering Governance Rules
1. **Single-Agent by Default:** All tasks must be executed sequentially by 1 agent from A to Z.
2. **Minimal Code Footprint (`MINIMAL_CODE_FOOTPRINT=ON`):** Changes must be surgical and focused strictly on the assigned task scope.
3. **No Speculative Frameworks (`YAGNI=ON`):** Do not introduce heavy frontend frameworks (React/Vue/Next.js). Maintain existing vanilla modern JS and performant CSS structure.
4. **Early Stop (`EARLY_STOP=ON`):** Stop calling tools immediately once verification tests pass.
5. **Owner Safety Gates:** Zero financial mutations during tests, zero table drops, zero unverified API calls, VPS-only deployment truth.
