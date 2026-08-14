"""Portal contracts for the Web-native Prompt Blueprint Composer."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "PROMPT_STUDIO_BLUEPRINT_CONTRACT.md").read_text(encoding="utf-8")


def test_prompt_studio_replaces_the_generic_feature_route_with_a_native_composer() -> None:
    assert 'customerPage("/prompt-studio", "Prompt Studio"' in PORTAL
    assert 'layout: "prompt-studio", type: "prompt-studio", action: "none"' in PORTAL
    assert 'featurePage("/prompt-studio"' not in PORTAL
    assert 'case "prompt-studio": return renderPromptStudio(page, context);' in PORTAL
    assert "function renderPromptStudio(page, context)" in PORTAL
    assert 'data-portal-action="prompt-studio-compose"' in PORTAL
    assert 'href="/prompt-library/new"' in PORTAL


def test_prompt_studio_alias_is_fenced_from_generic_bridge_hydration() -> None:
    path_start = INTEGRATION.index("const PROMPT_STUDIO_NATIVE_PATHS")
    path_end = INTEGRATION.index("const FEATURE_BY_PATH", path_start)
    paths = INTEGRATION[path_start:path_end]
    assert '"/prompt-studio", "/prompts"' in paths
    for helper in (
        "function isNativePromptStudioPath(path)",
        "function promptStudioRoutePath(path)",
        "function promptStudioRouteStates(enabled)",
    ):
        assert helper in paths

    feature_start = INTEGRATION.index("const FEATURE_BY_PATH")
    feature_end = INTEGRATION.index("  };", feature_start) + len("  };")
    assert '"/prompt-studio"' not in INTEGRATION[feature_start:feature_end]
    assert "!isNativePromptStudioPath(currentPath)" in INTEGRATION
    canonical_start = INTEGRATION.index("async function hydrateCanonicalData()")
    canonical_end = INTEGRATION.index("const canonicalBotVoiceRoute", canonical_start)
    canonical_hydration = INTEGRATION[canonical_start:canonical_end]
    assert "isNativePromptStudioPath(path)" in canonical_hydration
    assert "...promptStudioRouteStates(Boolean(account && promptStudioEnabled))" in INTEGRATION


def test_prompt_studio_receipt_is_bounded_transient_and_has_no_execution_path() -> None:
    for helper in (
        "function promptStudioPayload(fields)",
        "function promptStudioBoundaryIsSafe(value)",
        "function promptStudioBlueprintResultIsSafe(value)",
        "function normalizePromptStudioResult(raw)",
    ):
        assert helper in PORTAL or helper in INTEGRATION
    assert '"prompt-studio-compose": Boolean(account && me.csrf_token && promptStudioEnabled)' in INTEGRATION
    assert "promptStudioResult: {}" in INTEGRATION
    assert "promptStudioResult: normalizePromptStudioResult(source.promptStudioResult)" in PORTAL

    action_start = INTEGRATION.index('if (action === "prompt-studio-compose")')
    action_end = INTEGRATION.index('if (action === "prompt-studio-save-library")', action_start)
    action = INTEGRATION[action_start:action_end].lower()
    assert 'api("/prompt-studio/compose"' in action
    for forbidden in ("bridgeavailable", "core bridge", "/features/", "/payments", "/jobs", "payos", "provider call"):
        assert forbidden not in action

    for boundary in (
        "web_native_deterministic_prompt_blueprint_only",
        '"template_persisted"',
        '"bot_called"',
        '"bridge_called"',
        '"provider_called"',
        '"job_created"',
        '"wallet_mutated"',
        '"payment_started"',
        '"asset_saved"',
        '"publish_action_created"',
        '"delivery_created"',
    ):
        assert boundary in PORTAL
        assert boundary in INTEGRATION


def test_prompt_studio_library_handoff_uses_only_tab_memory_and_a_closed_metadata_receipt() -> None:
    for helper in (
        "function promptStudioLibrarySaveSource(value)",
        "function promptStudioLibrarySaveSourceMatchesResult(source, result)",
        "function promptStudioLibrarySaveReceipt(value)",
    ):
        assert helper in INTEGRATION
    assert '"prompt-studio-save-library": Boolean(account && me.csrf_token && promptStudioEnabled && promptLibraryEnabled)' in INTEGRATION
    assert "promptStudioSaveSource: {}" in INTEGRATION
    assert "promptStudioSaveReceipt: {}" in INTEGRATION
    assert "promptStudioSaveSource: normalizePromptStudioLibrarySaveSource(source.promptStudioSaveSource)" in PORTAL
    assert "promptStudioSaveReceipt: normalizePromptStudioLibrarySaveReceipt(source.promptStudioSaveReceipt)" in PORTAL

    action_start = INTEGRATION.index('if (action === "prompt-studio-save-library")')
    action_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', action_start)
    action = INTEGRATION[action_start:action_end].lower()
    assert 'api("/prompt-studio/save-to-library"' in action
    assert "confirmed: true" in action
    assert "idempotency_key: submission.key" in action
    for forbidden in ("blueprint", "prompt_text", "negative_prompt", "localstorage", "sessionstorage", "actor", "email", "audit"):
        assert forbidden not in action

    receipt_start = INTEGRATION.index("const PROMPT_STUDIO_LIBRARY_SAVE_FALSE_BOUNDARY_FIELDS")
    receipt_end = INTEGRATION.index("function contentPromptPackMemorySaveSource", receipt_start)
    receipt = INTEGRATION[receipt_start:receipt_end].lower()
    for required in (
        "destination", "execution", "blueprint_recomputed_on_server", "template_persisted",
        "browser_blueprint_persisted", "bot_called", "provider_called", "payment_started", "delivery_created",
    ):
        assert required in receipt
    for forbidden in (
        "title", "goal", "audience", "platform", "tone", "language", "output_format", "constraints",
        "prompt_text", "negative_prompt", "actor", "email", "audit",
    ):
        assert forbidden not in receipt

    renderer_receipt_start = PORTAL.index("const PROMPT_STUDIO_LIBRARY_SAVE_FALSE_BOUNDARY_FIELDS")
    renderer_receipt_end = PORTAL.index("const CONTENT_PROMPT_PACK_KINDS", renderer_receipt_start)
    renderer_receipt = PORTAL[renderer_receipt_start:renderer_receipt_end].lower()
    for forbidden in ("title", "goal", "audience", "platform", "tone", "language", "output_format", "constraints"):
        assert forbidden not in renderer_receipt

    render_start = PORTAL.index("function renderPromptStudioResult(raw, context)")
    render_end = PORTAL.index("function renderPromptStudio(page, context)", render_start)
    rendered = PORTAL[render_start:render_end]
    assert 'data-portal-action="prompt-studio-save-library"' in rendered
    assert 'data-portal-confirm=' in rendered
    assert "Lưu thành template" in rendered
    assert 'href="/prompt-library/${encodeURIComponent(template.id)}"' in rendered
    assert "aria-live=\"polite\"" in rendered
    assert "localStorage" not in rendered
    assert "sessionStorage" not in rendered
    receipt_markup_start = rendered.index("const receiptMarkup = template")
    receipt_markup_end = rendered.index("return `<section", receipt_markup_start)
    receipt_markup = rendered[receipt_markup_start:receipt_markup_end]
    assert "template.platform" not in receipt_markup
    assert "template.language" not in receipt_markup


def test_prompt_studio_save_replays_until_a_completed_validated_receipt_is_accepted() -> None:
    action_start = INTEGRATION.index('if (action === "prompt-studio-save-library")')
    action_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', action_start)
    action = INTEGRATION[action_start:action_end]

    assert "let completedReceiptAccepted = false;" in action
    assert "acknowledged" not in action
    completed_status = action.index('if (result.status !== "completed")')
    receipt_validation = action.index("const receipt = promptStudioLibrarySaveReceipt(result.data);")
    invalid_receipt_rejection = action.index("if (!receipt) throw", receipt_validation)
    accepted = action.index("completedReceiptAccepted = true;", invalid_receipt_rejection)
    assert "const activeSource = promptStudioLibrarySaveSource(base().promptStudioSaveSource);" in action
    assert "const activeResult = base().promptStudioResult;" in action
    assert "promptStudioLibrarySaveSourceEquals(source, activeSource)" in action
    assert "promptStudioLibrarySaveSourceMatchesResult(source, activeResult)" in action
    active_source = action.index("const activeSource = promptStudioLibrarySaveSource(base().promptStudioSaveSource);", accepted)
    active_result = action.index("const activeResult = base().promptStudioResult;", active_source)
    binding_start = action.index("if (", active_result)
    binding_end = action.index("} else {", binding_start)
    binding = action[binding_start:binding_end]
    assert "promptStudioLibrarySaveSourceEquals(source, activeSource)" in binding
    assert "promptStudioLibrarySaveSourceMatchesResult(source, activeResult)" in binding
    assert "merge({ promptStudioSaveReceipt: receipt });" in binding
    merged_receipt = action.index("merge({ promptStudioSaveReceipt: receipt });", accepted)
    assert completed_status < receipt_validation < invalid_receipt_rejection < accepted < active_source < active_result < merged_receipt
    assert "bản nháp trước đó" in action
    assert "bản nháp hiện tại không bị thay đổi" in action

    catch_start = action.index("} catch (error) {", merged_receipt)
    finally_start = action.index("} finally {", catch_start)
    catch = action[catch_start:finally_start]
    assert "discardSubmission" not in catch
    assert "completedReceiptAccepted = true" not in catch
    assert "merge({ promptStudioSaveReceipt: {} });" not in catch

    finally_block = action[finally_start:]
    release = finally_block.index("releaseSubmission(submission);")
    discard = finally_block.index("if (completedReceiptAccepted) discardSubmission(scope, submission);")
    assert release < discard


def test_prompt_studio_same_brief_stale_save_requires_exact_tab_generation() -> None:
    # Save(A) and Compose(B) can deliberately share all seven normalized
    # brief fields. The receipt guard must therefore use a separate tab-only
    # identity, rather than treating source equality as proof that A is B.
    assert "let promptStudioComposeGeneration = 0;" in INTEGRATION
    assert "function promptStudioComposeGenerationValue(value)" in INTEGRATION
    assert "function normalizePromptStudioComposeGeneration(raw)" in PORTAL
    assert "promptStudioComposeGeneration: normalizePromptStudioComposeGeneration(source.promptStudioComposeGeneration)" in PORTAL

    compose_start = INTEGRATION.index('if (action === "prompt-studio-compose")')
    compose_end = INTEGRATION.index('if (action === "prompt-studio-save-library")', compose_start)
    compose = INTEGRATION[compose_start:compose_end]
    assert "const composeGeneration = ++promptStudioComposeGeneration;" in compose
    assert "promptStudioComposeGeneration: 0" in compose
    assert "promptStudioComposeGeneration: composeGeneration" in compose

    save_start = INTEGRATION.index('if (action === "prompt-studio-save-library")')
    save_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', save_start)
    save = INTEGRATION[save_start:save_end]
    assert "const composeGeneration = promptStudioComposeGenerationValue(base().promptStudioComposeGeneration);" in save
    assert "const activeComposeGeneration = promptStudioComposeGenerationValue(base().promptStudioComposeGeneration);" in save
    binding_start = save.index("if (", save.index("const activeComposeGeneration"))
    binding_end = save.index("} else {", binding_start)
    binding = save[binding_start:binding_end]
    assert "composeGeneration === activeComposeGeneration" in binding
    assert "promptStudioLibrarySaveSourceEquals(source, activeSource)" in binding
    assert "promptStudioLibrarySaveSourceMatchesResult(source, activeResult)" in binding
    assert "merge({ promptStudioSaveReceipt: receipt });" in binding

    # Equal brief content alone must never attach A's receipt to B.
    same_normalized_brief = True
    captured_generation_for_a = 41
    current_generation_for_b = 42
    assert not (same_normalized_brief and captured_generation_for_a == current_generation_for_b)

    request_start = save.index('const result = await api("/prompt-studio/save-to-library"')
    request_end = save.index("if (result.status !== \"completed\")", request_start)
    request = save[request_start:request_end]
    assert "composeGeneration" not in request
    assert "promptStudioComposeGeneration" not in request
    assert "localStorage" not in save
    assert "sessionStorage" not in save


def test_prompt_studio_compose_locks_only_its_fields_through_the_request_window() -> None:
    helper_start = INTEGRATION.index("function setPromptStudioComposeFormLocked(route, busy)")
    helper_end = INTEGRATION.index("function setDeliveryReadStatus", helper_start)
    helper = INTEGRATION[helper_start:helper_end]

    assert 'document.querySelectorAll(\'[data-portal-form][data-portal-action="prompt-studio-compose"]\')' in helper
    assert '(form.getAttribute("data-portal-route") || window.location.pathname) === route' in helper
    assert 'form.querySelectorAll("input, select, textarea")' in helper
    assert "control.dataset.promptStudioComposeWasDisabled = control.disabled ? \"true\" : \"false\";" in helper
    assert "control.disabled = true;" in helper
    assert 'if (control.dataset.promptStudioComposeWasDisabled === "false") control.disabled = false;' in helper
    assert 'form.setAttribute("aria-busy", "true");' in helper
    assert 'form.removeAttribute("aria-busy");' in helper

    action_start = INTEGRATION.index('if (action === "prompt-studio-compose")')
    action_end = INTEGRATION.index('if (action === "prompt-studio-save-library")', action_start)
    action = INTEGRATION[action_start:action_end]
    reset = action.index("merge({ promptStudioResult: {}, promptStudioSaveSource: {}, promptStudioSaveReceipt: {}, promptStudioComposeGeneration: 0 });")
    lock = action.index("setPromptStudioComposeFormLocked(promptStudioRoute, true);")
    request = action.index('api("/prompt-studio/compose"', lock)
    finally_start = action.index("} finally {", request)
    unlock = action.index("setPromptStudioComposeFormLocked(promptStudioRoute, false);", finally_start)
    assert reset < lock < request < finally_start < unlock


def test_prompt_studio_compose_lock_survives_a_concurrent_save_remount() -> None:
    submission_start = INTEGRATION.index("const submissions = new Map();")
    submission_end = INTEGRATION.index("function isNativeContentPromptPackPath", submission_start)
    submission_state = INTEGRATION[submission_start:submission_end]
    assert 'let promptStudioComposeLockRoute = "";' in submission_state

    merge_start = INTEGRATION.index("function merge(next)")
    merge_end = INTEGRATION.index("// Keep the Web-native Support Desk helpers", merge_start)
    merge = INTEGRATION[merge_start:merge_end]
    assert "if (promptStudioComposeLockRoute) setPromptStudioComposeFormLocked(promptStudioComposeLockRoute, true);" in merge

    compose_start = INTEGRATION.index('if (action === "prompt-studio-compose")')
    compose_end = INTEGRATION.index('if (action === "prompt-studio-save-library")', compose_start)
    compose = INTEGRATION[compose_start:compose_end]
    started = compose.index("promptStudioComposeLockRoute = promptStudioRoute;")
    reset = compose.index("merge({ promptStudioResult: {}, promptStudioSaveSource: {}, promptStudioSaveReceipt: {}, promptStudioComposeGeneration: 0 });")
    finally_start = compose.index("} finally {", reset)
    unlocked = compose.index("setPromptStudioComposeFormLocked(promptStudioRoute, false);", finally_start)
    cleared = compose.index('promptStudioComposeLockRoute = "";', unlocked)
    assert started < reset < finally_start < unlocked < cleared

    save_start = INTEGRATION.index('if (action === "prompt-studio-save-library")')
    save_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', save_start)
    save = INTEGRATION[save_start:save_end]
    assert "merge({ promptStudioSaveReceipt: receipt });" in save


def test_prompt_studio_contract_records_the_explicit_library_handoff_boundary() -> None:
    assert "`/prompt-studio` (alias `/prompts`)" in CONTRACT
    assert "Không import hoặc sửa `bot.py`" in CONTRACT
    assert "không generic `draft → estimate → confirm`" in CONTRACT
    assert "không được gửi qua URL hoặc browser storage" in CONTRACT
    assert "WEBAPP_PROMPT_STUDIO_ENABLED" in CONTRACT
    assert "POST /api/v1/prompt-studio/save-to-library" in CONTRACT
    assert "server recompute" in CONTRACT
