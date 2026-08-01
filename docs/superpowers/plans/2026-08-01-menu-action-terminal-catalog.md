# Menu Action Terminal Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every currently observed `menu|...` callback and template with a truthful terminal disposition, while preserving only the existing, independently reviewed Web navigation allow-lists.

**Architecture:** The static migration auditor owns a private, finite catalog of frozen-baseline Bot-only menu actions and templates. It returns `TELEGRAM_ONLY` evidence before any generic route heuristics can run for those exact records; new/case-variant menu values remain fail-closed source-review evidence so Bot drift stays visible. Web-facing registries continue to expose only capability keys and never raw Bot callback strings. Generated migration documentation records the terminal boundary without claiming a Browser workflow, provider call, payment, job, output, or delivery.

**Tech Stack:** Python 3 static AST audit, pytest, generated Markdown/JSON reports, FastAPI Web App source (read-only for this vertical).

---

## File structure

- Modify: `scripts/migration/audit_bot_to_web.py`
  - Add one private terminal catalog and one mapping helper.
  - Route exact/timestamp-independent menu records and observed templates through it before generic mapping.
  - Render `MENU_ACTION_TERMINAL_CATALOG_CONTRACT.md`, update generated README and known-gaps text.
- Modify: `tests/test_migration_audit.py`
  - Replace stale source-review assertions for observed Menu records.
  - Add focused catalog, template, dynamic/case, report and browser-boundary tests.
- Create (generated): `docs/migration/MENU_ACTION_TERMINAL_CATALOG_CONTRACT.md`
- Modify (generated): `docs/migration/README.md`, `docs/migration/KNOWN_GAPS_AND_GUARDS.md`, `docs/migration/VIDEO_MENU_DEFERRED_CALLBACK_CONTRACT.md`, and report JSON files.

## Acceptance catalogue

The following exact Bot menu values are terminally Bot-only unless they are already in an existing fresh-navigation allow-list:

```python
expected_exact = {
    "menu|admin_confirm_clear_stale_jobs",
    "menu|admin_confirm_refund_job",
    "menu|admin_confirm_maintenance_off",
    "menu|admin_confirm_maintenance_on",
    "menu|admin_packages_grant_combo",
    "menu|admin_packages_grant_monthly",
    "menu|admin_packages_user",
    "menu|admin_provider_test",
    "menu|finance_compliance_update",
    "menu|tax_config",
    "menu|tax_estimate",
    "menu|tax_estimate_month",
    "menu|tax_estimate_previous",
    "menu|tax_estimate_quarter",
    "menu|tax_export",
    "menu|tax_export_custom_help",
    "menu|tax_export_month",
    "menu|tax_export_previous",
    "menu|tax_export_quarter",
    "menu|guide_guided_video",
    "menu|guide_video_ai",
    "menu|hint_film_blueprint",
    "menu|hint_growth_loop",
    "menu|hint_scene_pack",
    "menu|hint_video_status",
    "menu|translation_video_factory",
    "menu|video_ai_true",
    "menu|video_frame_intro",
}
expected_templates = {
    "menu|{*}", "menu|admin_confirm_ack_{*}", "menu|{*}_auto",
    "menu|{*}_de", "menu|{*}_en", "menu|{*}_fr", "menu|{*}_ja",
    "menu|{*}_ko", "menu|{*}_th", "menu|{*}_vi", "menu|{*}_zh",
}
```

The catalog preserves separate source evidence for canonical job/refund, finance/tax, provider/package/maintenance, and `VIDEO_MENU_LAST` cases. A future unlisted literal/template remains non-actionable source-review evidence; it may not inherit Web navigation, a route, identity, payment, provider, job, or output behavior.

### Task 1: Record red tests for the terminal boundary

**Files:**
- Modify: `tests/test_migration_audit.py`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add a focused exact-catalog test before implementation**

```python
def test_menu_terminal_catalog_classifies_observed_bot_only_values() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    for source, contract in audit.MENU_TERMINAL_TELEGRAM_ONLY_ACTIONS.items():
        mapped = audit._map_callback(source, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == contract["resolution"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
```

- [ ] **Step 2: Run the new test and confirm RED**

Run: `python -m pytest -q tests/test_migration_audit.py -k menu_terminal_catalog_classifies_observed_bot_only_values`

