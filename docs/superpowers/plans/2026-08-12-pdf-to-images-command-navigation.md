# PDF to Images Command Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify the frozen Bot `/pdf_to_images` command as a fresh signed Web navigation to the existing private `/documents/pdf-to-images` page without replaying a Bot document workflow or enabling the renderer.

**Architecture:** The finite command catalog in `scripts/migration/audit_bot_to_web.py` decides only whether a Bot command can open a fresh standalone Web page. The existing PDF-to-images surface owns its independent Asset Vault selection, feature flag, CSRF/idempotency, bounded renderer and verified private delivery; no change is made to that runtime.

**Tech Stack:** Python 3 static audit, pytest, existing JavaScript portal route contracts, generated migration JSON/Markdown evidence.

---

### Task 1: Establish failing navigation and state-boundary contracts

**Files:**

- Modify: `tests/test_document_operation_portal_contracts.py`
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the desired customer-page assertion**

Add this command/page pair to the existing reviewed navigation test:

```python
"/pdf_to_images": "/documents/pdf-to-images",
```

Add this expected audit record:

```python
"pdf_to_images": (
    "/documents/pdf-to-images",
    "documents_pdf_to_images",
    "documents_pdf_to_images",
    "pdf_to_images",
),
```

Remove only `pdf_to_images` from the negative mapping catalog. Add literal assertions proving that the contract retains the no-Telegram-ID, no-`USER_PENDING`, no-file/order/page-range/confirmation/charge/output replay boundary and only points at the page, never `/api/v1/document-operations/pdf-to-images`.

- [ ] **Step 2: Run RED**

Run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_document_operation_portal_contracts.py::test_document_command_navigation_only_opens_existing_private_web_surfaces tests/test_migration_audit.py::test_static_audit_maps_only_reviewed_document_commands_to_fresh_web_navigation
```

Expected: the contract lacks the page row and the audit returns the preexisting `COPIED_GUARDED` mapping because `pdf_to_images` is not in `DOCUMENT_FRESH_WEB_NAVIGATION_COMMANDS`.

### Task 2: Add the minimal fresh-Web catalog entry

**Files:**

- Modify: `scripts/migration/audit_bot_to_web.py`
- Modify: `docs/migration/DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md`

- [ ] **Step 1: Add the exact static catalog entry**

Add this entry beside the other document operations:

```python
"pdf_to_images": {
    "target": "/documents/pdf-to-images",
    "capability_key": "documents_pdf_to_images",
    "feature_key": "documents_pdf_to_images",
    "surface": "pdf_to_images",
},
```

Do not modify the existing `COMMAND_ROUTE_OVERRIDES`, portal JavaScript, document operation API, renderer, feature flag, storage, Bot source, Core Bridge, provider, wallet/Xu, PayOS, webhook or Railway code.

- [ ] **Step 2: Update the reviewed contract catalog**

Add `/pdf_to_images` with `/documents/pdf-to-images`. State that the signed customer starts with a fresh owner-scoped Asset Vault PDF and that the existing standalone page decides whether its renderer is enabled, accepts input, runs and delivers output. Remove it from the explicit-exclusions list while retaining the `/translate_file` and `docflow|*` boundaries.

- [ ] **Step 3: Run GREEN**

Run the Task 1 command again. Expected: both tests pass, with `NAVIGATION_ONLY`, the exact metadata and no raw API target.

### Task 3: Review, evidence and protected comparisons

**Files:**

- Modify only if generated: `docs/migration/README.md`, `docs/migration/FEATURE_PARITY_MATRIX.md`, `docs/migration/parity-matrix.md`, `docs/migration/TEST_EVIDENCE.md`, `reports/migration/preflight.json`, `reports/migration/parity_gap.json`

- [ ] **Step 1: Commit code and contract changes**

Commit the Task 1–2 files with:

```text
Map PDF to images command to fresh Web navigation
```

- [ ] **Step 2: Regenerate static-only migration evidence**

Run `scripts/migration/audit_bot_to_web.py` using only Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4`, the code-commit SHA, and the configured read-only Bot checkout. Inspect the evidence diff for `/pdf_to_images` metadata and changed aggregate counts; do not run a Bot, PDF renderer, provider or payment flow.

- [ ] **Step 3: Verify and commit evidence separately**

Run:

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_document_operation_portal_contracts.py tests/test_migration_audit.py tests/test_docflow_callback_disposition.py
node --check static/portal/portal.js
node --check static/portal/integration.js
git diff --check
```

Use the audit's `--verify-web-evidence` mode at the final HEAD. Confirm the diff omits Bot source, PDF renderer/API/flag, Core Bridge, provider, wallet/Xu, PayOS/payment, webhooks, deployment/ENV and docflow logic. Commit generated evidence with:

```text
Refresh migration evidence for PDF to images navigation
```
