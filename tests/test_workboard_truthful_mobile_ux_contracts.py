"""Contracts for truthful Workboard states and mobile Kanban layout."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _surface() -> str:
    start = PORTAL.index("// Workboard remains deliberately small")
    return PORTAL[start:PORTAL.index("function showToast", start)]


def test_overview_gates_metrics_and_board_on_signed_ready_state() -> None:
    surface = _surface()
    overview = surface[surface.index("function renderWorkboardOverview"):surface.index("function renderWorkboardNew")]
    assert 'const readState = ["loading", "ready", "failed", "guarded"].includes' in overview
    assert 'if (readState !== "ready")' in overview
    assert "workboardRecovery" in overview
    gate_end = overview.index("const items = workboardItems(context)")
    gate = overview[:gate_end]
    assert "workboardMetricCount" not in gate
    assert "renderWorkboardBoard" not in gate
    assert 'href="/workboard/new"' not in gate
    recovery = surface[surface.index("function workboardRecovery"):surface.index("function renderWorkboardOverview")]
    assert "Không dùng số 0 thay cho dữ liệu chưa xác minh" in recovery


def test_no_view_capability_uses_the_same_guarded_recovery_surface() -> None:
    surface = _surface()
    overview = surface[surface.index("function renderWorkboardOverview"):surface.index("function renderWorkboardNew")]
    no_view_start = overview.index("if (!canView)")
    no_view_end = overview.index("const items = workboardItems(context)")
    no_view_branch = overview[no_view_start:no_view_end]
    assert 'workboardRecovery("guarded"' in no_view_branch
    assert 'renderEmpty("Workboard đang được bảo vệ"' not in no_view_branch


def test_ready_empty_board_does_not_reintroduce_non_ready_copy() -> None:
    surface = _surface()
    overview = surface[surface.index("function renderWorkboardOverview"):surface.index("function renderWorkboardNew")]
    board_content = overview[overview.index("const content = view ==="):overview.index("const createAction")]
    assert "context.workboardReadState ===" not in board_content


def test_viewers_get_a_noninteractive_create_affordance() -> None:
    surface = _surface()
    tabs = surface[surface.index("function workboardTabs"):surface.index("function workboardView")]
    assert "function workboardTabs(active, context, allowCreate)" in tabs
    assert "workboard-tabs-new--disabled" in tabs
    assert 'aria-disabled="true"' in tabs
    assert 'href="/workboard/new"' in tabs
    # The disabled state is a span, never an anchor carrying aria-disabled.
    assert '<a class="portal-workboard-tabs-new" href="/workboard/new"' in tabs
    assert '<a class="portal-workboard-tabs-new" aria-disabled' not in tabs


def test_view_only_tab_keeps_the_same_touch_target_as_navigation_links() -> None:
    marker = "/* Final light Workboard surface */"
    theme = THEME[THEME.index(marker):]
    assert ".portal-workboard-tabs .portal-workboard-tabs-new--disabled" in theme
    disabled_start = theme.index(".portal-workboard-tabs .portal-workboard-tabs-new--disabled")
    disabled_rule = theme[disabled_start:theme.index("}", disabled_start)]
    for declaration in ("display: inline-flex", "align-items: center", "justify-content: center", "min-height: 44px", "padding: 10px 14px"):
        assert declaration in disabled_rule


def test_create_route_fails_closed_without_rendering_disabled_form() -> None:
    surface = _surface()
    renderer = surface[surface.index("function renderWorkboardNew"):surface.index("function renderWorkboardChecklist")]
    assert 'const readyForCreate = canCreate && readState === "ready"' in renderer
    assert "if (!readyForCreate)" in renderer
    assert "Không thể tạo công việc lúc này" in renderer
    recovery = surface[surface.index("function workboardRecovery"):surface.index("function renderWorkboardOverview")]
    assert 'href="/workboard"' in recovery
    guarded_branch = renderer[:renderer.index("return '<article", renderer.index("if (!readyForCreate)"))]
    assert "renderFields(workboardFields" not in guarded_branch


def test_mobile_kanban_is_one_column_without_horizontal_page_overflow() -> None:
    marker = "/* Final light Workboard surface */"
    mobile = THEME[THEME.index(marker):]
    mobile = mobile[mobile.index("@media (max-width: 700px)"):]
    assert ".portal-page.portal-workboard .portal-workboard-board-card" in mobile
    assert "overflow-x: visible" in mobile
    assert ".portal-page.portal-workboard .portal-workboard-board" in mobile
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert "min-width: 0" in mobile
    assert ".portal-page.portal-workboard .portal-workboard-column" in mobile


def test_mobile_workboard_titles_wrap_unbroken_user_content() -> None:
    marker = "/* Final light Workboard surface */"
    mobile = THEME[THEME.index(marker):]
    mobile = mobile[mobile.index("@media (max-width: 700px)"):]
    selector = ".portal-page.portal-workboard :is(.portal-workboard-card, .portal-workboard-card h3, .portal-workboard-card h3 a, .portal-workboard-card p, .portal-workboard-card footer)"
    assert selector in mobile
    rule = mobile[mobile.index(selector):mobile.index("}", mobile.index(selector))]
    assert "min-width: 0" in rule
    assert "overflow-wrap: anywhere" in rule
