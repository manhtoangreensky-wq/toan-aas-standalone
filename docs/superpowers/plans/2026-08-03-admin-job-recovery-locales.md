# Admin Job Recovery Guide Locale Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the existing canonical-admin Job-Lock Recovery Safety Guide in VI/EN/ZH without changing its read-only, no-control-plane boundary.

**Architecture:** The existing static Portal guide receives one scoped locale catalogue and a narrow renderer helper. `copyfast_pages.py` supplies matching locale-aware document titles for the server first paint. No API, bridge, route authorization, browser action, storage or runtime integration changes.

**Tech Stack:** FastAPI/Python shell rendering, static JavaScript Portal renderer, static locale catalogue, pytest, Node syntax checks.

---

### Task 1: Write the red locale contract

**Files:**

- Create: `tests/test_admin_job_recovery_guide_locale_contracts.py`
- Inspect: `tests/test_job_lock_recovery_guide_portal_contracts.py`
- Inspect: `tests/test_admin_postback_readiness_locale_contracts.py`

- [ ] **Step 1: Write the failing test**

Create a focused static contract that enumerates the 39 `adminGeneric.jobRecoveryGuide.*` suffixes and asserts each appears exactly three times in `static/portal/portal-i18n.js`. Assert the future renderer shape:

```python
assert "function adminJobRecoveryGuideText(key, fallback, params)" in portal
assert 'const text = (key, fallback, params) => adminJobRecoveryGuideText(key, fallback, params);' in renderer
assert '"Job-Lock Recovery Safety Guide": "adminGeneric.jobRecoveryGuide.route.title"' in portal
assert 'if (path === "/admin/job-recovery-guide") return adminJobRecoveryGuideText("route.title", fallback);' in page_titles
assert 'if (path === "/admin/job-recovery-guide") return adminJobRecoveryGuideText("route.description", fallback);' in page_descriptions
```

The same test must assert the three exact first-paint titles, the `serverAuthorizesAdminRoute(context, "/admin/jobs")` check, `renderHero(page, context)`, `badge("read_only")`, localized `renderNotes`, exact Vietnamese boundary fallbacks, and the existing forbidden control-plane tokens.

- [ ] **Step 2: Run the test to verify it fails for the intended reason**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_job_recovery_guide_locale_contracts.py
```

Expected: failure because the `adminJobRecoveryGuide` catalogue/helper/title mappings do not exist; no import or environment failure.

### Task 2: Add the minimal locale implementation

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Modify: `copyfast_pages.py`
- Test: `tests/test_admin_job_recovery_guide_locale_contracts.py`
- Test: `tests/test_job_lock_recovery_guide_portal_contracts.py`

- [ ] **Step 1: Add the reviewed 39-key catalogue**

Insert the same `adminGeneric.jobRecoveryGuide.*` key set into each `vi`, `en`, and `zh` dictionary. The Vietnamese values use the current guide copy; English and Chinese state the same triage/escalation boundaries without promising repair or delivery.

- [ ] **Step 2: Add the scoped text helper and title maps**

Next to the existing scoped admin helpers, add:

```javascript
function adminJobRecoveryGuideText(key, fallback, params) { return adminGenericText("jobRecoveryGuide." + key, fallback, params); }
```

Map only the exact `/admin/job-recovery-guide` path in `localizedPageTitle` and `localizedPageDescription`. Map only the exact existing static page title in the static-title catalogue. Add only this path to `_PORTAL_SHELL_TITLES`:

```python
"/admin/job-recovery-guide": {
    "vi": "Hướng dẫn xử lý Job-Lock · TOAN AAS",
    "en": "Job-Lock Recovery Guide · TOAN AAS",
    "zh": "任务锁恢复指南 · TOAN AAS",
},
```

- [ ] **Step 3: Localize the existing renderer without changing behavior**

At the start of `renderAdminJobRecoveryGuide`, create the `text` wrapper. Convert only fixed copy to calls such as:

```javascript
{ icon: ICONS.jobs, title: text("checkpoint.triage.title", "Dừng ở triage"), text: text("checkpoint.triage.body", "Nhận diện triệu chứng theo quy trình nội bộ, nhưng không suy đoán job nào bị kẹt hoặc đã hoàn tất từ màn hình này.") }
```

Keep `jobsLink`, existing `serverAuthorizesAdminRoute`, `safeText`, icons, canonical href, badges, guide layout and all forbidden-token boundaries unchanged. Supply localized notes and optional note labels with:

```javascript
${renderNotes({ ...page, notes: localizedNotes }, noteLabels)}
```

- [ ] **Step 4: Run focused tests and syntax checks**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_job_recovery_guide_locale_contracts.py tests/test_job_lock_recovery_guide_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
git diff --check
```

Expected: all tests pass, both JavaScript files parse, and no whitespace error is emitted.

### Task 3: Refresh evidence and complete review gates

**Files:**

- Modify only when generated content changes: `docs/migration/README.md`, `reports/migration/preflight.json`, `reports/migration/web_inventory.json`
- Inspect: `scripts/migration/audit_bot_to_web.py`

- [ ] **Step 1: Commit the source change**

Stage the two design documents, the new contract, `portal-i18n.js`, `portal.js`, and `copyfast_pages.py`. Commit with a narrow message:

```powershell
git add docs/superpowers/specs/2026-08-03-admin-job-recovery-locales-design.md docs/superpowers/plans/2026-08-03-admin-job-recovery-locales.md tests/test_admin_job_recovery_guide_locale_contracts.py static/portal/portal-i18n.js static/portal/portal.js copyfast_pages.py
git commit -m "Localize admin Job Recovery guide"
```

- [ ] **Step 2: Regenerate static migration evidence from the frozen Bot baseline**

Run the audit with the source commit SHA and the fixed Bot baseline SHA `b29d0d474974075f4cba963d2c510f49d2d1b3e4`. Stage only the three allowed evidence files if they changed; do not stage regenerated migration documents with unrelated line-ending or timestamp noise.

- [ ] **Step 3: Verify final evidence and bounded regression gates**

Run `audit_bot_to_web.py --verify-web-evidence`, `compileall`, focused Portal syntax checks, `git diff --check`, and the established bounded critical Web App pytest suite. Review the final diff for scope, secret exposure, and any accidental control-plane addition before PR creation.

- [ ] **Step 4: Create the sequential PR and merge after CI green**

Push only `feature/p0-webapp-admin-job-recovery-locales`, open a PR titled `Localize admin Job Recovery guide`, wait for the repository CI, and merge only after it is green. Preserve the worktree for any post-merge follow-up.
