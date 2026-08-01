# Partner Readiness Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one professional, private Partner Readiness profile per signed Web account without expanding the guarded Bot referral surface or creating financial, provider, job, CRM or public-marketplace behavior.

**Architecture:** `copyfast_partner_readiness.py` owns an additive SQLite profile/version/event/interest-receipt model. It follows the owner-scoped Workspace Setup and Content Handoff conventions: strict input validation, CSRF, idempotency, optimistic revision, audit events, bounded history and safe empty/not-found behavior. Portal presentation is one signed page that hydrates only from this API and retains the teal/cyan private shell, PWA and motion boundaries.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, existing signed-session/CSRF/audit helpers, vanilla Portal JS/CSS, pytest.

---

### Task 1: Prove the private profile lifecycle before production code

**Files:**
- Create: `tests/test_copyfast_partner_readiness.py`
- Create: `tests/test_partner_readiness_portal_contracts.py`

- [ ] **Step 1: Write the failing API contract tests**

Create a test module using the existing isolated `TestClient` pattern from
`tests/test_copyfast_workspace_setup_profile.py` and
`tests/test_copyfast_channel_strategy.py`. Set
`WEBAPP_SESSION_DB_PATH`, `WEB_SESSION_SECRET` and
`WEBAPP_PARTNER_READINESS_ENABLED`, clear imported app modules, and register
two signed accounts.

Use this safe create/update payload:

```python
def profile_payload(key: str, revision: int = 0, **overrides) -> dict:
    payload = {
        "service_focus": "Tư vấn chiến lược nội dung và vận hành sáng tạo",
        "capabilities": ["content_strategy", "creative_production"],
        "availability": "open",
        "rate_display_preference": "on_request",
        "preferred_briefs": ["brand_strategy", "content_campaign"],
        "portfolio_summary": "Tập trung vào quy trình rõ ràng, có review và bàn giao có kiểm soát.",
        "collaboration_note": "Ưu tiên brief có mục tiêu, phạm vi và tiêu chí review rõ ràng.",
        "visibility_draft": "private",
        "expected_revision": revision,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload
```

Add exact expected lifecycle assertions:

```python
assert client.get("/api/v1/partner-readiness/profile").status_code == 401
csrf = login(client, "partner-owner@example.com")
assert client.patch("/api/v1/partner-readiness/profile", json=profile_payload("partner-create-0001")).status_code == 403
created = client.patch("/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf}, json=profile_payload("partner-create-0001"))
assert created.status_code == 200 and created.json()["data"]["profile"]["state"] == "draft"
assert client.post("/api/v1/partner-readiness/profile/request-review", headers={"X-CSRF-Token": csrf}, json={"expected_revision": 1, "idempotency_key": "partner-review-0001"}).json()["data"]["profile"]["state"] == "review"
interest = client.post("/api/v1/partner-readiness/profile/interest", headers={"X-CSRF-Token": csrf}, json={"expected_revision": 2, "confirm_interest": True, "idempotency_key": "partner-interest-0001"})
assert interest.status_code == 200 and interest.json()["data"]["profile"]["state"] == "submitted"
assert interest.json()["data"]["interest_submitted"] is True
```

The tests must also prove raw-body 413/no-store handling, exact idempotency
replay/collision, stale revisions, invalid transitions, archive/restore to
`draft`, extra-field rejection, secret/card/OTP/contact rejection, disabled
feature behavior, cross-account isolation, bounded history and that no
response/table contains Bot, bridge, provider, job, wallet/Xu, PayOS,
referral, attribution, payout, recipient or Admin CRM state.

- [ ] **Step 2: Write the failing Portal contract tests**

Add a static Portal contract that asserts:

```python
assert 'customerPage("/partner-readiness", "Partner Readiness"' in portal
assert 'layout: "partner-readiness"' in portal
assert 'renderPartnerReadiness(page, context)' in portal
assert '"/api/v1/partner-readiness/policy"' in portal
assert '"/api/v1/partner-readiness/profile"' in portal
assert '"/api/v1/partner-readiness/profile/history"' in portal
assert 'partner-readiness-write' in app_source
assert 'partner-readiness-interest' in app_source
assert 'WEBAPP_PARTNER_READINESS_ENABLED' in db_source
```

