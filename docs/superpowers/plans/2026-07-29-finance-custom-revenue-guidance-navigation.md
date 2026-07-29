# Finance Custom Revenue Guidance Navigation Implementation Plan

> For agentic workers: use subagent-driven-development or executing-plans task by task.

**Goal:** Add safe navigation-only parity for the one reviewed Finance custom
revenue guidance callback without importing Bot Finance data or action state.

**Architecture:** Add one raw-key descriptor to the finite private
ADMIN_ERP_FRESH_WEB_NAVIGATION_ACTIONS registry. The static audit continues to
generate evidence from its frozen source snapshot; the Web application receives
no new route or handler.

**Tech Stack:** Python static auditor, generated Markdown/JSON evidence and
focused Pytest contracts.

---

### Task 1: Lock exact-key and authority behavior

Files:
- Modify tests/test_migration_audit.py

- [ ] Write a failing test for menu|finance_revenue_custom_help that requires:
  target /admin/finance, NAVIGATION_ONLY,
  BOT_FINANCE_REVENUE_CUSTOM_PERIOD_GUIDANCE_NOT_REPLAYED, and all required
  signed-admin boundaries.
- [ ] Assert MENU|FINANCE_REVENUE_CUSTOM_HELP and
  menu|finance_revenue_custom_help|future stay MENU_SOURCE_REVIEW_REQUIRED.
- [ ] Run the focused test and observe red because the finite descriptor is
  absent.

### Task 2: Implement one finite static descriptor

Files:
- Modify scripts/migration/audit_bot_to_web.py
- Modify generated docs/migration and reports/migration files

- [ ] Add only exact menu|finance_revenue_custom_help with target
  /admin/finance, classification admin, feature_key admin_finance,
  authority SIGNED_CANONICAL_ADMIN_READ and launch_mode WEB_NAVIGATION.
- [ ] Add dispositions: BOT_ADMIN_ONLY,
  FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION,
  BOT_FINANCE_REVENUE_CUSTOM_PERIOD_GUIDANCE_NOT_REPLAYED,
  NO_CANONICAL_FINANCE_DATA_TRANSFER,
  NO_FINANCE_PERIOD_OR_COMMAND_TRANSFER,
  NO_REPORT_EXPORT_OR_FILE_DELIVERY,
  NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION and NO_RUNTIME_CLAIM.
- [ ] State in source evidence that the frozen callback renders static
  custom-period guidance plus a selector only; it does not transfer a
  selected period, report, export or write behavior.
- [ ] Regenerate documented static-only evidence and reject unrelated
  VIDEO/capability/skills/QA changes.
- [ ] Run focused migration tests, Python compile and git diff --check.

### Task 3: Review and publish

- [ ] Confirm bot.py, bridge/runtime, Web route/API, wallet, ledger, PayOS,
  provider, tax/compliance, export and unrelated generated Video QA files do
  not change.
- [ ] Commit with Map Finance custom revenue guidance to Web navigation and
  publish the isolated branch after the focused gate is green.
