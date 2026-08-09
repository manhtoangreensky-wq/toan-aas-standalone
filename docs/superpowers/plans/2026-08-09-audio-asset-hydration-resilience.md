# Audio Asset Hydration Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep a valid owner-scoped Audio Asset Vault source usable when the independent audio-operation history request fails, while exposing the history failure truthfully.

**Architecture:** Split source-reference and operation-history read state in the existing Portal integration store. Fetch both endpoints independently with `Promise.allSettled`; a source success preserves the typed selector and write guard, while a history failure only disables history-dependent actions and offers retry. No provider, Bot, wallet, PayOS or output semantics change.

**Tech Stack:** Vanilla JavaScript Portal (`static/portal/integration.js`, `portal.js`, `portal.css`), Python static contract tests with pytest, Markdown migration contract.

---

### Task 1: Establish the isolated baseline

**Files:**
- Read: `D:/TOANAAS/TOAN_AAS_WEB_APP/GitHub/static/portal/integration.js`
- Read: `D:/TOANAAS/TOAN_AAS_WEB_APP/GitHub/tests/test_audio_asset_operations_portal_contracts.py`

- [x] **Step 1: Verify the worktree starts at `3d97ce74712b1257b5cc3387d9b13d4e36a224e1` and is clean.**
- [x] **Step 2: Run `pytest -q tests/test_audio_asset_operations_portal_contracts.py` and record the baseline result.**

### Task 2: Add the failing regression contract

**Files:**
- Modify: `tests/test_audio_asset_operations_portal_contracts.py`

- [x] **Step 1: Add `test_history_failure_does_not_hide_a_ready_audio_source` asserting `Promise.allSettled`, independent `audioAssetReferenceReadState`/`audioAssetOperationsReadState`, fulfilled-outcome branches and Portal source/history guards.**
- [x] **Step 2: Run `pytest -q tests/test_audio_asset_operations_portal_contracts.py::test_history_failure_does_not_hide_a_ready_audio_source`; it failed for the expected reason because the current hydration used `Promise.all`.**

### Task 3: Implement the minimal split-state hydration

**Files:**
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal.js`

- [x] **Step 1: Add source/history read-state defaults and preserve the existing typed projection when only history fails.**
- [x] **Step 2: Replace the coupled `Promise.all` with `Promise.allSettled`, keeping epoch/session/path fencing and fail-closed source behavior.**
- [x] **Step 3: Keep source selection/write controls enabled only when source metadata is ready; keep history retry/detail controls disabled until history is ready.**
- [x] **Step 4: Run the regression test and the focused audio contract suite; both must pass.**

### Task 4: Document and verify the boundary

**Files:**
- Modify: `docs/migration/AUDIO_ASSET_OPERATIONS_CONTRACT.md`
- Modify: `tests/test_audio_asset_operations_portal_contracts.py`

- [x] **Step 1: Document independent source/history read states and the failed-history retry behavior.**
- [x] **Step 2: Run `node --check static/portal/integration.js`, `node --check static/portal/portal.js`, `git diff --check`, and the focused Python tests.**
- [x] **Step 3: Review the complete diff for protected-scope violations, secrets, provider calls and wallet/payment mutations.**
- [ ] **Step 4: Commit with `Fix audio asset history hydration resilience`.**

### Task 5: Integrate

- [ ] **Step 1: Push `feature/p0-webapp-audio-asset-hydration-resilience` and open one non-draft PR against `main`.**
- [ ] **Step 2: Wait for CI, merge the PR, and verify `main` is clean and the Railway revision matches the merge SHA.**
