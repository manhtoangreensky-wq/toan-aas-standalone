"""Focused static contracts for the signed Web-native Starter Kits surface.

The catalog deliberately creates planning records only.  These checks keep the
browser route allow-list, confirmation boundary and offline policy narrow even
when later Portal work grows around the workspace.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


STARTER_KIT_KEYS = (
    "project-foundation",
    "content-foundation",
    "image-direction",
    "voice-script",
    "audio-brief",
    "subtitle-plan",
    "document-qa",
    "operations-board",
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_starter_kits_are_a_closed_workspace_route_family_without_video() -> None:
    browser_catalog = _between(PORTAL, "const STARTER_KIT_PORTAL_META", "// The legacy registry")
    bridge_catalog = _between(INTEGRATION, "const STARTER_KIT_KEYS", "function starterKitsSafeText")
    renderer = _between(PORTAL, "function starterKitCatalogItem", "function renderWorkspaceSetup")

    for key in STARTER_KIT_KEYS:
        assert f'"{key}"' in browser_catalog
        assert f'"{key}"' in bridge_catalog
    assert browser_catalog.lower().count('"') == len(STARTER_KIT_KEYS) * 2
    assert 'new Set([' in bridge_catalog
    assert "STARTER_KIT_PORTAL_KEYS" in PORTAL
    assert "STARTER_KIT_KEYS.has(key)" in INTEGRATION

    # A detail page is resolvable only when its key is in the fixed browser
    # catalog. It is not a generic /starter-kits/:slug authoring surface.
    resolver = _between(PORTAL, "function resolvePage", "if (/^\\/admin\\/governance")
    for requirement in (
        'normalized.startsWith("/starter-kits/")',
        'const meta = STARTER_KIT_PORTAL_META[kitKey];',
        'if (meta && normalized === `/starter-kits/${kitKey}`)',
        'type: "starter-kits", layout: "starter-kits", action: "none"',
        "browser không gửi nội dung Project, tài liệu, checklist hay reference.",
    ):
        assert requirement in resolver
    assert "STARTER_KIT_KEYS = frozenset(STARTER_KIT_BY_KEY)" in PAGES
    assert "normalized.removeprefix(\"/starter-kits/\") in STARTER_KIT_KEYS" in PAGES

    # This module is intentionally a Project-planning launchpad; Video Studio
    # remains outside the current implementation order and route family.
    for module_slice in (browser_catalog, bridge_catalog, renderer):
        assert "video" not in module_slice.lower()


def test_starter_kit_confirmation_is_signed_idempotent_and_route_fenced() -> None:
    detail = _between(PORTAL, "function renderStarterKitDetail", "function renderStarterKits")
    for requirement in (
        'data-portal-action="starter-kit-apply"',
        "data-portal-no-transient",
        "data-portal-confirm=",
        'name="kit_key"',
        'name="kit_version"',
        'name="expected_setup_revision"',
        'name="starter_kit_confirm" value="true" required',
        "không tạo kết quả hoàn tất hay chạy tác vụ bên ngoài.",
        "Nhấn lại cùng yêu cầu sẽ nhận lại receipt an toàn, không nhân đôi record.",
    ):
        assert requirement in detail

    payload = _between(INTEGRATION, "function starterKitApplyPayload", "async function applyStarterKit")
    for requirement in (
        "isNativeStarterKitsPath(route)",
        "fields.starter_kit_confirm !== true",
        "String(fields.kit_key || \"\").trim() !== key",
        "kit.version !== kitVersion",
        "profile.revision !== expectedSetupRevision",
        "return { key, kit_version: kitVersion, expected_setup_revision: expectedSetupRevision, confirmed: true };",
    ):
        assert requirement in payload

    apply = _between(INTEGRATION, "async function applyStarterKit", "async function hydrateWorkspaceSetup")
    for requirement in (
        "currentPortalPath() !== route",
        'base().capabilities["starter-kit-apply"] === true',
        "acquireSubmission(scope, featureFingerprint(payload))",
        'api(`/workspace/starter-kits/${encodeURIComponent(payload.key)}/apply`',
        "idempotency_key: submission.key",
        "starterKitApplyReceipt(result.data, payload.key)",
        "await hydrateStarterKits()",
        "window.location.assign(`/projects/${encodeURIComponent(receipt.project_id)}`)",
        "releaseSubmission(submission)",
    ):
        assert requirement in apply
    for forbidden in ("localStorage", "sessionStorage", 'api("/features', 'api("/payments', "api(\"/jobs"):
        assert forbidden not in apply
    assert '"starter-kit-apply": Boolean(account && me.csrf_token && starterKitsEnabled)' in INTEGRATION
    assert 'if (action === "starter-kit-apply")' in INTEGRATION


def test_starter_kits_fail_closed_without_engine_bridge_or_fake_output() -> None:
    boundary = _between(INTEGRATION, "const STARTER_KIT_BOUNDARY_FALSE_FIELDS", "function starterKitsSafeText")
    for false_field in (
        "bot_called",
        "bridge_called",
        "provider_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "publish_action_created",
        "notification_sent",
        "asset_created",
        "delivery_created",
    ):
        assert f'"{false_field}"' in boundary
    assert "boundary.execution === \"web_native_starter_kit_install\"" in INTEGRATION
    assert "STARTER_KIT_BOUNDARY_FALSE_FIELDS.every((field) => boundary[field] === false)" in INTEGRATION

    receipt = _between(INTEGRATION, "function starterKitApplyReceipt", "function priorFeatureFlow")
    for requirement in (
        "boundary.installation_created === true",
        "boundary.project_created === true",
        "boundary.studio_documents_created === true",
        "boundary.workboard_items_created === true",
        "every((field) => boundary[field] === false)",
    ):
        assert requirement in receipt

    status = _between(PORTAL, 'if (page.layout === "starter-kits")', 'if (status === "ready")')
    assert "không có integration, xử lý hay thanh toán" in status
    scope_rail = _between(PORTAL, "function starterKitScopeRail", "function renderStarterKitCatalog")
    for requirement in (
        "Không chạy công cụ hay sinh output",
        "Không thay đổi số dư hoặc giao dịch",
        "Không gửi thông báo hay phát hành nội dung",
    ):
        assert requirement in scope_rail

    # Generic bridge hydration must never replace the native account-scoped
    # catalog with Telegram/Core Bridge data.
    bootstrap = _between(INTEGRATION, "if (account && starterKitsEnabled", "function adminErpNavigationRoute")
    assert "await hydrateStarterKits()" in bootstrap
    assert "!isNativeStarterKitsPath(currentPath)) await hydrateCanonicalData()" in bootstrap


def test_starter_kits_remain_private_from_pwa_cache_and_responsive_in_the_app_shell() -> None:
    shell = _between(WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    public_navigation = _between(WORKER, "const PUBLIC_NAVIGATION_PATHS = Object.freeze([", "]);\n// This is deliberately redundant")
    private_paths = _between(WORKER, "const PRIVATE_PATH_PREFIXES = Object.freeze([", "]);\n\nself.addEventListener(\"install\"")
    for private_route in ('"/" + "api/v1/workspace/starter-kits"', '"/starter-kits"'):
        assert private_route in private_paths
        assert private_route not in shell
        assert private_route not in public_navigation

    styles = _between(CSS, "/* Starter Kits stay inside the app shell", "/* Admin ERP keeps")
    for requirement in (
        ".portal-starter-kits-layout",
        ".portal-starter-kit-grid",
        ".portal-starter-kit-confirmation",
        "min-height: 44px",
        "@media (max-width: 700px)",
    ):
        assert requirement in styles