Expected: failure because `MENU_TERMINAL_TELEGRAM_ONLY_ACTIONS` does not exist.

- [ ] **Step 3: Add template and non-inheritance tests before implementation**

```python
for template in audit.MENU_TERMINAL_TELEGRAM_ONLY_TEMPLATES:
    mapped = audit._map_callback_template(template, evidence, routes)
    assert mapped is not None
    assert (mapped["target"], mapped["status"]) == ("TELEGRAM_ONLY", "TELEGRAM_ONLY")

for raw in ("MENU|main", "menu|future_video_action", "menu|video_ai_true|again"):
    mapped = audit._map_callback(raw, "callback_data", evidence, routes)
    assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert mapped["target"] not in {"/dashboard", "/video-studio", "/admin", "/admin/callbacks"}
```

- [ ] **Step 4: Run focused tests and confirm RED for the desired reason**

Run: `python -m pytest -q tests/test_migration_audit.py -k 'menu_terminal_catalog or menu_callbacks_are_exact'`

Expected: failures only from the old source-review implementation/statuses, not import/setup errors.

### Task 2: Implement the private finite terminal catalog

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add immutable exact/template catalog constants adjacent to `MENU_ACTION_REGISTRY`**

Use a dictionary whose values contain only `classification`, bounded `resolution`, `source_dispositions`, and static `source_evidence`. No target route, feature key, Bot ID, Telegram identity, price, provider key, job/output data, or action payload belongs in a terminal record.

```python
MENU_TERMINAL_TELEGRAM_ONLY_ACTIONS = {
    "menu|admin_confirm_maintenance_on": {
        "classification": "admin",
        "resolution": "bot_admin_maintenance_mutation_telegram_only",
        "source_dispositions": (
            "BOT_ADMIN_ONLY", "CANONICAL_BOT_MAINTENANCE_MUTATION",
            "TELEGRAM_CONFIRMATION_CONTEXT_REQUIRED", "NO_RUNTIME_CLAIM",
        ),
        "source_evidence": "...",
    },
}
MENU_TERMINAL_TELEGRAM_ONLY_TEMPLATES = frozenset({...})
```

- [ ] **Step 2: Add one terminal mapping helper**

```python
def _menu_terminal_telegram_only_mapping(identifier, source_kind, evidence, contract=None):
    policy = contract or MENU_UNREVIEWED_DYNAMIC_TERMINAL_POLICY
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": "TELEGRAM_ONLY",
        "classification": policy["classification"],
        "status": "TELEGRAM_ONLY",
        "resolution": policy["resolution"],
        "source_dispositions": tuple(policy["source_dispositions"]),
        "source_evidence": policy["source_evidence"],
        "evidence": evidence,
    }
```

- [ ] **Step 3: Call the helper before generic menu routing, while preserving exact navigation allow-lists**

In `_map_callback`, check exact terminal records after rejecting invalid case variants but before Finance/Tax/Job/Video source-review branches. Preserve the residual raw `menu|` source-review fallthrough for future Bot drift. In `_map_callback_template`, recognize only the finite observed templates before the existing generic `menu|` fail-closed fallback. Do not change mappings for non-menu namespaces.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run: `python -m pytest -q tests/test_migration_audit.py -k 'menu_terminal_catalog or menu_callbacks_are_exact or tax_accounting_guidance or job_lock_recovery'`

Expected: all selected tests pass after updating old assertions to the intentional `TELEGRAM_ONLY` terminal contract.

### Task 3: Generate auditable contract documentation

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Derive terminal rows only from the private catalog**

```python
menu_terminal_contract_rows = [
    [source, "exact", contract["classification"], "TELEGRAM_ONLY", contract["resolution"],
     ", ".join(contract["source_dispositions"])]
    for source, contract in MENU_TERMINAL_TELEGRAM_ONLY_ACTIONS.items()
] + [[template, "template", "customer/admin boundary", "TELEGRAM_ONLY", "unreviewed_dynamic_menu_value_telegram_only", "..."]
     for template in sorted(MENU_TERMINAL_TELEGRAM_ONLY_TEMPLATES)]
```

- [ ] **Step 2: Emit the contract and references**

