"""Static contracts for the signed Web-native Workspace Setup experience."""

import importlib
from pathlib import Path
import sys

from fastapi.testclient import TestClient

from copyfast_pages import render_portal
from copyfast_registry import allowed_paths


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
APP_MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_memory",
    "copyfast_workspace_setup", "copyfast_starter_kits",
]


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _make_app_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "portal-route-session-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "portal-route-test-session-secret")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name in ("CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET"):
        monkeypatch.delenv(name, raising=False)
    for name in APP_MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def _register_and_login(client: TestClient) -> None:
    credentials = {
        "email": "first-run-portal-routes@example.com",
        "password": "correct-horse-battery-staple",
        "display_name": "First Run Owner",
    }
    registered = client.post("/api/v1/auth/register", json=credentials)
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert signed_in.status_code == 200


def test_first_run_app_routes_require_and_accept_a_real_signed_session(tmp_path, monkeypatch) -> None:
    with _make_app_client(tmp_path, monkeypatch) as client:
        for route in ("/workspace/setup", "/starter-kits"):
            anonymous = client.get(route, follow_redirects=False)
            assert anonymous.status_code == 307
            assert anonymous.headers["location"] == f"/login?next={route}"

        _register_and_login(client)

        for route in ("/workspace/setup", "/starter-kits"):
            signed = client.get(route)
            assert signed.status_code == 200
            assert b'<script id="portal-bootstrap" type="application/json">' in signed.content

        detail = client.get("/starter-kits/project-foundation")
        assert detail.status_code == 200
        assert b'<script id="portal-bootstrap" type="application/json">' in detail.content


def test_first_run_paths_are_server_allowlisted_and_render_the_portal_shell() -> None:
    """Every signed first-run entrypoint must survive a direct browser request."""

    paths = allowed_paths()
    assert {"/workspace/setup", "/starter-kits"} <= paths
    assert "/starter-kits/project-foundation" not in paths

    for path in ("/workspace/setup", "/starter-kits", "/starter-kits/project-foundation"):
        response = render_portal(path, interface_locale="vi")
        assert response.status_code == 200
        assert b'<script id="portal-bootstrap" type="application/json">' in response.body


def test_workspace_setup_is_a_signed_app_route_not_a_video_or_landing_change() -> None:
    assert 'customerPage("/workspace/setup", "Thiết lập Workspace"' in PORTAL
    assert 'layout: "workspace-setup"' in PORTAL
    assert 'case "workspace-setup": return renderWorkspaceSetup(page, context);' in PORTAL
    assert 'href: "/workspace/setup"' in PORTAL

    view = _between(PORTAL, "function renderWorkspaceSetup", "function renderOnboarding")
    for requirement in (
        'data-portal-action="workspace-setup-save"',
        'data-portal-action="workspace-setup-skip"',
        'data-portal-action="workspace-setup-refresh"',
        "data-portal-no-transient",
        "portalIcon(icon)",
        "ICONS.workboard",
        "aria-live=\"polite\"",
        "Chọn tối đa 3 nhóm studio ưu tiên",
        "workspace-setup-focus-status",
        "aria-describedby=\"workspace-setup-focus-status\"",
        "Một biểu mẫu, không có bước ẩn.",
    ):
        assert requirement in view
    for forbidden in ("localStorage", "sessionStorage", "telegram_id", "canonical_user_id", "/video", "aria-current=\"step\""):
        assert forbidden not in view
    guide = _between(PORTAL, "function renderDashboardStartGuide", "function renderDashboardAccountLane")
    assert 'href: "/workspace/setup"' in guide
    focus_limit = _between(PORTAL, "function synchronizeWorkspaceSetupFocusLimit", "function copyCanonicalDraftText")
    for requirement in ("checked.length > 3", "atLimit && !input.checked", "data-workspace-setup-focus-status", "status.textContent"):
        assert requirement in focus_limit


