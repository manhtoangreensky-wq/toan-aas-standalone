# Image Operation Export to Content Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit Web-only continuation from a verified Image Operation PNG Asset Vault export to a new, owner-scoped Content Handoff draft.

**Architecture:** A second opt-in portal action shares the existing `POST /api/v1/image-operations/{operation_id}/export-to-asset-vault` fence. The client refreshes authoritative operation/Vault state, then navigates only from an active completed receipt. The existing Content Handoff prefill helper and server ownership comparator remain authoritative.

**Tech Stack:** Vanilla portal JavaScript, existing FastAPI Image Operations and Content Handoff contracts, pytest static portal contracts, Node syntax checks.

---

### Task 1: Add RED portal contracts

**Files:**

- Modify: `tests/test_image_operation_asset_export_portal_contracts.py`
- Read: `tests/test_document_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Require a gated second control**

Add assertions for both exact action attributes, the `content-handoff-create` capability, and the Vietnamese continuation label. The control must be absent whenever the ordinary export capability or Content Handoff capability is false.

- [ ] **Step 2: Require active-only navigation**

Capture the joint action handler. Require the existing opaque Image Operation export path, `contentHandoffDraftPath(asset.id)`, an active-state check, and `window.location.assign(handoffPath)`. Reject a Content Handoff write path plus provider, wallet, payment, PayOS, Bot, or Telegram literals in the new action branch.

- [ ] **Step 3: Run RED**

Run `python -B -m pytest -p no:cacheprovider -q tests/test_image_operation_asset_export_portal_contracts.py`. The new assertions must fail because the continuation action is not yet present.

### Task 2: Implement the smallest continuation

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Test: `tests/test_image_operation_asset_export_portal_contracts.py`

- [ ] **Step 1: Render the second explicit action**

In `imageOperationAssetExportControl`, preserve the current export button. Render a second button only when `content-handoff-create` is true. It carries only the current Image Operation UUID, route, and a confirmation message.

- [ ] **Step 2: Share the export fence safely**

Handle both action names in the existing Image Operation export branch. Use the same opaque request, idempotency scope, receipt validation, and refresh function. For the continuation action, require an `active` receipt, derive `contentHandoffDraftPath(asset.id)`, and call `window.location.assign(handoffPath)`. Do not call a Content Handoff endpoint or create a record.

- [ ] **Step 3: Extend portal event field extraction**

Add `fields.__imageOperationId` for both exact Image Operation export action names. Preserve the generic pagination field behavior.

- [ ] **Step 4: Run GREEN**

Run these commands: `python -B -m pytest -p no:cacheprovider -q tests/test_image_operation_asset_export_portal_contracts.py tests/test_document_operation_asset_export_portal_contracts.py tests/test_copyfast_content_handoff.py`; `node --check static/portal/portal.js`; `node --check static/portal/integration.js`; and `git diff --check`.

### Task 3: Review, evidence, and integration

**Files:**

- Create: `docs/superpowers/specs/2026-08-11-image-operation-export-content-handoff-design.md`
- Create: `docs/superpowers/plans/2026-08-11-image-operation-export-content-handoff.md`

- [ ] **Step 1: Review protected domains**

Confirm no diff in `bot.py`, `copyfast_image_operations.py`, `copyfast_content_handoff.py`, `copyfast_assets.py`, `copyfast_db.py`, `app.py`, payment/wallet/provider files, service worker, or environment files.

- [ ] **Step 2: Request independent review**

Review the full diff for active-only receipt navigation, opaque-ID-only URL, no auto-create, and no forbidden provider/payment/Bot call.

- [ ] **Step 3: Commit and push after fresh verification**

Stage only the two portal files, the focused test, and the design/plan files. Commit as `Connect image exports to Content Handoff drafts`, push `feature/p0-webapp-image-operation-content-handoff`, wait for CI, then create/merge a PR only after the quality gate is green. Do not deploy Railway, change environment values, call a provider, modify the Bot, or mutate wallet/payment state.
