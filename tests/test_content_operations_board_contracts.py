"""Focused UI/security contracts for the canonical Content Operations Board.

The board is an app-first view over the existing owner-scoped Content Studio.
It must not become a second content system, Bot adapter, or fake execution UI.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "CONTENT_OPERATIONS_BOARD_CONTRACT.md").read_text(encoding="utf-8")


def board_surface() -> str:
    return PORTAL[
        PORTAL.index("function contentStudioEventLabel"):
        PORTAL.index("function renderContentStudioDetail", PORTAL.index("function contentStudioEventLabel"))
    ]


def test_content_operations_board_keeps_canonical_routes_without_a_second_hub() -> None:
    surface = board_surface()
    assert 'customerPage("/content-studio", "Creative Content Studio"' in PORTAL
    assert 'customerPage("/content-studio/new", "Content Brief mới"' in PORTAL
    assert 'const authoringRoute = route === "/content-studio/new";' in surface
    assert "renderContentStudioAuthoring(page, context, canCreate)" in surface
    assert 'href="/content-studio/new"' in surface
    assert "/content-hub" not in PORTAL


def test_content_operations_board_uses_truthful_signed_read_states_only() -> None:
    surface = board_surface()
    for token in (
        'const readState = String(context.contentStudioReadState || "guarded");',
        "if (!canView)",
        'if (readState === "loading")',
        'if (readState !== "ready")',
        'data-portal-action="content-studio-refresh"',
        "Không hiển thị dữ liệu cũ",
        "Không có output giả",
    ):
        assert token in surface
    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        "sessionStorage",
        "URLSearchParams",
        "bridge_request",
        "CORE_BRIDGE",
    ):
        assert forbidden.lower() not in surface.lower()


def test_content_operations_board_only_starts_allowlisted_kinds_and_keeps_activity_safe() -> None:
    surface = board_surface()
    for token in (
        "CONTENT_STUDIO_KINDS.map",
        'href="/content-studio/new?kind=${encodeURIComponent(kind)}"',
        "contentStudioKindFromQuery()",
        "const requestedKind = contentStudioQueryKind();",
        "requestedKind || draft.content_kind || contentStudioKindFromQuery()",
        ".filter((item) => item && typeof item === \"object\" && validContentBriefId(item.brief_id))",
        ".slice(0, 8)",
        "contentStudioEventLabel(item.action)",
        "item.revision",
        "item.created_at",
    ):
        assert token in surface
    assert "function contentStudioQueryKind()" in PORTAL
    for forbidden in ("item.content", "item.reference", "item.payload", "item.provider", "item.url"):
        assert forbidden not in surface


def test_content_operations_board_never_offers_a_dead_create_link() -> None:
    surface = board_surface()
    for token in (
        "function renderContentStudioKindBoard(canCreate)",
        "return canCreate",
        "portal-content-operations-kind-card--guarded",
        "const startAction = canCreate",
        "Chỉ có quyền xem",
        "Cần quyền tạo brief",
        "renderContentStudioKindBoard(canCreate)",
    ):
        assert token in surface
    assert "<a aria-disabled" not in surface


def test_new_authoring_uses_its_minimal_signed_reader_not_board_timeline() -> None:
    start = INTEGRATION.index("async function hydrateContentStudioAuthoring()")
    end = INTEGRATION.index("async function hydrateContentStudio(", start)
    authoring = INTEGRATION[start:end]
    for token in (
        'const route = "/content-studio/new";',
        "contentStudioAuthoringHydrationEpoch",
        'api("/content-studio/policy")',
        'api("/content-studio/references")',
        'contentStudioReadState: "ready"',
        'contentStudioReadState: "failed"',
        "contentStudioSummary: {}",
        "contentBriefs: []",
        "contentStudioEvents: []",
    ):
        assert token in authoring
    for forbidden in ("/content-studio/summary", "contentStudioListPath", "/content-studio/events"):
        assert forbidden not in authoring
    assert 'currentPath === "/content-studio/new") await hydrateContentStudioAuthoring();' in INTEGRATION
    refresh_start = INTEGRATION.index('if (action === "content-studio-refresh")')
    refresh_end = INTEGRATION.index('if (action === "content-brief-create")', refresh_start)
    assert 'route === "/content-studio/new") await hydrateContentStudioAuthoring();' in INTEGRATION[refresh_start:refresh_end]


def test_content_operations_board_preserves_existing_ephemeral_library_controls() -> None:
    surface = board_surface()
    for token in (
        'data-portal-no-transient data-portal-action="content-studio-filter"',
        'data-portal-action="content-studio-filter-clear"',
        "renderContentBriefCards(items)",
        "renderContentStudioPagination(listing)",
        "Bộ lọc chỉ tồn tại trong phiên trang hiện tại",
        "Owner-scoped library",
    ):
        assert token in surface


def test_content_operations_board_is_private_app_first_and_mobile_safe() -> None:
    private_prefixes = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/content-studio"' in private_prefixes
    assert '"/" + "api/v1/content-studio"' in private_prefixes
    assert '"/content-studio"' not in shell
    assert '"/api/v1/content-studio"' not in shell
    for token in (
        ".portal-content-operations-board",
        ".portal-content-studio-authoring",
        ".portal-content-operations-kind-card:focus-visible",
        ".portal-content-operations-kind-card--guarded",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
        "@media (max-width: 460px)",
        ".portal-content-operations-board .portal-content-studio-card:hover { transform: none; }",
    ):
        assert token in CSS
    board_css = CSS[CSS.index("/* Content Operations Board"):]
    assert "linear-gradient" not in board_css


def test_content_operations_contract_records_authority_and_non_goals() -> None:
    for token in (
        "`/content-studio`",
        "`/content-studio/new`",
        "`/content-studio/{uuid}`",
        "caption_hashtag",
        "GET /api/v1/content-studio/events?limit=50",
        "owner-scoped",
        "Bot parity",
        "PayOS",
        "44px",
        "No database table",
    ):
        assert token in CONTRACT
    assert "service worker" in CONTRACT.lower()