def test_workspace_setup_bootstrap_is_allowlisted_and_hydration_is_session_fenced() -> None:
    normalizer = _between(PORTAL, "function normalizeWorkspaceSetupBootstrap", "function normalizeAccountSecurityBootstrap")
    for requirement in (
        "WORKSPACE_SETUP_BOOTSTRAP_STATES",
        "WORKSPACE_SETUP_BOOTSTRAP_ROLES",
        "WORKSPACE_SETUP_BOOTSTRAP_GOALS",
        "WORKSPACE_SETUP_BOOTSTRAP_EXPERIENCE",
        "WORKSPACE_SETUP_BOOTSTRAP_FOCUS",
        "focusSeen",
        ".slice(0, 3)",
        "bootstrapSafeTimestamp",
        'locale: ["vi", "en", "zh"].includes(locale)',
    ):
        assert requirement in normalizer
    assert "workspaceSetup: normalizeWorkspaceSetupBootstrap(source.workspaceSetup)" in PORTAL
    for forbidden in ("telegram_id", "canonical_user_id", "localStorage.", "sessionStorage."):
        assert forbidden not in normalizer

    for epoch in ("workspaceSetupSessionEpoch", "workspaceSetupHydrationEpoch"):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION
    hydrate = _between(INTEGRATION, "function workspaceSetupRequestIsCurrent", "function workspaceDraftRequestIsCurrent")
    for requirement in (
        "requestEpoch === workspaceSetupHydrationEpoch",
        "sessionEpoch === workspaceSetupSessionEpoch",
        "currentPortalPath() === expectedPath",
        '["/workspace/setup", "/dashboard"].includes(expectedPath)',
        "base().session && base().session.authenticated === true",
        'api("/workspace/setup")',
        'workspaceSetup: workspaceSetupProjection({}, "guarded")',
    ):
        assert requirement in hydrate
    assert "localStorage." not in hydrate
    assert "sessionStorage." not in hydrate
    assert 'if (account && ["/workspace/setup", "/dashboard"].includes(currentPath)) await hydrateWorkspaceSetup();' in INTEGRATION
    assert "function workspaceSetupBoundaryIsSafe" in INTEGRATION
    assert "WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS" in INTEGRATION
    assert "function workspaceSetupProfileIsConsistent" in INTEGRATION
    assert 'workspaceSetupProjection(result.data, "read_only").readState !== "read_only"' in INTEGRATION


def test_workspace_setup_mutation_uses_current_revision_csrf_idempotency_and_rehydration() -> None:
    helper = _between(INTEGRATION, "function workspaceSetupCurrentRevision", "function workspaceDraftRequestIsCurrent")
    for requirement in (
        "workspaceSetupCurrentRevision()",
        "WORKSPACE_SETUP_ROLES.has(role)",
        "WORKSPACE_SETUP_GOALS.has(goal)",
        "WORKSPACE_SETUP_EXPERIENCE.has(experience)",
        "focusAreas.length > 3",
        "acquireSubmission(scope, featureFingerprint(payload))",
        'api("/workspace/setup"',
        "idempotency_key: submission.key",
        "await hydrateWorkspaceSetup()",
        'if (currentPortalPath() !== "/workspace/setup") return;',
        'window.location.assign("/dashboard")',
        "discardSubmission(scope, submission)",
    ):
        assert requirement in helper
    assert "expected_revision: expectedRevision" in helper
    assert "telegram_id" not in helper
    assert "localStorage" not in helper
    assert '"workspace-setup-save": Boolean(account && me.csrf_token)' in INTEGRATION
    assert 'if (action === "workspace-setup-save")' in INTEGRATION
    assert 'if (action === "workspace-setup-skip")' in INTEGRATION


def test_workspace_setup_has_responsive_private_ui_and_server_boundaries() -> None:
    for selector in (
        ".portal-workspace-setup-steps",
        ".portal-workspace-setup-context",
        ".portal-workspace-setup-form-grid",
        ".portal-workspace-setup-focus-grid",
        ".portal-workspace-setup-focus-card",
        ".portal-workspace-setup-focus-status",
        ".portal-workspace-setup-form .portal-select, .portal-workspace-setup-form .portal-button { min-height: 44px; }",
        "@media (max-width: 700px)",
    ):
        assert selector in CSS
    assert "min-height: 44px" in CSS
    assert '"/" + "api/v1/workspace/setup"' in WORKER
    assert '"/workspace/setup"' in WORKER
    for requirement in (
        "import copyfast_workspace_setup",
        "app.include_router(copyfast_workspace_setup.router)",
        "WORKSPACE_SETUP_BODY_MAX_BYTES = 8 * 1024",
        "WORKSPACE_SETUP_API_PATHS",
        "workspace_setup_write",
        "workspace-setup-read",
        "WEB_WORKSPACE_SETUP_BODY_TOO_LARGE",
    ):
        assert requirement in APP
