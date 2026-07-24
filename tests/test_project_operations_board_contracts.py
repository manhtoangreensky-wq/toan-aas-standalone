"""Focused UI/security contracts for the canonical Project Operations Board."""

import json
import re
from pathlib import Path

import copyfast_pages

ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "PROJECT_OPERATIONS_BOARD_CONTRACT.md").read_text(encoding="utf-8")


def project_surface() -> str:
    start = PORTAL.index("function projectCenterReadState")
    end = PORTAL.index("// Memory Center mirrors", start)
    return PORTAL[start:end]


def root_renderer() -> str:
    start = PORTAL.index("function renderProjectCenter(page, context)")
    end = PORTAL.index("// Memory Center mirrors", start)
    return PORTAL[start:end]


def project_shell_payload(path: str) -> dict[str, object]:
    response = copyfast_pages.render_portal(path, interface_locale="en")
    assert response.status_code == 200
    match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        response.body.decode("utf-8"),
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_project_operations_board_keeps_canonical_routes_without_a_duplicate_hub() -> None:
    surface = project_surface()
    assert 'customerPage("/projects", "Project Center"' in PORTAL
    assert 'customerPage("/projects/new", "Project mới"' in PORTAL
    assert 'path: "/projects/:id"' in PORTAL
    assert "function renderProjectCenterAuthoring" in surface
    assert 'const authoringRoute = route === "/projects/new";' in surface
    assert "renderProjectCenterAuthoring(page, context, canCreate)" in surface
    assert "/project-hub" not in PORTAL


def test_project_authoring_is_a_server_routable_exact_path_with_a_reviewed_shell_title() -> None:
    assert 'PROJECT_CREATE_PATH = "/projects/new"' in (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    payload = project_shell_payload("/projects/new")
    assert payload["path"] == "/projects/new"
    assert payload["title"] == "New Project · TOAN AAS"


def test_project_operations_board_has_truthful_owner_scoped_read_states() -> None:
    root = root_renderer()
    for token in (
        'const readState = projectCenterReadState(context);',
        "if (!canView)",
        'if (readState === "loading")',
        'if (readState !== "ready")',
        'data-portal-action="projects-refresh"',
        "Không có dữ liệu cũ",
        "Không có activity giả",
    ):
        assert token in root
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "URLSearchParams", "bridge_request", "CORE_BRIDGE"):
        assert forbidden.lower() not in root.lower()


def test_project_operations_board_separates_authoring_and_honest_create_access() -> None:
    surface = project_surface()
    root = root_renderer()
    authoring_start = surface.index("function renderProjectCenterAuthoring")
    authoring_end = surface.index("function renderProjectCenter(page, context)")
    authoring = surface[authoring_start:authoring_end]
    assert 'data-portal-action="project-create"' in authoring
    assert 'data-portal-route="${safeText(route)}"' in authoring
    assert 'transientFormValues(route)' in authoring
    assert 'data-portal-action="project-create"' not in root
    for token in (
        "const startAction = canCreate",
        'href="/projects/new"',
        "portal-project-operations-create-guard",
        "Chỉ có quyền xem",
        "Không có timeline suy đoán",
        "Project active trên trang này",
        "Studio Documents trên trang này",
    ):
        assert token in root


def test_project_operations_board_uses_existing_signed_reader_and_clears_failures() -> None:
    hydration = INTEGRATION[
        INTEGRATION.index("async function hydrateProjects("):
        INTEGRATION.index("async function hydrateMemoryCenter", INTEGRATION.index("async function hydrateProjects("))
    ]
    for token in (
        "const requestEpoch = ++projectCenterListHydrationEpoch;",
        "projectCenterRequestIsCurrent(requestEpoch, projectCenterListHydrationEpoch, sessionEpoch, expectedPath)",
        'expectedPath === "/projects"',
        'projectCenterReadState: "loading"',
        "projectListing: projectListingProjection(filter, offset, result.data, items.length)",
        'projectCenterReadState: "ready"',
        "projects: []",
        'projectCenterReadState: "failed"',
    ):
        assert token in hydration
    assert hydration.index('projectCenterReadState: "loading"') < hydration.index("const result = await api(projectListPath(filter, offset));")
    for forbidden in ("bridge_request", "CORE_BRIDGE", "payos", "wallet", "provider"):
        assert forbidden.lower() not in hydration.lower()
    assert 'projectCenterReadState: account ? "loading" : "guarded"' in INTEGRATION
    assert 'projectCenterReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.projectCenterReadState || ""))' in PORTAL
    assert "function projectRouteUsesListView()" in INTEGRATION
    assert 'return currentPortalPath() === "/projects";' in INTEGRATION
    root = root_renderer()
    assert root.index("if (authoringRoute)") < root.index('if (readState === "loading")')


def test_project_authoring_draft_is_cleared_before_every_fresh_signed_projection() -> None:
    clear_start = INTEGRATION.index("function clearSessionScopedTransientDrafts()")
    clear_end = INTEGRATION.index("function toast", clear_start)
    clear = INTEGRATION[clear_start:clear_end]
    assert 'const PROJECT_CREATE_ROUTE = "/projects/new";' in INTEGRATION
    assert "clearTransientFormDraft(PROJECT_CREATE_ROUTE);" in clear
    hydrate_start = INTEGRATION.index("async function hydrate()")
    hydrate_end = INTEGRATION.index("async function hydrateCampaignCalendar", hydrate_start)
    assert "clearSessionScopedTransientDrafts();" in INTEGRATION[hydrate_start:hydrate_end]
    pageshow_start = INTEGRATION.index('window.addEventListener("pageshow"')
    pageshow_end = INTEGRATION.index('window.addEventListener("visibilitychange"', pageshow_start)
    assert "event.persisted" in INTEGRATION[pageshow_start:pageshow_end]
    assert "hydrate()" in INTEGRATION[pageshow_start:pageshow_end]


def test_project_operations_board_is_private_in_pwa_and_app_first_on_mobile() -> None:
    private_prefixes = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/projects"' in private_prefixes
    assert '"/" + "api/v1/projects"' in private_prefixes
    assert '"/projects"' not in shell
    assert '"/api/v1/projects"' not in shell
    for token in (
        ".portal-project-operations-board",
        ".portal-project-center-authoring",
        ".portal-project-operations-create-guard",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
        ".portal-project-operations-board .portal-project-card:hover { transform: none; }",
    ):
        assert token in CSS
    board_css = CSS[CSS.index("/* Project Operations Board"):]
    assert "linear-gradient" not in board_css


def test_project_operations_contract_records_current_authority_and_non_goals() -> None:
    for token in (
        "`/projects`",
        "`/projects/new`",
        "`/projects/{uuid}`",
        "GET /api/v1/projects?limit=50&offset=…",
        "owner-scoped",
        "current list page",
        "No database table",
        "PayOS",
        "Service Worker",
        "44px",
    ):
        assert token in CONTRACT
