"""Test suite for P0.WEBAPP.V3.CUSTOMER.TRUTHFUL_UX_BOUNDARY.DIFFERENTIATION.R1.

Verifies:
1. Truthful boundary classification in portal.js (canonical_bridge, web_planning, runtime_generator).
2. Honest status badges in pageStatusBadge for all boundary types.
3. Boundary notice banner in renderFormCard with zero false execution promises.
4. Catalogue boundary signals and keywords in portal-features.js under 500 lines.
5. Strict preservation of safety contracts and invariants.
6. Audit Gap Matrix reconciliation: ux_gaps = 0.
7. Visual boundary styles in portal.css.
"""

from pathlib import Path
import json
import pytest

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PORTAL_FEATURES_JS = (ROOT / "static" / "portal" / "portal-features.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
AUDIT_JSON_PATH = ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
AUDIT_MD_PATH = ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"


def test_01_portal_js_boundary_classification_logic() -> None:
    """Verify classifyPageBoundary classifies routes accurately."""
    assert "function classifyPageBoundary(page, context)" in PORTAL_JS
    assert '"canonical_bridge"' in PORTAL_JS
    assert '"web_planning"' in PORTAL_JS
    assert '"runtime_generator"' in PORTAL_JS

    # Canonical bridge markers
    assert 'feature === "video_ai_prompt"' in PORTAL_JS
    assert 'route === "/video/create"' in PORTAL_JS

    # Web planning markers
    assert '"campaign_planner"' in PORTAL_JS
    assert '"prompt_studio"' in PORTAL_JS
    assert '"content_studio"' in PORTAL_JS
    assert 'route.startsWith("/video-studio/")' in PORTAL_JS

    # Runtime generator markers
    assert '"video_trend"' in PORTAL_JS
    assert '"video_long"' in PORTAL_JS
    assert '"voice_tts"' in PORTAL_JS
    assert '"voice_clone"' in PORTAL_JS
    assert '"music_background"' in PORTAL_JS


def test_02_portal_js_page_status_badge() -> None:
    """Verify pageStatusBadge provides truthful visual badges without claiming fake readiness."""
    assert "function pageStatusBadge(page, context)" in PORTAL_JS
    assert 'data-boundary="canonical_bridge"' in PORTAL_JS
    assert 'Job Bridge Sẵn sàng' in PORTAL_JS
    assert 'data-boundary="web_planning"' in PORTAL_JS
    assert 'Kế hoạch &amp; Bản nháp Web' in PORTAL_JS
    assert 'data-boundary="runtime_generator"' in PORTAL_JS
    assert 'Bộ tạo AI (Chờ Adapter)' in PORTAL_JS


def test_03_portal_js_render_form_card_boundary_notice() -> None:
    """Verify renderFormCard renders a clear boundary notice banner."""
    form_card_fn = PORTAL_JS[
        PORTAL_JS.index("function renderFormCard(page, context)"):
        PORTAL_JS.index("const ADMIN_TAB_GROUPS")
    ]
    assert "portal-notice--boundary" in form_card_fn
    assert 'data-ux-boundary="canonical_bridge"' in form_card_fn
    assert 'data-ux-boundary="web_planning"' in form_card_fn
    assert 'data-ux-boundary="runtime_generator"' in form_card_fn
    assert "Cầu nối Job Canonical" in form_card_fn
    assert "Không gian Kế hoạch Web" in form_card_fn
    assert "Bộ tạo AI (Chế độ An toàn)" in form_card_fn
    assert "Thông số của bạn được lưu thành Bản nháp Web an toàn mà không trừ Xu." in form_card_fn


def test_04_portal_safety_contracts_preserved() -> None:
    """Verify all existing safety contracts in renderFormCard remain untouched."""
    form_card_fn = PORTAL_JS[
        PORTAL_JS.index("function renderFormCard(page, context)"):
        PORTAL_JS.index("const ADMIN_TAB_GROUPS")
    ]
    assert "workspaceDraftEnabled" in form_card_fn
    assert "workspaceDraftSupported" in form_card_fn
    assert "context.workspaceDraftFeatures.includes(feature)" in form_card_fn
    assert "workspaceDraftIdForRoute(route)" in form_card_fn
    assert "workspace-draft-update" in form_card_fn
    assert "Lưu thành bản mới" in form_card_fn
    assert "formFieldsEnabled" in form_card_fn
    assert "const localAuthoringOnly = !enabled && workspaceDraftEnabled;" in form_card_fn
    assert "const formAction = localAuthoringOnly ? localDraftAction : page.action;" in form_card_fn
    assert 'data-portal-action="${safeText(formAction)}"' in form_card_fn
    assert "primaryActionLabel = localAuthoringOnly ? localDraftLabel" in form_card_fn
    assert "Bản nháp chỉ giữ brief scalar trên Web" in form_card_fn


def test_05_portal_features_js_boundary_signals_and_search() -> None:
    """Verify portal-features.js tags catalog cards with boundary signals and search keywords."""
    assert "function classifyCatalogBoundary(feature)" in PORTAL_FEATURES_JS
    assert 'data-boundary' in PORTAL_FEATURES_JS
    assert "Job Bridge" in PORTAL_FEATURES_JS
    assert "Kế hoạch Web" in PORTAL_FEATURES_JS
    assert "Bộ tạo AI" in PORTAL_FEATURES_JS
    assert "job bridge canonical thực thi trực tiếp" in PORTAL_FEATURES_JS
    assert "kế hoạch workspace bản nháp draft web planning" in PORTAL_FEATURES_JS
    assert "bộ tạo ai bot generator runtime" in PORTAL_FEATURES_JS

    # Ensure size and safety invariants in portal-features.js
    assert len(PORTAL_FEATURES_JS.splitlines()) <= 500
    for forbidden in (
        "/core/status", "/auth/providers", "telegram", "/wallet", "payos", "provider",
        "localStorage", "sessionStorage", "innerHTML", "startViewTransition",
    ):
        assert forbidden not in PORTAL_FEATURES_JS.lower()


def test_06_portal_css_boundary_styling() -> None:
    """Verify portal.css defines distinct visual styling for boundary notices and badges."""
    assert ".portal-notice--boundary" in PORTAL_CSS
    assert '.portal-notice--boundary[data-ux-boundary="canonical_bridge"]' in PORTAL_CSS
    assert '.portal-notice--boundary[data-ux-boundary="web_planning"]' in PORTAL_CSS
    assert '.portal-notice--boundary[data-ux-boundary="runtime_generator"]' in PORTAL_CSS
    assert '.portal-badge[data-boundary="canonical_bridge"]' in PORTAL_CSS
    assert '.portal-badge[data-boundary="web_planning"]' in PORTAL_CSS
    assert '.portal-badge[data-boundary="runtime_generator"]' in PORTAL_CSS


def test_07_audit_gap_metrics_ux_gap_reconciled() -> None:
    """Verify audit gap metrics record ux_gaps = 0 in both JSON and Markdown."""
    audit_data = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    assert audit_data["gap_metrics"]["ux_gaps"] == 0

    md_content = AUDIT_MD_PATH.read_text(encoding="utf-8")
    assert "| `UX_GAPS` | **0** |" in md_content
    assert "UX_GAPS = 0" in md_content
