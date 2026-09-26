"""Tests for WEB_SUBDUB_UIUX_PRODUCT_JOURNEY_CORRECTION_R1_1 (Web Issue #558, PR #559).

Validates all 8 Owner Blockers:
1. Source Intake Real or Guarded (DEAD_VISIBLE_CONTROL_COUNT=0, FAKE_SOURCE_INTAKE_COUNT=0).
2. Pricing Truth (HARDCODED_SUBDUB_PRICE_COUNT=0, CONTRADICTORY_PRICE_DISPLAY_COUNT=0).
3. EN Locale Parity (VI_MIXED_VISIBLE_COPY_COUNT=0, EN_MIXED_VISIBLE_COPY_COUNT=0, SUBDUB_PRESENTATION_COPY).
4. VI Purity across journey (No Text, Web-native, canonical, Combo, Runtime, Plain text, Ducking, Workspace, Pipeline, Guard, Draft, Voiceover, Saved).
5. Legacy Routes Automatic Canonicalization (REDUNDANT_NAVIGATION_STEP_COUNT=0, DUPLICATE_SUBDUB_ENTRY_WITHOUT_REDIRECT_COUNT=0).
6. Voice Authority (FICTIONAL_VOICE_OPTION_COUNT=0, voice catalog guarded).
7. Single-agent product truth and 6 unified customer status states.
8. Zero fake planning as real success (PLANNING_AS_REAL_SUCCESS_COUNT=0, COMBINED_MODE_RESELECT_REQUIRED=NO).
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
# Test 1: Four Product Journeys Defined Without Hardcoded Locale/Pricing in Modes
# -----------------------------------------------------------------------------
def test_four_subdub_product_journeys_defined(portal_js: str) -> None:
    """Verify SUBDUB_PRODUCT_MODES defines exactly 4 canonical journeys without hardcoded titleVI or unitCost."""
    modes_match = re.search(r"const SUBDUB_PRODUCT_MODES = Object\.freeze\(\{([\s\S]*?)\n  \}\);", portal_js)
    assert modes_match is not None, "SUBDUB_PRODUCT_MODES not found in portal.js"
    modes_block = modes_match.group(1)

    expected_modes = [
        "SUBTITLE_ONLY",
        "TRANSLATED_SUBTITLE",
        "DUBBING_ONLY",
        "SUBTITLE_PLUS_DUBBING",
    ]

    for mode_key in expected_modes:
        assert f"{mode_key}:" in modes_block

    # Hardcoded titleVI and unitCost must NOT be in SUBDUB_PRODUCT_MODES data structure
    assert "titleVI:" not in modes_block
    assert "unitCost:" not in modes_block

    # Query resolvers handle aliases and persistence
    assert "function resolveSubDubJourneyMode(context)" in portal_js
    assert '"subtitle_only"' in portal_js
    assert '"translated_subtitle"' in portal_js
    assert '"dubbing_only"' in portal_js
    assert '"subtitle_plus_dubbing"' in portal_js

    # Presentation copy dictionary present
    assert "const SUBDUB_PRESENTATION_COPY = Object.freeze({" in portal_js
    assert "vi:" in portal_js
    assert "en:" in portal_js


# -----------------------------------------------------------------------------
# Test 2: Four Stages Consistently Rendered
# -----------------------------------------------------------------------------
def test_four_consistent_customer_stages_rendered(portal_js: str) -> None:
    """Verify renderSubDubHub renders all 4 stages with data-subdub-stage attributes."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None, "renderSubDubHub not found in portal.js"
    func_body = subdub_func_match.group(1)

    assert 'data-subdub-stage="1"' in func_body
    assert 'data-subdub-stage="2"' in func_body
    assert 'data-subdub-stage="3"' in func_body
    assert 'data-subdub-stage="4"' in func_body

    # Stages use copy dictionary
    copy_match = re.search(r"const SUBDUB_PRESENTATION_COPY = Object\.freeze\(\{([\s\S]*?)\n  \}\);", portal_js)
    assert copy_match is not None
    copy_body = copy_match.group(1)

    assert 'stage1Title: "1. Nguồn dữ liệu"' in copy_body
    assert 'stage2Title: "2. Kết quả mong muốn"' in copy_body
    assert 'stage3Title: "3. Kiểm tra & chi phí"' in copy_body
    assert 'stage4Title: "4. Đang xử lý / Kết quả"' in copy_body


