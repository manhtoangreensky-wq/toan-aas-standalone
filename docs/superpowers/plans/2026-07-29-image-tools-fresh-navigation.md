# Image Tools Fresh Web Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Let only a finite set of reviewed Telegram Image Tools picker literals open an existing fresh signed Web-native image route; stateful, AI/provider, billing, result, and dynamic callbacks remain fail-closed.

**Architecture:** The static migration auditor gains a closed raw-case-sensitive IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS dictionary. _map_imgtool_callback checks it before its current IMGTOOL_SOURCE_REVIEW_REQUIRED fallback. A match is audit-only NAVIGATION_ONLY evidence: neither the source callback nor any Bot state reaches a URL, form, browser storage, request, or database row.

**Tech Stack:** Python 3 static AST audit, pytest, generated Markdown/JSON migration evidence.

---

## Scope and non-goals

- Frozen Bot baseline is b29d0d474974075f4cba963d2c510f49d2d1b3e4.
- Do not edit bot.py, Bot bridge, provider, PayOS, wallet/Xu, job, webhook, image runtime/API/UI, video, capability/skill, or LocalVideoStudio26-owned files.
- Existing Web routes independently retain signed-session, owner-scope, CSRF, idempotency, Asset Vault, feature-flag, output-validation, and private-delivery rules.
- A match must not preselect an image, prompt, ratio, method, preset, overlay, tier, price, confirmation, or delivery.
- Every case variant, suffix, dynamic template, AI/upscale, tier/confirmation, last-result, save, request, result, or back action remains source-review-required.

## File structure

- Modify: scripts/migration/audit_bot_to_web.py.
  - Add registry, exact mapper, existing-route propagation at both call sites, and generated Image Tools contract rows/text.
- Modify: tests/test_migration_audit.py.
  - Add exact allowlist, no-transfer, near-miss, template, and synthetic-audit coverage.
