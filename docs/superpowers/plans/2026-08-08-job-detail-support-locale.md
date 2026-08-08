# Job Detail and Support Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make customer /jobs/{id} detail, delivery lifecycle, output-asset panel, and recovery-support form fully understandable in Vietnamese, English, and Simplified Chinese without changing canonical job, delivery, wallet, payment, or provider authority.

**Architecture:** Fixed interface copy belongs in DELIVERY_CENTER_MESSAGES. Job IDs, feature names, timestamps, Xu/refund values, canonical states, and signed delivery URLs remain server data and pass through their existing escape/ownership boundaries. A strict server route matcher supplies generic first-paint metadata only; it never puts a job ID into HTML metadata.

**Tech Stack:** Python/FastAPI shell renderer, vanilla JavaScript portal, static i18n catalogue, pytest contracts, Node syntax checks.

---

### Task 1: Define the failing contract

**Files:**

- Create: tests/test_job_detail_locale_contracts.py
- Modify: tests/test_delivery_center_record_identity_contracts.py
- Modify: tests/test_portal_safety_contracts.py

- [x] **Step 1: Assert equal vi/en/zh detail keysets.**

~~~python
DETAIL_KEYS = {
    "jobDetail.title", "jobDetail.idNote",
    "jobDetail.field.feature", "jobDetail.field.status",
    "jobDetail.field.created", "jobDetail.field.updated",
    "jobDetail.field.estimatedXu", "jobDetail.field.ledgerXu",
    "jobDetail.field.refund", "jobDetail.field.errorCategory",
    "jobDetail.field.output", "jobDetail.field.delivery",
    "jobDetail.empty.title", "jobDetail.empty.body",
    "jobDetail.protection.title", "jobDetail.protection.body",
    "jobDetail.protection.currentState", "jobDetail.protection.waitingState",
    "jobs.output.title", "jobs.output.emptySubtitle",
    "jobs.output.listSubtitle", "jobs.output.emptyTitle",
    "jobs.output.emptyBody", "jobs.output.listEmptyTitle",
    "jobs.output.listEmptyBody",
    "lifecycle.kicker", "lifecycle.title", "lifecycle.body",
    "lifecycle.job", "lifecycle.output", "lifecycle.outputBody",
    "lifecycle.delivery", "lifecycle.deliveryBody",
    "lifecycle.next", "lifecycle.nextCompleted",
    "action.download", "action.support", "action.assets", "action.track",
    "status.delivery.noMatchingAsset",
    "state.draft", "state.awaitingConfirm", "state.queued",
    "state.processing", "state.completed", "state.failed",
    "state.cancelled", "state.refunded", "state.guarded", "state.unknown",
    "recovery.title.deliveryPending", "recovery.title.problem",
    "recovery.description.deliveryPending", "recovery.description.problem",
    "recovery.subject.deliveryPending", "recovery.subject.problem",
    "recovery.reason.deliveryPending", "recovery.reason.problem",
    "recovery.reason.disabled", "recovery.field.job",
    "recovery.field.workflow", "recovery.field.status",
    "recovery.field.subject", "recovery.field.detail",
    "recovery.placeholder", "recovery.help", "recovery.submit",
}
assert DETAIL_KEYS <= catalogues["vi"]
assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
~~~

- [x] **Step 2: Assert generic, non-identifying first paint for safe opaque job IDs.**

~~~python
for locale, title in {
    "vi": "Chi tiết job · TOAN AAS",
    "en": "Job details · TOAN AAS",
    "zh": "任务详情 · TOAN AAS",
}.items():
    body = render_portal("/jobs/wnj:v1:opaque-123", interface_locale=locale).body
    assert f"<title>{title}</title>".encode() in body
    title_tag = re.search(br"<title>(.*?)</title>", body).group(1)
    description_tag = re.search(br'<meta name="description" content="([^"]*)">', body).group(1)
    assert b"opaque-123" not in title_tag + description_tag
with pytest.raises(HTTPException):
    render_portal("/jobs/%3Cscript%3E", interface_locale="en")
~~~

The bootstrap payload may retain the opaque path so the signed client can route the request; this test protects title and description metadata only.

- [x] **Step 3: Prove the new test is RED.**

Run: python -B -m pytest -q tests/test_job_detail_locale_contracts.py -p no:cacheprovider

Expected: the fixed-copy keys, safe route metadata, and detail translator calls do not yet exist.

### Task 2: Implement the route boundary and first-paint metadata

**Files:**

- Modify: copyfast_pages.py
- Test: tests/test_job_detail_locale_contracts.py

- [x] **Step 1: Add the safe opaque detail matcher alongside existing route regexes.**

~~~python
JOB_DETAIL_PATH = re.compile(r"^/jobs/[A-Za-z0-9._:-]{1,160}$")
~~~

- [x] **Step 2: Add generic locale-only title and description branches.**

~~~python
if JOB_DETAIL_PATH.fullmatch(normalized):
    return {
        "vi": "Chi tiết job · TOAN AAS",
        "en": "Job details · TOAN AAS",
        "zh": "任务详情 · TOAN AAS",
    }[locale]
~~~

Use equivalent description copy that states owner-scoped canonical detail and signed delivery. Do not interpolate normalized, the ID, account information, job status, feature name, or an output URL.

- [x] **Step 3: Allow only JOB_DETAIL_PATH in render_portal route validation.**

