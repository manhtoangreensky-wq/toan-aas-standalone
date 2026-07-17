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
    assert "if (isNativePromptStudioPath(path) ||" in INTEGRATION
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
    action_end = INTEGRATION.index('if (action === "content-prompt-pack-compose")', action_start)
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


def test_prompt_studio_contract_records_the_explicit_library_handoff_boundary() -> None:
    assert "`/prompt-studio` (alias `/prompts`)" in CONTRACT
    assert "Không import hoặc sửa `bot.py`" in CONTRACT
    assert "không generic `draft → estimate → confirm`" in CONTRACT
    assert "không được gửi qua URL hoặc browser storage" in CONTRACT
    assert "WEBAPP_PROMPT_STUDIO_ENABLED" in CONTRACT