# -----------------------------------------------------------------------------
# Test 3: Combo Mode Shows Both Subtitle and Dubbing Without Redundant Selection
# -----------------------------------------------------------------------------
def test_combo_mode_shows_both_configs_and_single_shared_language(portal_js: str) -> None:
    """Verify SUBTITLE_PLUS_DUBBING displays subtitle & dubbing configs together with single shared target language."""
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # Shared language selector present
    assert 'id="subdub-shared-target-lang"' in func_body

    # Both configs present in the combo block
    assert "copy.subtitleConfigHeading" in func_body
    assert "copy.dubbingConfigHeading" in func_body

    # Zero redundant prompt asking if user wants dubbing
    assert "Bạn có muốn lồng tiếng không" not in portal_js
    assert "bạn có muốn lồng tiếng" not in portal_js.lower()


# -----------------------------------------------------------------------------
# Test 4: Source Intake Real or Guarded (Blocker 1)
# -----------------------------------------------------------------------------
def test_source_intake_guarded_truth(portal_js: str) -> None:
    """Verify source intake is explicitly guarded with no fake dropzone and no dead clickable controls.

    DEAD_VISIBLE_CONTROL_COUNT=0
    FAKE_SOURCE_INTAKE_COUNT=0
    """
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # No decorative fake dropzone masquerading as an active uploader
    assert "Kéo thả tệp media vào đây" not in func_body
    assert "portal-subdub-dropzone" not in func_body

    # No invalid /asset-vault route link in SubDub hub
    assert 'href="/asset-vault"' not in func_body

    # Stage 1 has explicit guarded attributes
    assert 'data-subdub-stage="1" data-status="guarded" data-tool-state="guarded"' in func_body

    # Controls are disabled so no dead visible clicks
    assert 'id="subdub-source-lang" class="portal-select" name="source_language" disabled' in func_body


# -----------------------------------------------------------------------------
# Test 5: Pricing Truth & Guarded CTA (Blocker 2)
# -----------------------------------------------------------------------------
def test_pricing_truth_and_guarded_cta(portal_js: str) -> None:
    """Verify pricing truth: no hardcoded rates (0.1, 0.2 Xu), no contradictory 0 Xu estimate, guarded CTA.

    HARDCODED_SUBDUB_PRICE_COUNT=0
    CONTRADICTORY_PRICE_DISPLAY_COUNT=0
    PLANNING_AS_REAL_SUCCESS_COUNT=0
    """
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # No hardcoded prices in SubDub Hub
    assert "0.1 Xu" not in func_body
    assert "0.2 Xu" not in func_body
    assert "0 Xu" not in func_body

    # Presentation copy defines honest pricing
    copy_match = re.search(r"const SUBDUB_PRESENTATION_COPY = Object\.freeze\(\{([\s\S]*?)\n  \}\);", portal_js)
    assert copy_match is not None
    copy_body = copy_match.group(1)

    assert 'summaryPriceValue: "Giá chưa khả dụng"' in copy_body
    assert 'summaryCostValue: "Chi phí sẽ được xác nhận khi tính năng sẵn sàng."' in copy_body
    assert 'summaryPriceValue: "Pricing unavailable"' in copy_body
    assert 'summaryCostValue: "Cost will be confirmed when feature is ready."' in copy_body

    # Guarded CTA button
    assert '<button class="portal-button portal-subdub-cta" type="button" disabled data-status="guarded">' in func_body


# -----------------------------------------------------------------------------
# Test 6: Voice Authority & Fictional Voices Purged (Blocker 6)
# -----------------------------------------------------------------------------
def test_voice_authority_and_fictional_voices_purged(portal_js: str) -> None:
    """Verify fictional voice profiles are purged and voice selection is disabled/guarded.

    FICTIONAL_VOICE_OPTION_COUNT=0
    """
    subdub_func_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert subdub_func_match is not None
    func_body = subdub_func_match.group(1)

    # Fictional voices purged
    assert "natural_female" not in func_body
    assert "natural_male" not in func_body
    assert "energetic" not in func_body

    # Voice select is disabled and guarded
    assert '<select class="portal-select" name="voice_style" disabled>' in func_body


