"""Static safety contracts for the Web-native Project Package UI."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_project_package_is_a_separate_web_native_portal_surface() -> None:
    assert 'customerPage("/project-packages", "Project Packages"' in PORTAL
    assert 'layout: "project-packages"' in PORTAL
    assert "function renderProjectPackagePanel(page, context, project)" in PORTAL
    assert "function renderProjectPackages(page, context)" in PORTAL
    assert 'case "project-packages": return renderProjectPackages(page, context);' in PORTAL
    assert '"/project-packages", "Project Packages"' in PORTAL
    panel = PORTAL[PORTAL.index("function renderProjectPackagePanel"):PORTAL.index("function renderProjectPackages")]
    assert 'data-portal-action="project-package-export"' in panel
    assert 'data-portal-action="project-package-refresh"' in panel
    assert "Package/Web export không tạo Job Bot" in panel
    assert "assetDownloadPath" not in panel
    assert "jobId" not in panel
    assert "fetch(" not in panel


def test_project_package_hydration_and_actions_do_not_depend_on_bot_bridge() -> None:
    assert "const projectPackageEnabled" in INTEGRATION
    assert '"project-package-view": Boolean(account && projectPackageEnabled)' in INTEGRATION
    assert '"project-package-export": Boolean(account && me.csrf_token && projectPackageEnabled)' in INTEGRATION
    assert "async function hydrateProjectPackages(projectId, offsetValue)" in INTEGRATION
    assert '"/project-packages"' in INTEGRATION
    assert "function projectPackageListPath" in INTEGRATION
    assert "api(projectPackageListPath(selectedProjectId, offset))" in INTEGRATION
    action = INTEGRATION[INTEGRATION.index('if (action === "project-package-export")'):INTEGRATION.index('if (action === "project-create")')]
    assert "bridgeAvailable" not in action
    assert "provider" not in action.lower()
    assert "payment" not in action.lower()
    assert "discardSubmission(scope, submission);" in action
    assert "projectPackages" in PORTAL
    assert "projectPackageEnabled" in PORTAL


def test_project_package_download_is_same_origin_attachment_and_never_cached_by_pwa() -> None:
    assert "/api/v1/project-packages/" in PORTAL
    assert "/api/v1/project-packages" in SERVICE_WORKER
    assert "projectPackages" not in SERVICE_WORKER
    assert ".portal-project-package-grid" in CSS
    assert ".portal-project-package-actions" in CSS
    assert ".portal-project-package-intro" in CSS
    assert "@media (max-width: 980px)" in CSS
    assert "@media (max-width: 700px)" in CSS
