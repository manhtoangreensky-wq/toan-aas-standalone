"""Regression contracts for the Workspace Draft → Project Studio transition.

The handoff receipt is durable server state, but the browser must not call a
new Project "not found" while its owner-scoped detail request is in flight.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "static" / "portal" / "portal.js"
PAGES = ROOT / "copyfast_pages.py"
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _render_project_detail(
    page_states: dict[str, str],
    *,
    page_status: str = "processing",
    authenticated: bool = True,
) -> str:
    """Run the actual Project renderer before its owner-scoped read returns."""

    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to exercise the Portal Project renderer")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error("missing " + start);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error("missing " + end);
  return source.slice(offset, finish);
}
function safeText(value) { return String(value ?? ""); }
function projectText(_key, fallback) { return fallback; }
function renderHero() { return "<hero></hero>"; }
const ICONS = { refresh: "refresh" };
function portalIcon(icon) { return `<svg data-icon="${icon}"></svg>`; }
function renderEmpty(title, body, icon) { return `<empty>${portalIcon(icon)}${title}|${body}</empty>`; }
function validProjectId() { return false; }
eval(extract("function renderProjectDetail(page, context)", "function renderFeatureFamily"));
const route = "/projects/8a0d55e2-2287-4387-8bd1-3774a56f023f";
const html = renderProjectDetail(
  { path: "/projects/:id", routePath: route, status: process.argv[3] },
  { projectDetail: {}, projectDocuments: [], pageStates: JSON.parse(process.argv[2]), session: { authenticated: process.argv[4] === "true" } }
);
process.stdout.write(JSON.stringify({ html }));
'''
    result = subprocess.run(
        [node, "-e", script, str(PORTAL), json.dumps(page_states), page_status, str(authenticated).lower()],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return str(json.loads(result.stdout)["html"])


def test_pending_project_route_never_announces_not_found_before_owner_read_returns() -> None:
    route = "/projects/8a0d55e2-2287-4387-8bd1-3774a56f023f"
    html = _render_project_detail({route: "processing"})

    assert "Đang tải Project" in html
    assert "Không tìm thấy Project" not in html
    assert 'role="status"' in html
    assert 'data-icon="refresh"' in html


def test_direct_project_route_starts_loading_before_the_owner_scoped_read_returns() -> None:
    """A reload begins with no client pageStates, not a missing Project."""

    html = _render_project_detail({})

    assert "Đang tải Project" in html
    assert "Không tìm thấy Project" not in html


def test_guarded_project_route_explains_sign_in_instead_of_claiming_not_found() -> None:
    """A completed signed-session guard is not evidence of a missing Project."""

    route = "/projects/8a0d55e2-2287-4387-8bd1-3774a56f023f"
    html = _render_project_detail({route: "guarded"}, authenticated=False)

    assert "Project đang được bảo vệ" in html
    assert "Không tìm thấy Project" not in html
    assert 'href="/login?next=%2Fprojects%2F8a0d55e2-2287-4387-8bd1-3774a56f023f"' in html


def test_server_shell_marks_only_project_detail_as_initially_pending() -> None:
    """The first DOM paint gets a neutral dynamic-route loading marker."""

    import copyfast_pages

    project_route = "/projects/8a0d55e2-2287-4387-8bd1-3774a56f023f"
    project_shell = copyfast_pages.render_portal(project_route, interface_locale="vi")
    project_match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        project_shell.body.decode("utf-8"),
        flags=re.DOTALL,
    )
    assert project_match
    project_payload = json.loads(project_match.group(1).replace("<\\/", "</"))
    assert project_payload["pageStates"] == {project_route: "processing"}

    list_shell = copyfast_pages.render_portal("/projects", interface_locale="vi")
    list_match = re.search(
        r'<script id="portal-bootstrap" type="application/json">(.*?)</script>',
        list_shell.body.decode("utf-8"),
        flags=re.DOTALL,
    )
    assert list_match
    list_payload = json.loads(list_match.group(1).replace("<\\/", "</"))
    assert "pageStates" not in list_payload
    assert 'payload["pageStates"] = {normalized: "processing"}' in PAGES.read_text(encoding="utf-8")


def test_workspace_handoff_marks_only_the_destination_route_as_processing() -> None:
    handoff = _between(INTEGRATION, 'if (action === "workspace-draft-attach") {', 'if (action === "workspace-draft-archive") {')
    detail = _between(INTEGRATION, "async function hydrateProjectDetail(path)", "async function hydrateProjectPackages")

    assert 'const projectRoute = `/projects/${encodeURIComponent(projectId)}`;' in handoff
    assert 'pageStates: { ...(base().pageStates || {}), [projectRoute]: "processing" }' in handoff
    assert handoff.index("pageStates:") < handoff.index("await hydrateProjectDetail(projectRoute);")
    # The POST receipt is allowed to prove that the server accepted the
    # requested Project ID.  It must never be used as the visible Project
    # detail because the GET remains the owner-scoped source of truth.
    assert "projectDetail: receipt.project" not in handoff
    assert 'pageStates: { ...(base().pageStates || {}), [path]: "processing" }' in detail
    assert detail.index('pageStates: { ...(base().pageStates || {}), [path]: "processing" }') < detail.index("const result = await api")


def test_project_handoff_discards_an_acknowledged_retry_key_and_syncs_browser_history() -> None:
    """A receipt acknowledgement stays terminal even if local hydration then fails."""

    handoff = _between(INTEGRATION, 'if (action === "workspace-draft-attach") {', 'if (action === "workspace-draft-archive") {')
    history_sync = _between(INTEGRATION, "function synchronizePortalHistoryNavigation()", 'window.addEventListener("popstate", synchronizePortalHistoryNavigation);')

    assert "let acknowledged = false;" in handoff
    assert handoff.index("acknowledged = true;") < handoff.index("const receipt = result.data")
    assert "acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);" in handoff
    assert "acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);" not in handoff
    assert "if (acknowledged) discardSubmission(scope, submission);" in handoff
    assert handoff.index("if (acknowledged) discardSubmission(scope, submission);") > handoff.index("releaseSubmission(submission);")
    assert "window.location.pathname" in history_sync
    assert "const projectState = projectRoute" in history_sync
    assert "...projectState" in history_sync
    assert "projectDetail: {}," in history_sync
    assert "path: route," in history_sync
    assert 'title: "TOAN AAS",' in history_sync
    assert history_sync.index("path: route,") < history_sync.index("void hydrate()")


def test_project_loading_copy_is_available_in_every_supported_interface_locale() -> None:
    for key, translations in {
        "project.detail.loadingTitle": ("Đang tải Project", "Loading Project", "正在加载项目"),
        "project.detail.loadingBody": (
            "Portal đang kiểm tra Project owner-scoped",
            "The Portal is checking the owner-scoped Project",
            "Portal 正在检查此账户范围内的项目",
        ),
        "project.detail.guardedTitle": ("Project đang được bảo vệ", "Project access is protected", "项目访问已受保护"),
        "project.detail.signIn": ("Đăng nhập để tiếp tục", "Sign in to continue", "登录以继续"),
    }.items():
        for translation in translations:
            assert f'"{key}": "{translation}' in I18N


def test_workspace_handoff_uses_scoped_aura_controls_and_existing_motion_lifecycle() -> None:
    """The handoff is polished without becoming a global CSS/animation fork."""

    for required in (
        ".portal-workspace-draft-grid:has(> .portal-workspace-draft:only-child)",
        "grid-template-columns: minmax(0, 1fr)",
        "max-width: 960px",
        ".portal-page.portal-workspace-drafts .portal-workspace-draft-attach",
        ".portal-workspace-draft-attach > .portal-checkbox",
        ".portal-workspace-draft-attach :is(.portal-select, .portal-checkbox, .portal-button--secondary)",
        "min-height: 44px",
        "var(--portal-action)",
        "var(--portal-focus)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert required in THEME

    for required in (
        '".portal-workspace-drafts > .portal-card"',
        '".portal-workspace-draft"',
        '".portal-workspace-draft-attach"',
    ):
        assert required in MOTION
