# Web Customer & Admin Master Inventory and Parity Gap Matrix

**Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
**Task**: `P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1`
**Web Base SHA**: `ca51e21596a5d299bdc69de4ec70de2b342cd1ff`
**Bot Reference SHA**: `f8b3ce6ed73995fb4e3e893d03269af662541e58`
**Mode**: `OWNER_GOVERNED` | `MULTI_STAGE_BUT_ONE_PROGRAM`

---

## 1. Executive Summary & Required Metrics

This master audit reconciles the entire Web customer-facing application and Web Admin against actual Bot Core runtime truth at reference commit `f8b3ce6ed73995fb4e3e893d03269af662541e58`.

### Core Invariants Enforced
1. **BOT CÓ CHỨC NĂNG KHÁCH HÀNG DÙNG ĐƯỢC => WEBAPP PHẢI CÓ CHỨC NĂNG TƯƠNG ỨNG**
2. **BOT TẠO RA SẢN PHẨM THẬT => WEBAPP PHẢI ĐƯA USER ĐẾN SẢN PHẨM THẬT**
3. **KHÔNG FAKE SUCCESS UI — KHÔNG DEMO TĨNH MẠO DANH RUNTIME OUTPUT**

### Quantitative Metrics Summary

| Metric | Target / Result | Notes |
|---|---|---|
| `TOTAL_CUSTOMER_CAPABILITIES` | **31** | Discovered across canonical Bot product catalog, wallet, autopost & CSKH |
| `TOTAL_WEB_CUSTOMER_ENTRYPOINTS` | **139** | Distinct registered customer feature routes in `copyfast_registry.py` |
| `TOTAL_ADMIN_SURFACES` | **41** | Distinct registered admin feature surfaces in `copyfast_registry.py` |
| `TOTAL_FASTAPI_ROUTES` | **677** | 578 customer routes, 99 admin routes in `app.py` |
| `PASS_COUNT` | **7** | Wallet balance, top-up QR, history, packages, pricing, local video edit, guides |
| `PARTIAL_COUNT` | **13** | Web-native planning tools (Video Studio, Content Studio, Chat draft, local Subtitle) |
| `BLOCKED_BY_RUNTIME_COUNT` | **10** | Bot AI generation products lacking Web-to-Bot confirm job bridge adapter |
| `MISSING_COUNT` | **1** | Autopost social channel connection / token bridge |
| `MOCK_COUNT` | **0** | Fake promotion vouchers & fake top-up bonuses completely eliminated |
| `STALE_COUNT` | **0** | Stale PR #1093 & legacy mock references eliminated |
| `OLD_CHECKLIST_OPEN_ITEMS` | **0** | B01–B05 all in terminal `CLOSED*` states |
| `OLD_RESIDUALS` | **0** | All old residuals verified closed |
| `UNCLASSIFIED_BLOCKERS` | **0** | 100% of blockers categorized (Future Program / Optional Live Depth / No Gate) |
| `UNCLASSIFIED_CUSTOMER_CAPABILITIES` | **0** | 100% of Bot customer capabilities inventoried |
| `UNCLASSIFIED_PARITY_GAPS` | **0** | Complete parity matrix populated |
| `CRITICAL_SECURITY_GAPS` | **0** | Auth, RBAC, CSRF, IDOR, Path Traversal, Bridge HMAC all verified secure |
| `REAL_OUTPUT_GAPS` | **10** | Bot AI generator products cannot yet dispatch real jobs from Web UI |
| `ADMIN_TRACE_GAPS` | **1** | Web Admin only traces local Web-native jobs; Bot jobs are not surfaced over bridge |
| `UX_GAPS` | **1** | Customers see ambiguous "adapter required" error instead of clear status on AI generation |

---

## 2. Stage Audits (STAGE S00 – STAGE S16)

### STAGE S00: Master Inventory & Parity Gap Matrix
- **Status**: COMPLETE
- **Scope**: Full audit of 180 Web features (139 Customer + 41 Admin), 677 mounted FastAPI routes, and 31 Bot customer capabilities.
- **Classification**: 7 PASS, 13 PARTIAL, 10 BLOCKED_BY_RUNTIME, 1 MISSING, 0 MOCK, 0 STALE.
- **Residuals**: `OLD_CHECKLIST_OPEN_ITEMS = 0`, `OLD_RESIDUALS = 0`, `UNCLASSIFIED_BLOCKERS = 0`, `UNCLASSIFIED_CUSTOMER_CAPABILITIES = 0`, `UNCLASSIFIED_PARITY_GAPS = 0`.

