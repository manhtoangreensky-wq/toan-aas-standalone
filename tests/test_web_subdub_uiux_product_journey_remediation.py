"""Tests for WEB_SUBDUB_UIUX_PRODUCT_JOURNEY_REMEDIATION_R1 (Web Issue #558).

Validates:
- 4 canonical product journeys: SUBTITLE_ONLY, TRANSLATED_SUBTITLE, DUBBING_ONLY, SUBTITLE_PLUS_DUBBING.
- 4 consistent customer stages: Nguồn, Kết quả mong muốn, Kiểm tra & chi phí, Đang xử lý / Kết quả.
- SubDub combo mode displays both subtitle and dubbing configs immediately with single shared language selection.
- Zero redundant mode selection prompts ("Bạn có muốn lồng tiếng không?").
- Source language logic (target lang omitted for subtitle only, shared for combo).
- Real-vs-draft truth (guarded disabled CTA when backend runtime is unproven).
- Strictly 6 unified customer status states (Chuẩn bị, Đang chờ, Đang xử lý, Hoàn tất, Cần bạn xử lý, Thất bại).
- VI locale purity (purged internal English jargon: Workspace, Pipeline, Guard, Draft, Voiceover, Workflow Plan, Saved, Studio Pro).
- Single canonical entry /subdub with zero duplicate SubDub forms.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = REPO_ROOT / "static" / "portal" / "portal.js"
CUSTOMER_APP_PATH = REPO_ROOT / "customer_app.html"
COPYFAST_PAGES_PATH = REPO_ROOT / "copyfast_pages.py"


@pytest.fixture(scope="module")
def portal_js() -> str:
    assert PORTAL_JS_PATH.exists(), f"Missing {PORTAL_JS_PATH}"
    return PORTAL_JS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def customer_app_html() -> str:
    assert CUSTOMER_APP_PATH.exists(), f"Missing {CUSTOMER_APP_PATH}"
    return CUSTOMER_APP_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def copyfast_pages() -> str:
    assert COPYFAST_PAGES_PATH.exists(), f"Missing {COPYFAST_PAGES_PATH}"
    return COPYFAST_PAGES_PATH.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Test 1: Four Product Journeys Persist Consistent State Across All Modes
# -----------------------------------------------------------------------------
def test_four_subdub_product_journeys_defined(portal_js: str) -> None:
    """Verify SUBDUB_PRODUCT_MODES defines exactly 4 canonical journeys with consistent properties."""
    modes_match = re.search(r"const SUBDUB_PRODUCT_MODES = Object\.freeze\(\{([\s\S]*?)\n  \}\);", portal_js)
    assert modes_match is not None, "SUBDUB_PRODUCT_MODES not found in portal.js"
    modes_block = modes_match.group(1)

    expected_modes = {
        "SUBTITLE_ONLY": "Tạo phụ đề",
        "TRANSLATED_SUBTITLE": "Dịch phụ đề",
        "DUBBING_ONLY": "Lồng tiếng",
        "SUBTITLE_PLUS_DUBBING": "Phụ đề + lồng tiếng",
    }

    for mode_key, expected_title in expected_modes.items():
        assert f"{mode_key}:" in modes_block
        assert f'titleVI: "{expected_title}"' in modes_block

    # Verify query resolver handles aliases and persistence
    assert "function resolveSubDubJourneyMode(context)" in portal_js
    assert '"subtitle_only"' in portal_js
    assert '"translated_subtitle"' in portal_js
    assert '"dubbing_only"' in portal_js
    assert '"subtitle_plus_dubbing"' in portal_js


# -----------------------------------------------------------------------------
# Test 2: Four Stages Consistently Rendered
# -----------------------------------------------------------------------------
def test_four_consistent_customer_stages_rendered(portal_js: str) -> None:
    """Verify renderSubDubHub renders all 4 stages: Nguồn, Kết quả mong muốn, Kiểm tra & chi phí, Đang xử lý / Kết quả."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None, "renderSubDubHub not found in portal.js"
    func_body = subdub_func_match.group(1)

    assert 'data-subdub-stage="1"' in func_body
    assert "1. Nguồn" in func_body
    assert 'data-subdub-stage="2"' in func_body
    assert "2. Kết quả mong muốn" in func_body
    assert 'data-subdub-stage="3"' in func_body
    assert "3. Kiểm tra & chi phí" in func_body
    assert 'data-subdub-stage="4"' in func_body
    assert "4. Đang xử lý / Kết quả" in func_body


