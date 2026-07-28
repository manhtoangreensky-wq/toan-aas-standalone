# Migration Evidence Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore consistency between the current frozen-baseline parity report and the checked-in migration test-evidence summary, then make the existing consistency contract part of the bounded CI quality gate.

**Architecture:** `reports/migration/parity_gap.json` remains the generated source for the current static-audit metric. `docs/migration/TEST_EVIDENCE.md` records the same human-readable current metric, while the existing audit contract asserts exact agreement. This hotfix updates only that stale documentation value and runs the existing contract in CI; it adds no Bot, bridge, provider, payment, wallet, webhook, browser, or runtime behavior.

**Tech Stack:** Python/pytest static-audit contract, checked-in Markdown/JSON evidence, GitHub Actions YAML.

---

## Scope and non-goals

- The frozen Bot baseline remains `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
- The correct current value is read from `reports/migration/parity_gap.json`, not recomputed or invented: `mapping_coverage_percent = 79.35`.
- Do not edit `reports/migration/*.json`, the Bot, bridge, provider, PayOS, wallet/Xu, webhook, video, capability/skill, or LocalVideoStudio26-owned files.
- Do not make a LIVE, deployment, or runtime-equivalence claim.

## File structure

- Modify: `docs/migration/TEST_EVIDENCE.md:15`
  - Correct the stale current static-audit metric from `78.68%` to the report-backed `79.35%`.
- Modify: `.github/workflows/webapp-quality.yml`
  - Include the pre-existing `test_current_migration_evidence_records_frozen_baseline_and_historical_bridge` in the bounded quality suite so an evidence/report mismatch blocks a PR.
- Create: `docs/superpowers/plans/2026-07-29-migration-evidence-consistency.md`
  - Preserve this exact hotfix contract and verification steps.

### Task 1: Prove the stale evidence regression (existing red contract)

**Files:**
- Test: `tests/test_migration_audit.py:303-340`
- Read: `reports/migration/parity_gap.json`
- Read: `docs/migration/TEST_EVIDENCE.md:15`

- [ ] **Step 1: Run the existing consistency test before editing the evidence.**

```powershell
python -m pytest -q tests/test_migration_audit.py::test_current_migration_evidence_records_frozen_baseline_and_historical_bridge
```

Expected: fail because the checked-in report says `79.35%` while the current-evidence row says `78.68%`.

- [ ] **Step 2: Confirm the source of truth is the current generated report.**

```powershell
python -c "import json; print(json.load(open('reports/migration/parity_gap.json', encoding='utf-8'))['mapping_coverage_percent'])"
```

Expected: `79.35`.

### Task 2: Apply the minimal evidence and CI-gate fix

**Files:**
- Modify: `docs/migration/TEST_EVIDENCE.md:15`
- Modify: `.github/workflows/webapp-quality.yml:60-100`

- [ ] **Step 1: Update only the stale metric in the current static-audit table row.**

Replace the text fragment:

```text
78.68% safe disposition coverage
```

with:

```text
79.35% safe disposition coverage
```

- [ ] **Step 2: Add the existing consistency contract to the bounded quality command.**

Insert this exact argument beside the existing migration-audit tests:

```text
tests/test_migration_audit.py::test_current_migration_evidence_records_frozen_baseline_and_historical_bridge
```

It must run after dependency installation and before the whitespace check; no new test implementation is needed because the pre-existing test is the regression contract.

### Task 3: Verify the green contract and narrow diff

**Files:**
- Verify: `docs/migration/TEST_EVIDENCE.md`
- Verify: `.github/workflows/webapp-quality.yml`
- Verify: `tests/test_migration_audit.py`

- [ ] **Step 1: Run the exact consistency contract after the documentation correction.**

```powershell
python -m pytest -q tests/test_migration_audit.py::test_current_migration_evidence_records_frozen_baseline_and_historical_bridge
```

Expected: `1 passed`.

- [ ] **Step 2: Run the focused migration audit file.**

```powershell
python -m pytest -q tests/test_migration_audit.py
```

Expected: all tests pass; no provider, Telegram, PayOS, or Bot runtime is contacted.

- [ ] **Step 3: Validate static build and exact scope.**

```powershell
python -m compileall -q .
git diff --check
git status --short --untracked-files=all
git diff --name-only
```

Expected: no whitespace errors, and the working tree lists only the plan, `TEST_EVIDENCE.md`, and quality workflow before commit. After staging those exact files, inspect `git diff --cached --check` and `git diff --cached --name-only` before committing.

### Task 4: Independent review and merge

- [ ] **Step 1: Request a spec review.**

Verify the report-backed metric is exact, no generated report is altered, the baseline/guard language remains unchanged, and the CI command invokes the exact existing test.

- [ ] **Step 2: Request a code-quality/security review.**

Verify YAML placement, CI command validity, test reproducibility, diff scope, and that no runtime/authority behavior changes.

- [ ] **Step 3: Commit, push, and merge only after the Web App quality gate is green.**

```powershell
git add docs/migration/TEST_EVIDENCE.md .github/workflows/webapp-quality.yml docs/superpowers/plans/2026-07-29-migration-evidence-consistency.md
git commit -m "Keep migration evidence metrics consistent"
git push -u origin feature/p0-webapp-copyfast162-migration-evidence-consistency
```

## Plan self-review

- The plan covers the verified root cause: one stale metric plus the absent CI invocation of its existing consistency test.
- It does not recompute or manually alter a JSON audit report and does not broaden product scope.
- The existing regression test is explicitly run red first, then green after the smallest correction.
- The final scope is limited to a documentation artifact, the bounded CI test list, and this plan.
