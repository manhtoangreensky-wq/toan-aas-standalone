# Migration Audit Rebaseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the committed migration evidence from the frozen Bot baseline and current Web App main so parity planning uses current, reproducible facts, while fixing the audit generator so it does not omit the existing Web-native Finance Planning module.

**Architecture:** The existing static audit remains the only generator. It reads the frozen Bot source and the current Web worktree without importing either runtime, then writes the complete Markdown and JSON evidence bundle into the versioned migration directories. The generator gains a small documentation-only Finance Planning section for the existing Web-local module; it introduces no browser route, provider call, Bot bridge, wallet/PayOS logic, or runtime-equivalence claim.

**Tech Stack:** Python 3 static audit, generated JSON/Markdown, pytest audit contracts, Git diff validation.

---

### Task 1: Record the reproducible generation contract

**Files:**
- Create: `docs/superpowers/plans/2026-07-28-audit-rebaseline-design.md`
- Read: `scripts/migration/audit_bot_to_web.py`
- Read: `tests/test_migration_audit.py`

- [x] Verify the clean worktree starts at `origin/main` commit `e88ace1` and the Bot baseline is `b29d0d474974075f4cba963d2c510f49d2d1b3e4`.
- [x] Verify the audit supports separate output directories, so the preliminary inventory does not alter the source-of-truth checkout.
- [x] Exclude configured output roots and the standard `docs/migration` / `reports/migration` evidence directories from a Web inventory, and label a materialized Bot snapshot as `git-baseline:<sha>` so output location does not alter a second static audit.
- [x] Run the static audit once into `C:\\tmp\\toanaas-current-audit-20260728` and record that it succeeds with 773 Bot commands and 664 Web routes.

### Task 2: Preserve Finance Planning in the generated authority maps

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Modify: `tests/test_migration_audit.py`

- [x] Add a focused generated-document contract asserting that the state map names the Finance Planning table family, the environment map names `WEBAPP_FINANCE_PLANNING_ENABLED`, and the admin map names the signed `/admin/finance/planning` boundary.
- [x] Run the focused test and confirm it fails before the renderer change because the regenerated maps omit that evidence.
- [x] Add documentation-only renderer content for the existing signed Web-local Finance Planning module. It states that Bot finance state, wallet/Xu, PayOS, provider state and Bot-admin identity remain outside the module.
- [x] Run the focused test again and confirm it passes.

### Task 3: Regenerate the committed evidence bundle

**Files:**
- Modify: `reports/migration/preflight.json`
- Modify: `reports/migration/bot_inventory.json`
- Modify: `reports/migration/web_inventory.json`
- Modify: `reports/migration/parity_gap.json`
- Modify: `docs/migration/*.md` emitted by `scripts/migration/audit_bot_to_web.py`

- [x] Run exactly:

```powershell
python scripts/migration/audit_bot_to_web.py `
  --bot-root "C:\\Users\\toann\\Documents\\Codex\\2026-05-31\\files-mentioned-by-the-user-bot\\toanaas-hotfix-28ff87f" `
  --web-root . `
  --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 `
  --report-dir reports/migration `
  --docs-dir docs/migration
```

- [x] Confirm the regenerated `preflight.json` records the exact frozen SHA and masks secrets.
- [x] Confirm `parity_gap.json` reports the current 664-route inventory and does not increase runtime-equivalence above its static `NOT_STATICALLY_VERIFIABLE` boundary.
- [x] Do not edit any generated file by hand or stage a source/runtime/provider/ledger/webhook change.

### Task 4: Verify generated evidence and prepare the focused PR

**Files:**
- Test: `tests/test_migration_audit.py`
- Verify: `reports/migration/*.json`
- Verify: `docs/migration/*.md`

- [x] Parse all generated JSON reports with Python-compatible JSON parsing; each is valid JSON.
- [x] Run `python -m py_compile scripts/migration/audit_bot_to_web.py`.
- [x] Run `python -m pytest -q tests/test_migration_audit.py -k 'static_audit_preserves_finance_planning_authority_and_redacts_secret_literals or current_migration_evidence_records_frozen_baseline_and_historical_bridge or audio_hub' -p no:cacheprovider`; the explicitly named Finance Planning authority, current-evidence consistency and Audio Hub boundary contracts pass.
- [x] Run `git diff --check`, inspect the diff and require it contains only the audit generator, focused test, generated migration docs/reports and this plan.
- [x] Reclassify `TELEGRAM_WEB_CONNECTION.md` and `TEST_EVIDENCE.md` so their prior bridge checkout/metrics cannot contradict the current frozen-baseline evidence.
- [ ] Commit only after spec and code-quality review approve the generator, focused test and generated-evidence diff.
