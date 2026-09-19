# Web App V3 Admin Architecture & Operating Model
> **Task**: `P0.WEBAPP.V3.AUDIT.AUTOPOST.SINGLE.AUTHORITY.FINAL.ALIGNMENT`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Authoritative Base SHA**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`

---

## 1. Operating Model & Governance Boundary

### 1.1 Governance Boundary: Product Control vs Production Gate (`INDEPENDENT_SOURCE_VERIFIED`)

A fundamental rule of the TOAN AAS ecosystem is the absolute separation between business operational controls and production safety gates:

```
+-------------------------------------------------------------------------------+
|                             ADMIN PRODUCT CONTROL                             |
|  Operational actions exposed via canonical adapters in the Admin Web UI:       |
|  - View customer 360 profile, active jobs, and transaction history            |
|  - Inspect job state, provider task payload, and delivery receipts            |
|  - Review and approve manual topup drafts with 3-layer reconciliation proofs   |
|  - Reply to customer support tickets and assign agents                        |
|  - Monitor live worker fleet telemetry and queue backlogs (Read-Only)         |
|  - Pause or retry publication attempts (publish-only via Bot API; never rerunning video)|
+-------------------------------------------------------------------------------+
                                      ||
                     STRICT SECURITY AIR-GAP / BOUNDARY
                                      ||
+-------------------------------------------------------------------------------+
|                            OWNER PRODUCTION GATE                              |
|  PROHIBITED from the Admin Web UI — Requires Owner Authorization:             |
|  - NO raw database editor / arbitrary SQL query console                       |
|  - NO arbitrary wallet balance modifier without audited canonical adapter     |
|  - NO secret / environment variable (.env) editor                             |
|  - NO unbounded systemctl console or shell command execution                  |
|  - NO production queue mutations (re-dispatch/re-queue) without Owner gate    |
+-------------------------------------------------------------------------------+
```

---

## 2. Production Queue Mutation Policy (`TARGET_DESIGN`)

In task `P0-F`, queue operations are divided into two distinct security tiers:
1. **Read-Only Telemetry (Ordinary Observability)**:
   - Real-time visibility into the SQLite `video_dispatch_outbox` table, lease durations, worker heartbeat timestamps, and claim depths.
   - Viewing dead-letter queue (DLQ) task error diagnostics and stack traces.
2. **Production Queue Mutations (`QUEUE_REDISPATCH_OWNER_GATED=YES`)**:
   - Re-queue, re-dispatch, or forced cancellation of queued tasks are production mutations.
   - Raw queue mutation must **NEVER be an unrestricted Admin button**.
   - Queue mutation requires:
     - Canonical adapter enforcing valid state transitions.
     - Authenticated administrator identity with an immutable audit receipt.
     - Proven idempotency key preventing duplicate dispatch.
     - Fresh Owner authorization where required by production governance.

---

## 3. The 13 Canonical Admin Web Domains (`TARGET_DESIGN`)

1. **Live System Dashboard (`/admin`)**: Real-time service status, active users, queue depth, error rates.
2. **Customer 360 (`/admin/customers`)**: Unified customer profile linking account identity, verified wallet balance, job run history, support tickets, and Telegram pairing status.
3. **CRM Leads & Requests (`/admin/leads`)**: Enterprise lead capture, consulting requests, conversion status.
4. **Financial Ledger & Reconciliation (`/admin/finance`)**: PayOS webhook logs, topup volume, revenue breakdown.
5. **Manual Topup Operations (`/admin/topups`)**: 3-layer verification for manual bank transfers, draft approvals, and idempotent credit invocation via Bot Core bridge.
6. **Job Queue Monitor (`/admin/jobs`)**: Status tracking for video, voice, manual edit, and audio jobs across their entire lifecycle.
7. **Dead-Letter Queue (DLQ) Recovery (`/admin/dlq`)**: Isolated failed tasks with error stack traces and Owner-gated retry outbox dispatcher.
8. **Worker Fleet Telemetry (`/admin/workers`)**: Status of systemd-managed Product Video workers on VPS (`tg.toanaas.vn`), claim heartbeats, and queue backlog depths (`services/remote_worker_api.py`).
9. **Catalog & Pricing Governance (`/admin/pricing`)**: Token pricing per model/second, SKU catalog management, and bridge synchronization.
10. **Delivery & Webhook Postbacks (`/admin/delivery`)**: Outbound platform postbacks, external API delivery receipts.
11. **AutoPost Publication Monitor (`/admin/publishing`)**: Scheduled social posts, platform attempt history, publication outbox states, and channel receipts projected directly from Bot AutoPost Core (Web App does NOT maintain a separate execution database).
12. **Operator Audit Logs (`/admin/audit`)**: Immutable chronological log of all administrator actions.
13. **Support Tickets (`/admin/tickets`)**: Integrated helpdesk for resolving customer inquiries and technical disputes.

---

## 4. Internal Mobile App Operating Architecture (Reference Media Analysis)

Based on empirical review of the reference media suite in `evidence/admin-internal-reference-20260827/` (`App nội bộ.mp4`, `app mẫu.mp4`, `bảng chức năng.png`):

### 4.1 Business Domain Alignment (`REFERENCE_MEDIA_OBSERVED`)
The 21 functional rows in `bảng chức năng.png` map into 5 primary mobile operational tabs:

```
+-------------------------------------------------------------------+
|                     INTERNAL MOBILE APP SHELL                     |
|                                                                   |
| [Tab 1: Trang chủ]   -> Real-time KPIs, Red Alerts, System Health |
| [Tab 2: Công việc]   -> Active Job Queue, DLQ Failures, Approvals |
| [Tab 3: Tạo nhanh]   -> Quick Actions (Grant Quota, Fast Ticket)  |
| [Tab 4: Nội bộ]      -> Operator Shifts, Tasks, Internal Handoffs |
| [Tab 5: Cá nhân]     -> Admin Account, Session Security, Settings |
+-------------------------------------------------------------------+
```

### 4.2 Mobile Interaction Guidelines (`TARGET_DESIGN`)
1. **Thumb-Friendly Bottom Navigation**: Fixed bottom navigation bar with 5 primary touch targets.
2. **Slide-In Detail Sheets**: Clicking any item opens an inspection sheet from the bottom (200–240ms ease-out) rather than full page transitions.
3. **No Unconstrained Gamification**: Particle animations, falling stars, or fake marketing badges are strictly excluded from the professional internal tool.
4. **Offline-Safe Read Cache**: Essential emergency contacts and service status cache locally to ensure availability during network drops.
