"""Focused contracts for the non-video, Web-native Workspace Menu directory.

The page is intentionally a compact signed navigation surface, not another
feature engine or an attempt to replay Telegram menu callbacks.  These static
checks keep its catalog allow-list, private-cache policy and client boundary
closed while the broader portal continues to evolve.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _function(source: str, name: str) -> str:
    marker = f"function {name}("
    begin = source.index(marker)
    next_begin = source.find("\n  function ", begin + len(marker))
    return source[begin:] if next_begin < 0 else source[begin:next_begin]


def test_workspace_menu_is_an_explicit_signed_navigation_directory() -> None:
    assert 'WebFeature("workspace_menu", "Chuyển workspace", "content", "/workspace-menu"' in REGISTRY
    for declaration in (
        'customerPage("/workspace-menu", "Chuyển workspace"',
        'type: "workspace-menu", layout: "workspace-menu", fields: [], action: "none", status: "read_only"',
        'case "workspace-menu": return renderWorkspaceMenu(page, context);',
        '["/workspace-menu", "Chuyển workspace", ICONS.dashboard]',
        'href="/workspace-menu"',
    ):
        assert declaration in PORTAL

    # A browser-owned projection must remain fixed and must not expose the
    # existing public catalog's Video, admin or payment-write entries.
    specs = _between(
        PORTAL,
        "const WORKSPACE_MENU_CAPABILITY_SPECS = Object.freeze([",
        "]);\n\n  const WORKSPACE_MENU_GROUP_SPECS",
    )
    for key in (
        "workspace_home",
        "memory_center",
        "reminder_center",
        "campaign_planner",
        "chat_workspace",
        "prompt_studio",
        "image_studio",
        "image_prompt_composer",
        "documents",
        "subtitle_studio",
        "asset_vault",
        "media_workspace",
        "account",
        "wallet",
        "membership",
        "packages",
        "pricing",
        "support",
    ):
        assert f'key: "{key}"' in specs
    assert specs.count('key: "') == 18
    for forbidden in ("video", "admin", "wallet_topup", "menu|"):
        assert forbidden not in specs.lower()

    normalizer = _between(PORTAL, "function normalizeWorkspaceMenuCapabilities", "// Capability Hub")
    for requirement in (
        "WORKSPACE_MENU_CAPABILITY_SPECS.reduce",
        "safeHubText(item.feature_key, 80) === spec.featureKey",
        "safeHubRoute(item.route) === spec.route",
        "safeHubText(item.authority, 80) === spec.authority",
        "safeHubText(item.launch_mode, 80) === spec.launchMode",
        "safeHubText(item.availability, 80) === spec.availability",
        'safeHubText(item.execution, 80) === "NO_EXECUTION_CLAIM"',
    ):
        assert requirement in normalizer
    assert 'catalogReadState: source.catalogReadState === "read_only"' in PORTAL

    # Every fixed string added by this route has a reviewed vi/en/zh entry;
    # it must not leave Vietnamese-only cards behind after a locale switch.
    for key in (
        "nav.workspaceMenu",
        "page.workspaceMenu.title",
        "workspaceMenu.loadingTitle",
        "workspaceMenu.group.organize.title",
        "workspaceMenu.card.workspace_home.title",
        "workspaceMenu.card.support.description",
    ):
        assert I18N.count(f'"{key}":') == 3


def test_workspace_menu_renderer_only_links_to_reviewed_routes() -> None:
    renderer = _function(PORTAL, "renderWorkspaceMenu")
    card = _function(PORTAL, "workspaceMenuCard")
    for requirement in (
        "WORKSPACE_MENU_GROUP_SPECS.map",
        "context.workspaceMenuCapabilities",
            "catalogReadState === \"loading\"",
            "entries.length !== WORKSPACE_MENU_CAPABILITY_SPECS.length",
            "aria-busy=\"true\"",
            'workspaceMenuText("directoryLabel", "Danh sách workspace đã review")',
        "Navigation only",
        "Không có hành động tự động",
        "Video để phase riêng",
    ):
        assert requirement in renderer
    for requirement in (
        "safeHubRoute",
        "manifest[normalizePath(route)]",
        'page.access === "admin"',
        'href="${safeText(route)}"',
        "Mở workspace",
    ):
        assert requirement in card
    for source in (renderer, card):
        for forbidden in (
            "data-portal-action",
            "fetch(",
            "api(",
            "/internal/",
            "/api/",
            "localStorage",
            "sessionStorage",
            "telegram_id",
            "canonical_user_id",
            "menu|",
        ):
            assert forbidden not in source


def test_workspace_menu_is_excluded_from_generic_canonical_hydration_and_offline_cache() -> None:
    for declaration in (
        "function isNativeWorkspaceMenuPath(path)",
        'return String(path || "").split("?")[0] === "/workspace-menu";',
        '"/workspace-menu": account ? "read_only" : "guarded"',
        "!isNativeWorkspaceMenuPath(currentPath)",
        "if (isNativeWorkspaceMenuPath(path)",
    ):
        assert declaration in INTEGRATION
    assert "const catalogReadState = catalogResponse" in INTEGRATION
    assert 'catalogReadState,' in INTEGRATION

    shell = _between(WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    public_navigation = _between(WORKER, "const PUBLIC_NAVIGATION_PATHS = Object.freeze([", "]);\n// This is deliberately redundant")
    private_paths = _between(WORKER, "const PRIVATE_PATH_PREFIXES = Object.freeze([", "]);\n\nself.addEventListener(\"install\"")
    assert '"/workspace-menu"' in private_paths
    assert '"/workspace-menu"' not in shell
    assert '"/workspace-menu"' not in public_navigation

    styles = _between(CSS, "/* Workspace Menu is a compact", "/* Tax Readiness")
    for requirement in (
        ".portal-workspace-menu-grid",
        ".portal-workspace-menu-card:focus-visible",
        "min-height: 184px",
        "@media (max-width: 700px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert requirement in styles