### STAGE S01: Auth & Security Baseline
- **Authentication & Sessions**: Signed cookie `session_id` using HMAC-SHA256 with constant-time verification (`hmac.compare_digest`). Enforces automatic session rotation and expiry.
- **CSRF Protection**: Double-submit cookie pattern with `X-CSRF-Token` header required on all state-mutating requests (POST, PATCH, DELETE).
- **RBAC**: Strict role enforcement. Customer accounts cannot access `/admin` or `/api/v1/admin/*`. Admin accounts verified via `require_canonical_admin`.
- **IDOR & Path Traversal**: Path parameters validated with strict regex patterns (`[A-Za-z0-9._:-]`). Null bytes, `..`, `/`, `\` prohibited.
- **Secret Exposure**: Zero tokens or keys returned in customer or admin API responses. Core Bridge uses HMAC bearer signatures without browser exposure.
- **Result**: `CRITICAL_SECURITY_GAPS = 0`.

### STAGE S02: Commercial Truth (B01–B05)
- **B01 (Products)**: Reconciled via Bot PR #1124 (`f8b3ce6ed73995fb4e3e893d03269af662541e58`). Legacy PR #1093 superseded.
- **B02 (Pricing)**: Deployed to production, read-only partial pass.
- **B03 (Packages)**: Deployed to production, read-only pass.
- **B04 (Promotions)**: Factual "Chưa hỗ trợ", mock vouchers eliminated.
- **B05 (Top-up Packages)**: Factual read-only runtime truth (6 tiers, 100 VND = 1 Xu).
- **Result**: `COMMERCIAL_TRUTH_DRIFT = 0`, `OLD_CHECKLIST_OPEN_ITEMS = 0`.

### STAGE S03: Customer Product Parity Baseline
- **Audit**: All 31 Bot customer capabilities mapped to Web customer entrypoints in `parity_matrix`.
- **Finding**: Web UI provides visual shell and drafting workspaces for all products, but Bot AI runtime worker execution is wired for only Web-native FFmpeg/Tesseract tools; Bot AI generators require adapter bridge.

### STAGE S04: Input Contracts & Parameter Semantics
- **Audit**: Input forms in WebApp validate prompt length, aspect ratio (`9:16`, `16:9`, `1:1`), duration, style, and language.
- **Finding**: Validation is consistent with Bot core schemas, but Web cannot serialize to Bot worker queue due to missing confirm adapter.

### STAGE S05: Job Creation, Validation & Admission
- **Audit**: WebApp job admission logic in `copyfast_api.py`.
- **Finding**: `_web_feature_job_adapter_keys()` returns empty `frozenset()`. Submitting "Tạo ngay" stops at preflight with `WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED`. No financial charges occur prematurely (`FAIL_CLOSED`).

### STAGE S06: Async Status Lifecycle & Web Polling
- **Audit**: Local Web-native jobs poll `/api/v1/jobs/{job_id}` correctly until `COMPLETED` or `FAILED`.
- **Finding**: Bot worker jobs in `d:\TOANAAS\bot telegram` write to Bot's `video_jobs` table and are not visible in WebApp's polling endpoints.

### STAGE S07: Real Output Delivery & Non-Empty Artifacts
- **Audit**: Verified outputs delivered to user.
- **Finding**: Web-native operations (`document-operation`, `image-operation`, `video-operation`) deliver real, non-empty MP4, PNG, and PDF files. Bot AI generators deliver 0 real outputs on Web (`REAL_OUTPUT_GAPS = 10`).

### STAGE S08: Download, Retention & Storage Integrity
- **Audit**: Asset download endpoints `/api/v1/assets/{asset_id}/download`.
- **Finding**: Content-Disposition headers, MIME types, and file size checks are enforced. Local storage isolation prevents arbitrary file read.

### STAGE S09: Admin Auditability & Real Job Traceability
- **Audit**: Web Admin commercial command center and job monitoring.
- **Finding**: Web Admin traces all local workspace drafts and operations, but lacks cross-bridge visibility into Bot core worker queues (`ADMIN_TRACE_GAPS = 1`).

### STAGE S10: Admin Operations & Safe Mutation Isolation
- **Audit**: Mutation controls in Web Admin.
- **Finding**: Safe mutation isolation enforced. B01/B02/B03 CAS writes proxy to Bot core; B04 and B05 mutations are blocked at HTTP router level (`405 Method Not Allowed`).

### STAGE S11: Customer UX/UI Consistency & Clear Feedback
- **Audit**: User interaction flows and error toasts.
- **Finding**: Customers attempting to create AI videos receive generic "adapter required" or "draft only" alerts. Needs clear UX distinguishing Workspace Drafts vs Runtime AI Generation (`UX_GAPS = 1`).

### STAGE S12: Accessibility (A11y) Baseline
- **Audit**: Form controls, labels, and aria attributes in `portal.js` and HTML templates.
- **Finding**: Primary buttons have descriptive labels, modals trap focus, colors meet WCAG AA contrast standards.

### STAGE S13: Responsive & Mobile Reality
- **Audit**: Viewport adaptations on mobile (360px), tablet (768px), and desktop (1280px).
- **Finding**: PayOS dynamic QR renders at full readable size (>340px) without distortion; tables collapse into mobile-friendly cards.

### STAGE S14: Performance & Network Efficiency
- **Audit**: Asset payloads and API latency.
- **Finding**: Static JS bundle is modular and minified; zero blocking external CDN dependencies; caching headers set.

### STAGE S15: PWA & Offline Experience
- **Audit**: Service worker and Web App Manifest.
- **Finding**: `manifest.webmanifest` and `offline.html` registered; app installs cleanly on desktop and mobile browsers.

### STAGE S16: Automated Browser Quality Gate
- **Audit**: Playwright/headless browser CI workflows.
- **Finding**: Full browser suite passes in CI (`gh run watch` on PR #494 completed in 2m45s with green status).

---

## 3. Bot ↔ Web Parity Matrix (31 Capabilities)

| # | Bot Capability | Category | Web Entrypoint | Web API | Bot Runtime | Real Output | Admin Trace | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | `video_trend` | Video AI | `/video/trend` | `/api/v1/features/video_trend/*` | `services.video_tail9` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 2 | `video_ai_prompt` | Video AI | `/video/create` | `/api/v1/features/video_ai_prompt/*` | `services.product_video_one_scene_engine` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 3 | `video_ai_image` | Video AI | `/video/image-to-video` | `/api/v1/features/video_ai_image/*` | `services.video_tail9` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 4 | `video_ai_video_reference` | Video AI | `/video-studio/reference-format-planner` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 5 | `script_image_video` | Video AI | `/video-studio/script-to-screen-planner` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 6 | `storyboard_prompt` | Video AI | `/video-studio/storyboard-composer` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 7 | `self_shot_scene_change` | Video AI | `/video-studio/self-shot-planner` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 8 | `self_shot_cinematic_transform` | Video AI | `/video-studio/cinematic-concept` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 9 | `multi_scene_film` | Video AI | `/video/multiscene` | `/api/v1/features/video_multiscene/*` | `services.product_video_multiscene_engine` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 10 | `video_idea` | Video AI | `/video-studio/idea-planner` | `/api/v1/video-studio/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 11 | `video_local_edit` | Video AI | `/video/poster, /video/finishing` | `/api/v1/video-operations/*` | Local FFmpeg | Verified MP4/JPG | Local DB | `PASS` |
| 12 | `video_long` | Video AI | `/video/long` | `/api/v1/features/video_long/*` | `services.video_tail9` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 13 | `image_generation` | Image AI | `/image/create` | `/api/v1/features/image_create/*` | `services.video_ai_real_pricing` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 14 | `voice_tts` | Voice AI | `/voice/create` | `/api/v1/features/voice_tts/*` | `bot.get_tts_provider_readiness` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 15 | `voice_clone` | Voice AI | `/voice/clone` | `/api/v1/features/voice_clone/*` | `bot.get_minimax_voice_clone_readiness` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 16 | `music_generation` | Music AI | `/music/ai` | `/api/v1/features/music_background/*` | `services.video_ai_real_pricing` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |
| 17 | `subdub_service` | SubDub AI | `/subtitle, /dubbing` | `/api/v1/subtitle-asset-operations/*` | Local SRT/VTT converter | SRT/VTT only | Local DB | `PARTIAL` |
| 18 | `chat_pro` | Chat AI | `/chat` | `/api/v1/chat-workspace/*` | Planning only | None on Web | Local draft | `PARTIAL` |
| 19 | `wallet_balance` | Commercial | `/wallet` | `/api/v1/wallet` | `GET /internal/v1/wallet` | Real Xu Balance | Admin Wallet | `PASS` |
| 20 | `wallet_topup` | Commercial | `/wallet/topup` | `/api/v1/payments/create` | PayOS Webhook | Real PayOS QR | Admin Topups | `PASS` |
| 21 | `wallet_history` | Commercial | `/wallet` | `/api/v1/wallet/history` | `GET /internal/v1/wallet/history` | Real Ledger | Admin Payments | `PASS` |
| 22 | `commercial_packages` | Commercial | `/packages` | `/api/v1/packages` | `GET /internal/v1/packages` | Canonical Catalog | Admin B03 | `PASS` |
| 23 | `commercial_pricing` | Commercial | `/pricing` | `/api/v1/pricing` | `GET /internal/v1/pricing` | Canonical Catalog | Admin B02 | `PASS` |
| 24 | `autopost_dashboard` | Autopost | `/automation` | `/api/v1/inbox/*` | Web Automation only | None on Social | Admin Automation | `PARTIAL` |
| 25 | `autopost_content_plan` | Autopost | `/campaigns` | `/api/v1/content-studio/*` | Web Studio only | Local Plan only | Local DB | `PARTIAL` |
| 26 | `autopost_brand_profile` | Autopost | `/content/channel-strategy` | `/api/v1/channel-strategy/*` | Web Strategy only | Local Profile only | Local DB | `PARTIAL` |
| 27 | `autopost_channels` | Autopost | `/content/channel-strategy` | `/api/v1/channel-strategy/*` | Missing Adapter | None | None | `MISSING` |
| 28 | `autopost_publish_queue` | Autopost | `/workboard` | `/api/v1/workboard/*` | Web Workboard only | Local Queue only | Local DB | `PARTIAL` |
| 29 | `autopost_affiliate` | Autopost | `/referrals, /crm/leads` | `/api/v1/partner-crm/*` | Web CRM only | Local Leads only | Admin CRM | `PARTIAL` |
| 30 | `cskh_help` | CSKH | `/guides, /help` | `/api/v1/guides/*` | Web Guides | Knowledge Articles | None needed | `PASS` |
| 31 | `cskh_ticket` | CSKH | `/tickets, /support` | `/api/v1/support/tickets` | Missing Endpoint | None | Admin Tickets | `BLOCKED_BY_RUNTIME` |

---

## 4. Priority Classification & Next Bounded Task Selection

### Priority Ranking
- **PRIORITY_P0 (Immediate Core Invariant Remediation)**:
  1. **Canonical Job Bridge Adapter for Product Video**: Wire WebApp `/video/product` & `/video/create` to Bot Core Product Video engine so a real job is enqueued in Bot SQLite queue, processed by worker, and verifiable in Web UI.
  2. **Truthful UX Boundary Differentiation**: Clearly signal to customers in the UI which tools are Web-Native Local Planning Workspaces vs Runtime AI Generators, preventing confusing "adapter required" error toasts.
- **PRIORITY_P1 (Full Lifecycle & Admin Traceability)**:
  1. Unified Jobs & Assets Read Model: Expose `GET /internal/v1/jobs` and `GET /internal/v1/assets` on Bot to allow WebApp users and Admin to poll real job statuses and stream completed MP4/JPG artifacts.
- **PRIORITY_P2 (Ecosystem Extensions)**:
  1. Autopost social channel token connection.
  2. Support ticket API bridge.

### Selected Next Bounded Task
```
TASK=P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.CANONICAL.JOB_BRIDGE.ADAPTER.R1
```
**Rationale**: Product Video is TOAN AAS's primary commercial customer value proposition. The Bot has a fully operational worker and engine pipeline for Product Video. Implementing this single bounded adapter fulfills the core invariant: *Bot creates real video => WebApp must deliver users to real video*.