Write `MENU_ACTION_TERMINAL_CATALOG_CONTRACT.md` with the privacy/no-action boundary and table. Add its link to generated `README.md`, and update `KNOWN_GAPS_AND_GUARDS.md` / deferred Video wording so they say that these source records are terminal Bot-only and do not signal Web implementation or runtime parity.

- [ ] **Step 3: Add report/browser boundary tests**

```python
result = audit.run_audit(bot_root, web_root, "baseline", reports, docs)
menu_mappings = [m for m in result["parity_gap"]["callback_mappings"] + result["parity_gap"]["callback_template_mappings"] if m["source"] in expected_exact | expected_templates]
assert all(m["status"] == "TELEGRAM_ONLY" for m in menu_mappings)
assert "MENU_ACTION_TERMINAL_CATALOG_CONTRACT.md" in (docs / "README.md").read_text()
assert "menu|admin_confirm_maintenance_on" not in json.dumps(menu_capability_catalog())
```

- [ ] **Step 4: Run documentation-focused tests and confirm GREEN**

Run: `python -m pytest -q tests/test_migration_audit.py -k 'menu_terminal_catalog or current_migration_evidence or menu_callbacks'`

Expected: all selected tests pass and generated test docs include the new contract.

### Task 4: Regenerate static evidence and verify the isolated branch

**Files:**
- Modify (generated): `reports/migration/*.json`, `docs/migration/*`

- [ ] **Step 1: Run the static audit against the frozen Bot baseline**

Run the repository's existing read-only migration audit command with the frozen `b29d0d474974075f4cba963d2c510f49d2d1b3e4` source baseline. Do not import/start `bot.py`, invoke a provider, PayOS, Telegram, wallet/Xu, webhook, or a live job.

- [ ] **Step 2: Inspect regenerated parity output**

Run a read-only JSON filter asserting that the 61 frozen-baseline `callback_mappings` and `callback_template_mappings` represented by the exact acceptance catalogue are `TELEGRAM_ONLY`; existing navigation remains unchanged, future unknown menu values remain fail-closed, and no raw callback appears in `copyfast_registry.menu_capability_catalog()`.

- [ ] **Step 3: Run targeted and full static audit tests**

Run:

```text
python -m pytest -q tests/test_migration_audit.py
python -m compileall -q scripts/migration/audit_bot_to_web.py
git diff --check
```

Expected: tests, compile, and whitespace gates pass. Warnings must be recorded but no failures are accepted.

- [ ] **Step 4: Commit only this vertical**

Run:

```text
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration reports/migration docs/superpowers/specs/2026-08-01-menu-action-terminal-catalog-design.md docs/superpowers/plans/2026-08-01-menu-action-terminal-catalog.md
git commit -m "audit: close menu action terminal catalog"
```

### Task 5: Independent reviews, PR, merge, and Railway verification

**Files:**
- Review: branch diff only

- [ ] **Step 1: Run a spec-compliance review**

Verify every value in the acceptance catalogue is terminally mapped, existing navigation remains exact, and no Video implementation, Bot edit, provider/payment/bridge change, or browser endpoint was added.

- [ ] **Step 2: Run a code/security review**

Verify policy ordering is case-sensitive, unknown values cannot borrow a navigation route, terminal data has no sensitive state, generated docs make no runtime equivalence claim, and the public Web catalog contains no raw Bot callback.

- [ ] **Step 3: Open a single PR and wait for CI**

Use branch `feature/p0-webapp-copyfast261-menu-action-terminal-catalog`. Address any CI regression in this branch before merging; do not rebase unrelated work.

- [ ] **Step 4: Merge only after green CI, then verify Railway**

Confirm GitHub merge, Railway deployment success, `/health` HTTP 200, and that anonymous protected app routes still redirect/return a non-cacheable unauthorized boundary. Do not test a provider, PayOS, Telegram login, wallet, webhook, or live job.

## Plan self-review

- Scope coverage: exact actions, dynamic templates, safe fallthrough, generated contract, migration reports, tests, PR/CI/Railway are all covered.
- No placeholder scan: each implementation and test step is concrete; the catalog preserves only required facts and uses bounded policy fields.
- Type consistency: all terminal mapper records use existing `source_kind`, `source`, `target`, `classification`, `status`, `resolution`, `source_dispositions`, `source_evidence`, and `evidence` keys.