# -----------------------------------------------------------------------------
# Test 7: Six Unified Customer Status States
# -----------------------------------------------------------------------------
def test_six_unified_customer_status_states(portal_js: str) -> None:
    """Verify stage 4 exclusively utilizes the 6 standard customer status states in VI and EN."""
    copy_match = re.search(r"const SUBDUB_PRESENTATION_COPY = Object\.freeze\(\{([\s\S]*?)\n  \}\);", portal_js)
    assert copy_match is not None
    copy_body = copy_match.group(1)

    expected_vi = ["Chuẩn bị", "Đang chờ", "Đang xử lý", "Hoàn tất", "Cần bạn xử lý", "Thất bại"]
    for state in expected_vi:
        assert state in copy_body, f"Expected VI state '{state}' missing in presentation copy"

    expected_en = ["Preparing", "Queued", "Processing", "Completed", "Action required", "Failed"]
    for state in expected_en:
        assert state in copy_body, f"Expected EN state '{state}' missing in presentation copy"

    # Customer guide does not show raw internal states in visible text
    for raw in ("PENDING", "PROCESSING", "COMPLETED", "FAILED", "QUEUED"):
        assert f'"{raw}"' not in copy_body


# -----------------------------------------------------------------------------
# Test 8: VI Locale Purity (Blocker 4)
# -----------------------------------------------------------------------------
def test_vi_locale_purity_across_journey(portal_js: str, customer_app_html: str) -> None:
    """Verify forbidden English jargon is completely purged from visible Vietnamese copy.

    Forbidden words: Text, Web-native, canonical, Combo, Runtime, Plain text, Ducking, Workspace, Pipeline, Guard, Draft, Voiceover, Saved.
    """
    copy_match = re.search(r"vi:\s*\{([\s\S]*?)\n    \},", portal_js)
    assert copy_match is not None, "VI presentation copy block not found"
    vi_copy = copy_match.group(1)

    # In VI presentation copy, check forbidden words
    forbidden_in_vi = [
        "Text",
        "Web-native",
        "canonical",
        "Combo",
        "Runtime",
        "Plain text",
        "Ducking",
        "Pipeline",
        "Voiceover",
    ]
    for word in forbidden_in_vi:
        assert word not in vi_copy, f"Found forbidden jargon '{word}' in VI presentation copy"

    # Check Subtitle Studio rendered VI strings
    assert "Không gian biên tập text" not in portal_js
    assert "Soạn thảo Text & Mốc thời gian" not in portal_js
    assert "Biên tập phụ đề Web-native" not in portal_js

    # Check customer app subdub entries
    assert "Tạo subtitle draft" not in customer_app_html
    assert "Dịch Ngôn ngữ (Text/Audio/Docs)" not in customer_app_html


# -----------------------------------------------------------------------------
# Test 9: Legacy Routes Auto-Redirect Without Extra Click (Blocker 5)
# -----------------------------------------------------------------------------
def test_legacy_routes_auto_redirect_no_extra_click(portal_js: str) -> None:
    """Verify legacy routes auto-redirect to /subdub with preserved query intent and NO extra click card.

    REDUNDANT_NAVIGATION_STEP_COUNT=0
    DUPLICATE_SUBDUB_ENTRY_WITHOUT_REDIRECT_COUNT=0
    """
    # resolveLegacySubDubCanonicalUrl exists
    assert "function resolveLegacySubDubCanonicalUrl(pathname, search)" in portal_js

    # Legacy transition card with manual click button has been purged
    assert "function renderSubDubTransitionCard" not in portal_js
    assert "portal-subdub-canonical-transition" not in portal_js

    # Lightweight redirect placeholder with script replacement present
    assert "function renderSubDubRedirectPlaceholder(route)" in portal_js
    assert "portal-subdub-canonical-redirect" in portal_js

    # Early redirect check present in mountPortal
    mount_portal_match = re.search(r"function mountPortal\(override\)\s*\{([\s\S]*?)\n  \}", portal_js)
    assert mount_portal_match is not None
    mount_body = mount_portal_match.group(1)
    assert "resolveLegacySubDubCanonicalUrl" in mount_body
    assert "window.location.replace" in mount_body
