"""Safety contracts for the former Bot content shortcut routes.

The routes remain stable for existing links, but must now use the bounded
Web-native Prompt Pack composer.  They cannot fall back to generic bridge
draft/estimate/confirm actions just because a browser opens an old path.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "CONTENT_PROMPT_PACK_CONTRACT.md").read_text(encoding="utf-8")


SHORTCUTS = (
    ("/content/caption", "/caption", "caption_hashtag"),
    ("/content/hashtag", "/hashtag", "caption_hashtag"),
    ("/content/hook", "/hook", "hook_script"),
    ("/content/script", "/script", "hook_script"),
    ("/content/storyboard", "/storyboard", "image_video_prompt"),
    ("/content/pack", "/content-pack", "content_ideas"),
)


def test_legacy_content_shortcuts_render_native_prompt_pack_with_a_safe_default() -> None:
    assert "function contentPromptPackShortcutPage(" in PORTAL
    for route, alias, kind in SHORTCUTS:
        assert f'contentPromptPackShortcutPage("{route}"' in PORTAL
        assert f'"{kind}", ["{alias}"]' in PORTAL
        assert f'featurePage("{route}"' not in PORTAL

    shortcut_start = PORTAL.index("function contentPromptPackShortcutPage(")
    shortcut_end = PORTAL.index("function guardedFeaturePage", shortcut_start)
    shortcut = PORTAL[shortcut_start:shortcut_end]
    assert 'type: "content-prompt-pack"' in shortcut
    assert 'layout: "content-prompt-pack"' in shortcut
    assert 'action: "none"' in shortcut
    assert "promptPackKind" in shortcut
    assert "feature-draft" not in shortcut

    renderer_start = PORTAL.index("function renderContentPromptPack(page, context)")
    renderer_end = PORTAL.index("function renderPublishReviewPackResult", renderer_start)
    renderer = PORTAL[renderer_start:renderer_end]
    assert "const route = String(page.routePath || page.path || \"/content/prompt-pack\");" in renderer
    assert "contentPromptPackKindForPage(page)" in renderer
    assert 'data-portal-route="${safeText(route)}"' in renderer
    assert "renderFields(contentPromptPackFields(), canCompose, context, values" in renderer
    assert "renderContentPromptPackResult(context.contentPromptPackResult, context.contentPromptPackSaveSource, canSaveToMemory, route)" in renderer
    assert 'data-portal-route="${safeText(activeRoute)}"' in PORTAL

    catalog_start = PORTAL.index("function catalogEntryState")
    catalog_end = PORTAL.index("function moduleCard", catalog_start)
    catalog = PORTAL[catalog_start:catalog_end]
    assert 'page.type === "content-prompt-pack"' in catalog
    assert 'context.capabilities["content-prompt-pack-compose"] === true' in catalog


def test_shortcut_paths_are_not_generic_bridge_features_or_canonical_hydration_targets() -> None:
    paths_start = INTEGRATION.index("const CONTENT_PROMPT_PACK_NATIVE_PATHS")
    paths_end = INTEGRATION.index("const FEATURE_BY_PATH", paths_start)
    native_paths = INTEGRATION[paths_start:paths_end]
    for route, alias, _ in SHORTCUTS:
        assert f'"{route}"' in native_paths
        assert f'"{alias}"' in native_paths
    for helper in (
        "function isNativeContentPromptPackPath(path)",
        "function contentPromptPackRoutePath(path)",
        "function contentPromptPackRouteStates(enabled)",
    ):
        assert helper in native_paths

    feature_start = INTEGRATION.index("const FEATURE_BY_PATH")
    feature_end = INTEGRATION.index("  };", feature_start) + len("  };")
    feature_map = INTEGRATION[feature_start:feature_end]
    for route, _, _ in SHORTCUTS:
        assert f'"{route}"' not in feature_map

    assert "...contentPromptPackRouteStates(Boolean(account && contentPromptPackEnabled))" in INTEGRATION
    assert "!isNativeContentPromptPackPath(currentPath)" in INTEGRATION
    assert "if (isNativeContentPromptPackPath(path) || isNativeContentStudioPath(path)" in INTEGRATION

    action_start = INTEGRATION.index('if (action === "content-prompt-pack-compose")')
    action_end = INTEGRATION.index('if (action === "publish-review-pack-compose")', action_start)
    action = INTEGRATION[action_start:action_end].lower()
    assert "contentpromptpackroutepath(route)" in action
    assert "[promptpackroute]: \"ready\"" in action
    for forbidden in ("bridgeavailable", "core bridge", "/features/", "/payments", "/jobs", "payos"):
        assert forbidden not in action


def test_shortcut_mapping_is_documented_as_a_native_request_only_composer() -> None:
    for route, alias, kind in SHORTCUTS:
        assert f"| `{route}` | `{alias}` | `{kind}` |" in CONTRACT
    assert "Chúng không\nđi vào generic Core Bridge" in CONTRACT
    assert "không nhận pending\nTelegram result" in CONTRACT