- [x] **Step 4: Re-run the focused test.**

Expected: first-paint cases pass; client-copy cases remain RED.

### Task 3: Localize every fixed detail and support string

**Files:**

- Modify: static/portal/portal-i18n.js
- Modify: static/portal/portal.js
- Test: tests/test_job_detail_locale_contracts.py
- Test: tests/test_delivery_center_record_identity_contracts.py
- Test: tests/test_portal_safety_contracts.py

- [x] **Step 1: Add every DETAIL_KEYS entry to the three DELIVERY_CENTER_MESSAGES objects.**

Use separate output subtitle keys:

~~~javascript
"deliveryCenter.jobs.output.emptySubtitle":
  "Only owner-scoped asset metadata can create Web delivery.",
"deliveryCenter.jobs.output.listSubtitle":
  "This list uses only signed-session asset metadata with an exact job-ID match.",
"deliveryCenter.recovery.placeholder":
  "Describe what you saw and when it happened. Do not send API keys, passwords, OTP/CVV, bills, TXID, bank-account numbers, or payment QR codes."
~~~

Provide reviewed Vietnamese and Simplified Chinese values too. Never reuse asset-list filter copy for Job Detail.

- [x] **Step 2: Replace only static literals in detail-only renderers.**

Use deliveryCenterText in renderJobOutputAssets, jobStateExplanation, jobDeliveryNextAction, jobDeliveryStage, renderJobDeliveryLifecycle, renderJobRecoverySupport, and renderJobDetail.

- [x] **Step 3: Preserve every dynamic-data boundary.**

Keep record ID, job feature, dates, Xu/refund values, error category, exact asset matching, signed download path, form action, capability/CSRF, safeText, and encodeURIComponent unchanged. The localized recovery subject may interpolate the already validated job ID but must still pass through safeText at its existing input boundary.

- [x] **Step 4: Verify GREEN with focused contracts.**

Run: python -B -m pytest -q tests/test_job_detail_locale_contracts.py tests/test_delivery_center_locale_contracts.py tests/test_delivery_navigation_app_ux_contracts.py tests/test_delivery_center_record_identity_contracts.py tests/test_portal_safety_contracts.py -p no:cacheprovider

Expected: all pass; no translated UI can create a file, infer ownership, or create a payment/provider action.

### Task 4: Package and verify one clean Web App PR

**Files:**

- Modify only if static audit changes them: docs/migration/README.md, reports/migration/preflight.json, reports/migration/web_inventory.json

- [x] **Step 1: Run final syntax and diff gates.**

~~~powershell
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
python -B -m compileall -q copyfast_pages.py
git diff --check
~~~

Expected: exit 0.

- [ ] **Step 2: Commit source.**

~~~powershell
git commit -m "Localize job detail and support"
~~~

- [ ] **Step 3: Run static-only migration audit for the full source SHA, commit only evidence files, then invoke --verify-web-evidence with the full final SHA.**

Expected: every audit reports ok: true; the audit reads source text only and never imports or calls Bot, PayOS, providers, or webhooks.

- [ ] **Step 4: Capture the committed source revision and regenerate only static migration evidence.**

~~~powershell
$sourceSha = git rev-parse HEAD
python -B scripts/migration/audit_bot_to_web.py `
  --bot-root "D:\TOANAAS\bot telegram" `
  --web-root . `
  --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 `
  --web-revision $sourceSha `
  --report-dir reports/migration `
  --docs-dir docs/migration
git status --short
~~~

Expected: the audit exits 0 and only its generated migration evidence changes. It parses source text and local Git metadata; it does not import, run, or change Bot source.

- [ ] **Step 5: Commit generated evidence only when it changed.**

~~~powershell
git add docs/migration/README.md reports/migration/preflight.json reports/migration/web_inventory.json
git commit -m "Refresh migration evidence for job detail locale"
~~~

Expected: this commit contains no portal source, Bot source, provider configuration, secrets, or environment file. If `git status --short` shows no evidence change, skip the commit and record that evidence was already current.

- [ ] **Step 6: Verify evidence against the final Web revision.**

~~~powershell
$finalSha = git rev-parse HEAD
python -B scripts/migration/audit_bot_to_web.py `
  --web-root . `
  --web-revision $finalSha `
  --report-dir reports/migration `
  --docs-dir docs/migration `
  --verify-web-evidence
~~~

Expected: exit 0. The source revision recorded by the audit is an ancestor of `$finalSha`, fingerprints match current eligible Web source, and no migration evidence was edited after verification.

- [ ] **Step 7: Push one focused PR without deployment.**

~~~powershell
git push -u origin feature/p0-webapp-job-detail-locale
gh pr create --base main --head feature/p0-webapp-job-detail-locale --title "Localize job detail and support" --body "## Scope`n- localize /jobs/{id}, delivery lifecycle, output assets and recovery support in vi/en/zh`n- preserve exact asset, ownership and signed delivery guards`n- no Bot, bridge, PayOS, wallet, provider or deployment change`n`n## Verification`n- focused locale and safety contracts`n- Node syntax checks, Python compileall, diff check`n- static migration evidence verification"
gh pr checks --watch
~~~

Expected: the PR contains only the source, focused contract, and any generated migration evidence from this slice. Do not deploy Railway. Merge only after all required checks are green and the final PR diff still matches this plan.