The test must isolate the Partner Readiness renderer slice and assert it has
no `localStorage`, `sessionStorage`, `telegram_id`, `referral`, `payout`,
`payment`, `provider`, `job`, `admin` or CRM-hydration path. It must assert
the submitted copy says it is not approval, matching, contact, referral,
commission, payment or payout; it must also prove the private API/page prefix
is not service-worker cacheable.

- [ ] **Step 3: Run tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_copyfast_partner_readiness.py tests/test_partner_readiness_portal_contracts.py
```

Expected: collection or assertions fail because the module, router, tables,
body/rate boundary and Portal route do not yet exist.

### Task 2: Add the additive schema and owner-scoped server API

**Files:**
- Create: `copyfast_partner_readiness.py`
- Modify: `copyfast_db.py`
- Modify: `copyfast_api.py`
- Modify: `app.py`
- Test: `tests/test_copyfast_partner_readiness.py`

- [ ] **Step 1: Add additive storage and the feature guard**

In `ensure_copyfast_schema()`, add these local Web-only tables and indexes:

```sql
CREATE TABLE IF NOT EXISTS web_partner_readiness_profiles (
    account_id TEXT PRIMARY KEY, id TEXT NOT NULL UNIQUE,
    service_focus TEXT NOT NULL, capabilities_json TEXT NOT NULL DEFAULT '[]',
    availability TEXT NOT NULL, rate_display_preference TEXT NOT NULL,
    preferred_briefs_json TEXT NOT NULL DEFAULT '[]', portfolio_summary TEXT NOT NULL DEFAULT '',
    collaboration_note TEXT NOT NULL DEFAULT '', visibility_draft TEXT NOT NULL DEFAULT 'private',
    state TEXT NOT NULL DEFAULT 'draft', revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived_at TEXT,
    FOREIGN KEY(account_id) REFERENCES web_accounts(id)
);
CREATE TABLE IF NOT EXISTS web_partner_readiness_versions (
    id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, account_id TEXT NOT NULL,
    revision INTEGER NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL,
    UNIQUE(profile_id, revision),
    FOREIGN KEY(profile_id) REFERENCES web_partner_readiness_profiles(id),
    FOREIGN KEY(account_id) REFERENCES web_accounts(id)
);
CREATE TABLE IF NOT EXISTS web_partner_readiness_events (
    id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, account_id TEXT NOT NULL,
    action TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(profile_id) REFERENCES web_partner_readiness_profiles(id),
    FOREIGN KEY(account_id) REFERENCES web_accounts(id)
);
CREATE TABLE IF NOT EXISTS web_partner_readiness_interest_submissions (
    id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, account_id TEXT NOT NULL,
    profile_revision INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'submitted',
    submitted_at TEXT NOT NULL, created_at TEXT NOT NULL,
    UNIQUE(profile_id, profile_revision),
    FOREIGN KEY(profile_id) REFERENCES web_partner_readiness_profiles(id),
    FOREIGN KEY(account_id) REFERENCES web_accounts(id)
);
```

Add owner/updated, owner/revision and owner/created indexes. Add
`partner_readiness_enabled()` reading `WEBAPP_PARTNER_READINESS_ENABLED` with
a default of `true`. Expose only its enabled flag in the existing redacted
status feature map.

- [ ] **Step 2: Implement strict models and pure helpers**

Create the router and closed vocabularies:

```python
router = APIRouter(prefix="/api/v1/partner-readiness", tags=["Web Partner Readiness"])
PROFILE_STATES = frozenset({"draft", "review", "submitted", "archived"})
AVAILABILITY = frozenset({"open", "limited", "unavailable"})
RATE_DISPLAY_PREFERENCES = frozenset({"on_request", "range_discussion", "not_shown"})
VISIBILITY_DRAFTS = frozenset({"private", "handoff_ready"})
```

Use strict Pydantic models with `extra="forbid"`, `expected_revision`, a
12–160 character idempotency key and a literal `confirm_interest: True` for
submission. Normalize text/lists and reject controls, markup, secrets, tokens,
card-like values, OTPs and contact destination patterns. Capability and brief
values must be closed, duplicate-free lists. Never accept URLs, handles,
referral codes, amounts, recipients or staff/admin fields.

Implement `_boundary(profile_persisted, interest_submitted=False)` with false
claims for Bot, Telegram, bridge, provider, job, wallet, Xu, payment, PayOS,
referral, attribution, commission, payout, public listing, matching, contact,
CRM, notification and delivery. Use only existing local auth/db/audit helpers.

- [ ] **Step 3: Implement the one-profile lifecycle**

Implement exactly these endpoints:

```python
@router.get("/policy")
@router.get("/profile")
@router.get("/profile/history")
@router.patch("/profile")
@router.post("/profile/request-review")
@router.post("/profile/interest")
@router.post("/profile/archive")
@router.post("/profile/restore")
```

`PATCH /profile` creates revision 1 only when `expected_revision == 0` and no
profile exists; it otherwise updates a draft/review profile atomically with
`WHERE account_id=? AND revision=?`. An update from `review` returns the state
to `draft`. Every success writes one immutable version, one narrow event and a
sanitized `_record_audit` action.

Use a 24-hour `web_idempotency` prefix
`web-partner-readiness:{account_id}:...`, SHA-256 normalized JSON fingerprints
and constant-time comparison. Only allow `draft -> review`, `review ->
submitted`, non-archived -> `archived`, and `archived -> draft`. Interest must
insert one version-pinned local receipt only; it must never call or enqueue
anything beyond local SQLite/audit.

- [ ] **Step 4: Mount, bound and throttle the route family**

Import/mount the router in `app.py`, add a compact
`PARTNER_READINESS_BODY_MAX_BYTES`, and extend the existing raw ASGI body guard
with the exact `/api/v1/partner-readiness/` prefix, truthful boundary and
`WEB_PARTNER_READINESS_BODY_TOO_LARGE` error. Add rate families before database
work:

```python
partner_readiness_read = request.method == "GET" and request.url.path.startswith("/api/v1/partner-readiness/")
partner_readiness_interest = request.method == "POST" and request.url.path == "/api/v1/partner-readiness/profile/interest"
partner_readiness_write = request.method in {"POST", "PATCH"} and request.url.path.startswith("/api/v1/partner-readiness/") and not partner_readiness_interest
```

Use fixed scopes and caps: reads 120/min, profile writes 30/min and explicit
interest submissions 12/min. Preserve `no-store, private` and a guarded
boundary on raw-body and rate rejections; no generic CRM/bridge/payment
exception may be added.

- [ ] **Step 5: Run backend tests to verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_copyfast_partner_readiness.py
```