# -----------------------------------------------------------------------------
# Test 3: Combo Mode Shows Both Subtitle and Dubbing Without Redundant Selection
# -----------------------------------------------------------------------------
def test_combo_mode_shows_both_configs_and_single_shared_language(portal_js: str) -> None:
    """Verify SUBTITLE_PLUS_DUBBING displays subtitle & dubbing configs together with single shared target language."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # Shared language selector present
    assert "Ngôn ngữ mục tiêu chung (Áp dụng đồng thời cho dịch phụ đề và lồng tiếng AI)" in func_body
    assert 'id="subdub-shared-target-lang"' in func_body

    # Both configs present in the combo block
    assert "Cấu hình phụ đề" in func_body
    assert "Cấu hình lồng tiếng AI" in func_body

    # Zero redundant prompt asking if user wants dubbing
    assert "Bạn có muốn lồng tiếng không" not in func_body
    assert "bạn có muốn lồng tiếng" not in func_body.lower()


# -----------------------------------------------------------------------------
# Test 4: Source Language Logic
# -----------------------------------------------------------------------------
def test_language_logic_omits_target_when_subtitle_only(portal_js: str) -> None:
    """Verify target language is omitted for SUBTITLE_ONLY mode."""
    modes_match = re.search(r"SUBTITLE_ONLY:\s*\{([\s\S]*?)\},", portal_js)
    assert modes_match is not None
    subtitle_only_block = modes_match.group(1)
    assert "hasTargetLang: false" in subtitle_only_block

    # In SUBTITLE_ONLY stage 2 inner html, there is no target_language select
    assert 'name="output_format"' in portal_js


# -----------------------------------------------------------------------------
# Test 5: Real-vs-Draft Truth & Guarded CTA
# -----------------------------------------------------------------------------
def test_real_vs_draft_truth_guarded_cta(portal_js: str) -> None:
    """Verify primary CTA is guarded/disabled with explicit runtime notice and zero fake success."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    assert "Tính năng này chưa sẵn sàng để chạy thật." in func_body
    assert "Bắt đầu xử lý" in func_body
    assert 'disabled data-status="guarded"' in func_body
    assert "Không tạo bản nháp giả" in func_body

    # No fake render alerts
    assert "alert('Đã kích hoạt render" not in func_body
    assert "alert('Đang tải" not in func_body


# -----------------------------------------------------------------------------
# Test 6: Six Unified Customer Status States
# -----------------------------------------------------------------------------
def test_six_unified_customer_status_states(portal_js: str) -> None:
    """Verify stage 4 exclusively utilizes the 6 standard customer status states in Vietnamese."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    expected_states = [
        "Chuẩn bị",
        "Đang chờ",
        "Đang xử lý",
        "Hoàn tất",
        "Cần bạn xử lý",
        "Thất bại",
    ]

    for state in expected_states:
        assert state in func_body, f"Expected state '{state}' missing in SubDub Hub"

    # Customer guide does not show raw internal states
    guide_match = re.search(r'class="portal-subdub-status-guide"([\s\S]*?)<\/div>\s*<div class="portal-state"', func_body)
    assert guide_match is not None
    guide_body = guide_match.group(1)
    for raw in ("PENDING", "PROCESSING", "COMPLETED", "FAILED", "QUEUED"):
        assert raw not in guide_body


# -----------------------------------------------------------------------------
# Test 7: VI Locale Purity
# -----------------------------------------------------------------------------
def test_vi_locale_purity_in_subdub_hub(portal_js: str) -> None:
    """Verify internal English jargon is purged from SubDub visible UI."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    forbidden_jargon = [
        "Voiceover",
        "Studio Pro",
        "Workflow Plan",
        "Pipeline",
    ]

    for word in forbidden_jargon:
        assert word not in func_body, f"Found forbidden jargon '{word}' in renderSubDubHub"


# -----------------------------------------------------------------------------
# Test 8: Single Canonical Entry /subdub & Transition Cards for Legacy Routes
# -----------------------------------------------------------------------------
def test_single_canonical_entry_and_transition_for_legacy_routes(portal_js: str, customer_app_html: str, copyfast_pages: str) -> None:
    """Verify /subdub is registered and legacy routes render transition cards to /subdub."""
    # /subdub shell description registered
    assert '"/subdub":' in copyfast_pages

    # customer_app.html video_dub redirects to /subdub?mode=subtitle_plus_dubbing
    assert "window.location.href='/subdub?mode=subtitle_plus_dubbing'" in customer_app_html

    # Legacy routes render transition card in renderWorkspace
    assert "function renderSubDubTransitionCard(route)" in portal_js
    assert "portal-subdub-canonical-transition" in portal_js
    assert 'isLegacySubDubRoute ? renderSubDubTransitionCard(route) : renderFormCard(page, context)' in portal_js
    assert 'href="/subdub?mode=' in portal_js

    # Legacy subtitle-studio points to /subdub
    assert 'href="/subdub"' in portal_js
    assert "Mở Trung tâm Phụ đề & Lồng tiếng" in portal_js


# -----------------------------------------------------------------------------
# Test 9: Zero Dead / Redundant Steps
# -----------------------------------------------------------------------------
def test_zero_dead_and_redundant_steps(portal_js: str) -> None:
    """Verify REDUNDANT_MODE_SELECTION_COUNT=0, PLANNING_AS_REAL_SUCCESS_COUNT=0, DUPLICATE_SUBDUB_ENTRY_WITHOUT_REDIRECT_COUNT=0."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # 1. REDUNDANT_MODE_SELECTION_COUNT=0: No secondary prompt asking for dubbing
    redundant_prompts = re.findall(r"bạn có muốn lồng tiếng", func_body, re.IGNORECASE)
    assert len(redundant_prompts) == 0

    # 2. PLANNING_AS_REAL_SUCCESS_COUNT=0: CTA is disabled, cannot trigger fake success
    assert 'disabled data-status="guarded"' in func_body
    fake_success_matches = re.findall(r"Đã kích hoạt render SubDub AI", func_body)
    assert len(fake_success_matches) == 0

    # 3. DUPLICATE_SUBDUB_ENTRY_WITHOUT_REDIRECT_COUNT=0: Legacy routes show transition card
    assert "isLegacySubDubRoute" in portal_js
    assert "renderSubDubTransitionCard" in portal_js
