# Document Export to Content Handoff Prefill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit Web-only continuation from a verified Document
Operation Asset Vault export to a new, owner-scoped Content Handoff draft.

**Architecture:** The portal adds a separate opt-in action which reuses the
existing fenced export POST.  It redirects only from a `completed` and `active`
receipt.  The existing Content Handoff renderer consumes the opaque `asset_id`
only when it matches its active owner-scoped Vault projection; the existing
server write remains the canonical ownership gate.

**Tech Stack:** Vanilla portal JavaScript, existing FastAPI ownership contract,
pytest static/Node portal contracts.

---

### Task 1: Prove the new portal boundary in RED

**Files:**

- Modify: `tests/test_document_operation_asset_export_portal_contracts.py`
- Read: `tests/test_copyfast_content_handoff.py`

- [ ] **Step 1: Add an opt-in rendered-card test**

```python
assert 'data-portal-action="document-operation-export-to-content-handoff"' in markup
assert 'Lưu & chuẩn bị bàn giao' in markup
```

Render the same completed PDF fixture twice: once with only the export
capability, where the continuation control is absent, and once with both
`document-operation-export-to-asset-vault` and `content-handoff-create`, where
the control is present.

- [ ] **Step 2: Add a navigation receipt test**

```python
assert sandbox.contentHandoffDraftPath(active_id) == "/content/handoffs/new?asset_id=" + active_id
assert sandbox.contentHandoffDraftPath("not-a-uuid") == ""
```

Assert the new action slice contains the existing export path and idempotency
header but no `/content-handoffs/records` write, and branches away from an
`archived` or `unavailable` receipt before navigation.

- [ ] **Step 3: Add a query-prefill eligibility test**

Execute the small portal helper with a valid active owner asset, an absent UUID,
an archived asset, and an edited-record value.  Only the new-record plus active
asset case may return the UUID.

- [ ] **Step 4: Run the test and observe RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests\test_document_operation_asset_export_portal_contracts.py
```

Expected: the new contract fails because the continuation action and prefill
helper do not exist; existing export assertions remain green.

### Task 2: Implement the smallest truthful continuation

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Test: `tests/test_document_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Render the separate opt-in continuation control**

Keep `document-operation-export-to-asset-vault` intact.  Next to it, render
`document-operation-export-to-content-handoff` only when both capabilities are
true.  It carries only the existing operation UUID, route, and confirmation
text.

- [ ] **Step 2: Share the existing fenced export action safely**

Handle both action names in one export branch.  Keep route/capability,
idempotency, receipt, pending, guarded, refresh, and finalization behavior.
For the continuation action, require `asset.state === "active"`, derive a
navigation path from a valid receipt ID, then call `window.location.assign`.
Do not call a Content Handoff endpoint or fabricate a record.

- [ ] **Step 3: Resolve query prefill against active Vault state**

Add a small `contentHandoffDraftAssetId(context, record)` helper in
`portal.js`.  It returns an ID only for a new record, a valid query UUID, and a
matching `vaultItems(context)` entry.  Use it as the default selector value;
record references continue to take priority for updates.

- [ ] **Step 4: Run GREEN verification**

Run:

```powershell
python -B -m pytest -p no:cacheprovider -q tests\test_document_operation_asset_export_portal_contracts.py tests\test_copyfast_content_handoff.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all selected tests pass, JavaScript parses, and the diff remains
portal/test/spec/plan only.

### Task 3: Review and deliver the isolated branch

**Files:**

- Modify: only the files named in Tasks 1-2 and this plan/spec

- [ ] **Step 1: Review the complete diff against the protected boundary**

Confirm `copyfast_assets.py`, `copyfast_document_operations.py`,
`copyfast_content_handoff.py`, `copyfast_db.py`, `app.py`, payment/wallet,
provider, Bot, ENV, and PWA cache files have no diff.

- [ ] **Step 2: Request independent spec and quality reviews**

Reviewers must verify explicit intent, active-only receipt navigation, query
sanitization, no auto-create/write, server-owner comparator preservation, and
absence of forbidden subsystem calls.

- [ ] **Step 3: Commit and open one PR after fresh verification**

```powershell
git add static\portal\portal.js static\portal\integration.js tests\test_document_operation_asset_export_portal_contracts.py docs\superpowers\specs\2026-08-11-document-export-content-handoff-prefill-design.md docs\superpowers\plans\2026-08-11-document-export-content-handoff-prefill.md
git commit -m "Connect document exports to Content Handoff drafts"
git push -u origin feature/p0-webapp-content-handoff-asset-export-followup
gh pr create --base main --title "Connect document exports to Content Handoff drafts"
```

No Railway deployment, ENV change, provider call, Bot edit, payment/wallet
mutation, or `LIVE PASS` claim belongs to this plan.