- Regenerate: docs/migration/*.md and reports/migration/*.json from frozen Bot SHA; update the current metric sentence in docs/migration/TEST_EVIDENCE.md from the regenerated parity report.
- Create: docs/superpowers/plans/2026-07-29-image-tools-fresh-navigation.md.

### Task 1: Write the red regression contract

**Files:**
- Modify: tests/test_migration_audit.py in test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes.

- [ ] **Step 1: Add the exact desired registry assertion.**

~~~python
imgtool_navigation = {
    "imgtool|prompt_manual": ("/image/prompt-composer", "web_image_prompt_composer"),
    "imgtool|edit_need_image": ("/image/edit", "web_image_enhance"),
    "imgtool|resize_need_image": ("/image/resize", "web_image_resize"),
    "imgtool|resize_task|ratio": ("/image/resize", "web_image_resize"),
    "imgtool|resize_task|pixels": ("/image/resize", "web_image_resize"),
    "imgtool|resize_method|blur": ("/image/resize", "web_image_resize"),
    "imgtool|resize_method|pad": ("/image/resize", "web_image_resize"),
    "imgtool|resize_method|crop": ("/image/resize", "web_image_resize"),
    "imgtool|editor_resize": ("/image/resize", "web_image_resize"),
    "imgtool|editor_presets": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_preset|photo_clear_detail": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_preset|product_clean": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_preset|cinematic_warm": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_preset|fresh_blue": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_preset|food_vivid": ("/image/edit", "web_image_enhance"),
    "imgtool|editor_overlays": ("/image/brand-overlay", "web_image_brand_overlay"),
    "imgtool|editor_text": ("/image/brand-overlay", "web_image_brand_overlay"),
    "imgtool|editor_logo": ("/image/brand-overlay", "web_image_brand_overlay"),
}
assert set(audit.IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS) == set(imgtool_navigation)
~~~

- [ ] **Step 2: Assert the exact mapped shape.**

For each entry, call audit._map_callback with the four target routes and assert target, intent, customer, NAVIGATION_ONLY, resolution reviewed_imgtool_fresh_web_navigation, authority SIGNED_WEB_NATIVE_CUSTOMER, and launch mode WEB_NAVIGATION. Assert this exact source disposition set:

~~~python
{
    "FRESH_SIGNED_WEB_IMAGE_TOOL_NAVIGATION",
    "FINITE_BOT_IMAGE_TOOL_ENTRY_ONLY",
    "NO_RAW_BOT_CALLBACK_OR_IMAGE_STATE_TO_BROWSER",
    "BOT_IMAGE_TOOL_PENDING_OR_RESULT_STATE_NOT_REPLAYED",
    "WEB_NATIVE_OWNER_SCOPED_IMAGE_TOOL_ONLY",
    "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION",
    "NO_RUNTIME_CLAIM",
}
~~~

- [ ] **Step 3: Keep unsafe values on the generic boundary.**

Move allowlisted literals out of the current all-negative loop. Verify IMGTOOL|EDITOR_RESIZE, imgtool|resize_method|pad|future, imgtool|editor_preset|future, imgtool|ai_upscale_start, imgtool|edit_ai, imgtool|prompt_tier|basic, imgtool|edit_from_last, and imgtool|editor_save return IMGTOOL_SOURCE_REVIEW_REQUIRED with NEEDS_FEATURE_DISPOSITION. Keep templates imgtool|resize_method|{*}, imgtool|editor_preset|{*}, imgtool|prompt_tier|{*}, and imgtool|future|{*} fail-closed.

- [ ] **Step 4: Extend the synthetic static fixture.**

The fixture bot.py contains exact prompt, edit, resize, preset, and overlay literals plus AI/template negatives. Its Web app contains /image/prompt-composer, /image/edit, /image/resize, and /image/brand-overlay. Assert only exact literals become NAVIGATION_ONLY and IMAGE_TOOLS_CALLBACK_CONTRACT.md names reviewed_imgtool_fresh_web_navigation and no raw callback/image-state transfer.

- [ ] **Step 5: Run the red test.**

~~~powershell
python -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes
~~~

Expected: FAIL because IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS and its navigation result do not exist.

### Task 2: Implement the exact mapper

**Files:**
- Modify: scripts/migration/audit_bot_to_web.py near _imgtool_source_review_mapping, _map_imgtool_callback, _map_callback, and _map_callback_template.

- [ ] **Step 1: Add the closed raw-key registry.**

Use every Task 1 key with target and web_image_tool_intent string fields. Do not lower, casefold, split, prefix-match, or otherwise normalize keys.

- [ ] **Step 2: Add the fresh mapping helper.**

~~~python
def _imgtool_fresh_web_navigation_mapping(
    identifier: str,
    source_kind: str,
    evidence: dict[str, Any],
    existing_routes: set[str],
) -> dict[str, Any] | None:
    action = IMGTOOL_FRESH_WEB_NAVIGATION_ACTIONS.get(identifier)
    if action is None:
        return None
    target = str(action["target"])
    return {
        "source_kind": source_kind,
        "source": identifier,
        "target": target,
        "classification": "customer",
        "status": _mapping_status(target, existing_routes, telegram_only=False, navigation_only=True),
        "resolution": "reviewed_imgtool_fresh_web_navigation",
        "source_dispositions": (
            "FRESH_SIGNED_WEB_IMAGE_TOOL_NAVIGATION",
            "FINITE_BOT_IMAGE_TOOL_ENTRY_ONLY",
            "NO_RAW_BOT_CALLBACK_OR_IMAGE_STATE_TO_BROWSER",
            "BOT_IMAGE_TOOL_PENDING_OR_RESULT_STATE_NOT_REPLAYED",
            "WEB_NATIVE_OWNER_SCOPED_IMAGE_TOOL_ONLY",
            "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION",
            "NO_RUNTIME_CLAIM",
        ),
        "imgtool_navigation_authority": "SIGNED_WEB_NATIVE_CUSTOMER",
        "imgtool_navigation_launch_mode": "WEB_NAVIGATION",
        "web_image_tool_intent": str(action["web_image_tool_intent"]),
        "evidence": evidence,
    }
~~~

Add source_evidence that explicitly excludes callback, Telegram identity/file/result/pending state, prompt, ratio, method, preset, overlay, provider, wallet/payment, job, output, and delivery transfer.

- [ ] **Step 3: Invoke the helper before fallback.**

Change _map_imgtool_callback to accept existing_routes. After confirming raw namespace starts with imgtool|, return a fresh mapping when found; otherwise return the current generic mapping unchanged. Pass existing_routes from both _map_callback and _map_callback_template.

- [ ] **Step 4: Run the focused test green.**

Run the Task 1 command. Expected: 1 passed.

### Task 3: Render truthful frozen-baseline evidence

**Files:**
- Modify: scripts/migration/audit_bot_to_web.py in _render_docs.
- Regenerate: docs/migration/*.md and reports/migration/*.json.

- [ ] **Step 1: Add finite Image Tools rows before generic source-review rows.**

Each row uses the exact target/resolution and says fresh signed route only, no callback/image/prompt/preset/pending/result transfer or prefill, and no Bot/provider/Xu/PayOS/job/output/delivery/runtime effect.

- [ ] **Step 2: Correct generated explanatory text.**

Only finite exact tool-picker literals are navigation-only exceptions. Every unlisted imgtool|* value, including case variants, suffixes, templates, AI/upscale, tier/confirmation, last-result and back actions, remains IMGTOOL_SOURCE_REVIEW_REQUIRED and cannot inherit an Image route.

- [ ] **Step 3: Regenerate with the frozen static Bot baseline.**

~~~powershell
python scripts/migration/audit_bot_to_web.py --bot-root C:\Users\toann\Documents\Codex\2026-05-31\files-mentioned-by-the-user-bot\toanaas-hotfix-28ff87f --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --report-dir reports/migration --docs-dir docs/migration
~~~

Expected: result contains ok true and the requested SHA; Bot code is only materialized/read as a frozen snapshot.

- [ ] **Step 4: Synchronize the current test-evidence metric.**

Read mapping_coverage_percent from reports/migration/parity_gap.json and replace only the matching current static-audit safe-disposition percentage in docs/migration/TEST_EVIDENCE.md. This is required because the existing quality gate asserts that the checked-in human-readable current metric exactly agrees with the regenerated report; historical metrics remain untouched.

### Task 4: Verify, review, and integrate

**Files:**
- Verify: scripts/migration/audit_bot_to_web.py, tests/test_migration_audit.py, docs/migration, reports/migration.

- [ ] **Step 1: Run focused tests.**

~~~powershell
python -m pytest -q tests/test_migration_audit.py::test_static_audit_keeps_imgtool_callbacks_out_of_generic_web_routes tests/test_copyfast_image_operations.py tests/test_image_operation_portal_contracts.py
~~~

Expected: all selected tests pass without a Bot, provider, PayOS, or production request.

- [ ] **Step 2: Run static checks.**

~~~powershell
python -m compileall -q .
node --check static/portal/portal.js
node --check static/portal/integration.js
node --check static/portal/service-worker.js
git diff --check
git status --short --untracked-files=all
~~~

- [ ] **Step 3: Stage only task files and inspect staged scope.**

~~~powershell
git add docs/superpowers/specs/2026-07-29-image-tools-fresh-navigation-design.md docs/superpowers/plans/2026-07-29-image-tools-fresh-navigation.md scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py docs/migration/TEST_EVIDENCE.md docs/migration reports/migration
git diff --cached --check
git diff --cached --name-only
~~~

Expected: only spec/plan, static audit, focused test, and generated migration evidence. No Bot, UI/runtime, Video, capability/skill, provider/payment/wallet/webhook, or LocalVideoStudio26-owned file is staged.

- [ ] **Step 4: Complete spec then code-quality/security review.**

Review exact case sensitivity, no-transfer language, no generic imgtool override, generated evidence, and no runtime claim. Resolve every important finding and re-review any fix.

- [ ] **Step 5: Commit, push, PR, wait for the Web App quality gate, and merge only if green.**

~~~powershell
git commit -m "Add safe Image Tools Web navigation parity"
git push -u origin feature/p0-webapp-copyfast163-image-tools-fresh-navigation
~~~

## Plan self-review

- Every allowlisted literal, route, intent, no-transfer disposition, and unsafe family is named exactly.
- The mapper is closed and raw-case-sensitive; generic imgtool routing is never introduced.
- Existing signed Web-native routes are reused without a new image engine or runtime claim.
- The task excludes Bot modifications and the LocalVideoStudio26-owned area.