Expected: signed ownership, lifecycle, idempotency, body/rate boundaries and
negative authority assertions pass.

### Task 3: Register and render the focused private workflow

**Files:**
- Modify: `copyfast_registry.py`
- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/service-worker.js`
- Test: `tests/test_partner_readiness_portal_contracts.py`

- [ ] **Step 1: Register only the independent customer feature**

Add exactly one Web-native record and leave `/referrals` unchanged:

```python
WebFeature(
    "partner_readiness", "Partner Readiness", "growth", "/partner-readiness",
    description="Hồ sơ hợp tác riêng tư có version, self-review và receipt quan tâm Web-owned; không tạo referral/link, commission, payout, Xu/PayOS, CRM, liên hệ, matching hay public listing.",
)
```

Create one `customerPage("/partner-readiness", ...)`; do not create an
`/admin/*` route, dynamic profile URL, public route or extra mobile-dock item.

- [ ] **Step 2: Add bounded hydration and real controls**

Add page-memory state for policy, profile, history and read state. In
`integration.js`, validate a complete boundary before accepting the response,
use the existing API/CSRF/request-epoch/idempotency helpers and rehydrate after
each acknowledgement. Never put profile fields or IDs into URL query,
local/session storage or the generic Partner CRM projection.

Implement real `data-portal-action` forms for save, request review, submit
interest, archive and restore. The interest form must include a confirmation
checkbox and confirmation prompt. The result copy must be exact in meaning:
“Đã ghi nhận quan tâm trong Web App; chưa có duyệt, ghép khách, liên hệ,
referral, hoa hồng, thanh toán hoặc payout.”

- [ ] **Step 3: Add narrow visual and PWA support**

Reuse existing `--portal-*` tokens, form primitives and motion system. Add only
scoped `.portal-partner-readiness*` rules needed for straight aligned form
rows, state cells and compact version/activity history. Preserve 44px mobile
controls and focus visibility. Do not add raw colors, gradients, new fonts,
marketing/portfolio grids or custom animation.

Add `/partner-readiness` and `/api/v1/partner-readiness/` to the service worker
private/no-cache exclusions; do not change public shell caching.

- [ ] **Step 4: Run Portal contract checks**

Run:

```powershell
python -m pytest -q tests/test_partner_readiness_portal_contracts.py tests/test_portal_navigation_ux_contracts.py tests/test_pwa_scope_offline_contracts.py
node --check static/portal/portal.js
node --check static/portal/integration.js
```

Expected: dynamic screen, signed hydration, private caching boundary and JS
syntax checks pass.

### Task 4: Document the authority boundary and run the focused release gate

**Files:**
- Create: `docs/migration/PARTNER_READINESS_WORKSPACE_CONTRACT.md`
- Modify: `docs/migration/README.md`
- Modify: `design-system/toan-aas-web-app/MASTER.md`
- Test: `tests/test_copyfast_partner_readiness.py`
- Test: `tests/test_partner_readiness_portal_contracts.py`

- [ ] **Step 1: Write the migration contract**

Document the route/API set, one-profile ownership model, tables, lifecycle,
idempotency/revision rules, private visibility, body/rate/PWA boundary and all
exclusions. State explicitly that this is a new Web-native preparation
workspace, not a claim of Bot freelance/affiliate runtime parity, and that
`/referrals` remains Bot-companion guarded.

- [ ] **Step 2: Link the contract and record the UI rule**

Add a concise migration README link and a Partner Readiness page note to the
design master: private dense workflow, teal/cyan shared shell, no public
portfolio grid, 44px mobile controls and transform/opacity-only motion.

- [ ] **Step 3: Run the focused release gate**

Run:

```powershell
python -m compileall -q .
python -m pytest -q tests/test_copyfast_partner_readiness.py tests/test_partner_readiness_portal_contracts.py tests/test_workspace_setup_profile.py tests/test_copyfast_channel_strategy.py tests/test_portal_navigation_ux_contracts.py tests/test_pwa_scope_offline_contracts.py
node --check static/portal/portal.js
node --check static/portal/integration.js
node --check static/portal/portal-motion.js
git diff --check
```

Expected: all selected tests pass; there are no whitespace errors, no Bot
changes, no provider/payment/job/referral/CRM behavior and no private PWA cache
extension.

- [ ] **Step 4: Commit**

```powershell
git add copyfast_partner_readiness.py copyfast_db.py copyfast_api.py copyfast_registry.py app.py static/portal/portal.js static/portal/integration.js static/portal/portal-theme.css static/portal/service-worker.js tests/test_copyfast_partner_readiness.py tests/test_partner_readiness_portal_contracts.py docs/migration/PARTNER_READINESS_WORKSPACE_CONTRACT.md docs/migration/README.md design-system/toan-aas-web-app/MASTER.md docs/superpowers/specs/2026-08-01-partner-readiness-workspace-design.md docs/superpowers/plans/2026-08-01-partner-readiness-workspace.md
git commit -m "feat: add partner readiness workspace"
```
