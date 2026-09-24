"""Contract and Evidence Suite for SubDub Canonical Product Authority Reconciliation.

Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.SUBDUB.C1.INPUT.PRICING.EVIDENCE.AUTHORITY.TRUTH
Parent Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1

Enforces:
1. Exact Matrix row for SubDub: real_output=SRT_VTT_LOCAL_ONLY, status=PARTIAL, blocker=AI_DUBBING_BLOCKED_BY_RUNTIME.
2. 4 Bot canonical lanes: subtitle_create, subtitle_translate, dub, subtitle_plus_dub.
3. Current Web field sets: subtitleCreate, subtitleTranslate, dubbing.
4. /subdub Hub is presentation/navigation: fields=[], action='none' (no business input form).
5. /subdub Hub lacks explicit Combo launcher, BUT /dubbing form DOES contain subtitle_plus_dubbing.
6. Fictional /subtitle-studio workbench presence: -15 Xu fake action, fake download alerts.
7. Unsourced marketing claims: 99.5% ASR accuracy, Timeline Match.
8. Current Web SRT-only form restrictions (semantic gap on dubbing).
9. Bot canonical price keys (Xu/ký tự, Xu), derived formulas, and 0.5 Xu/word Auto scope.
10. Web 15/25/35 static rows are NOT canonical Bot pricing authority.
11. Strict separation of Web and Bot input/output authority contracts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

AUDIT_JSON_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.json"
AUDIT_MD_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.md"
MASTER_MATRIX_PATH = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
PORTAL_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal.js"
COPYFAST_REGISTRY_PATH = STANDALONE_ROOT / "copyfast_registry.py"


@pytest.fixture(scope="module")
def audit_data() -> dict:
    assert AUDIT_JSON_PATH.exists(), f"Missing audit artifact: {AUDIT_JSON_PATH}"
    data = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def master_matrix() -> dict:
    assert MASTER_MATRIX_PATH.exists(), f"Missing master matrix: {MASTER_MATRIX_PATH}"
    data = json.loads(MASTER_MATRIX_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def portal_js_source() -> str:
    assert PORTAL_JS_PATH.exists(), f"Missing portal.js: {PORTAL_JS_PATH}"
    return PORTAL_JS_PATH.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# A. CURRENT MATRIX SUBDUB ROW
# -----------------------------------------------------------------------------
def test_a_current_matrix_subdub_row(master_matrix: dict):
    """Prove Master Inventory subdub row states real_output=SRT_VTT_LOCAL_ONLY and status=PARTIAL."""
    parity_matrix = master_matrix.get("parity_matrix", [])
    subdub_rows = [c for c in parity_matrix if c.get("bot_capability") == "subdub_service"]
    assert len(subdub_rows) == 1, "Expected exactly 1 subdub_service row in master matrix parity_matrix"
    row = subdub_rows[0]
    assert row.get("real_output") == "SRT_VTT_LOCAL_ONLY"
    assert row.get("status") == "PARTIAL"
    assert row.get("blocker") == "AI_DUBBING_BLOCKED_BY_RUNTIME"
    assert row.get("bot_runtime_consumer") == "services.subtitle_dub_product_pipeline"


# -----------------------------------------------------------------------------
# B. 4 BOT CANONICAL LANES
# -----------------------------------------------------------------------------
def test_b_four_bot_canonical_lanes(audit_data: dict):
    """Prove Bot has exactly 4 canonical lanes."""
    lanes = audit_data.get("bot_canonical_lanes", [])
    assert len(lanes) == 4, f"Expected exactly 4 lanes, found {len(lanes)}"
    lane_modes = {lane["mode"] for lane in lanes}
    expected_modes = {"subtitle_create", "subtitle_translate", "dub", "subtitle_plus_dub"}
    assert lane_modes == expected_modes

    # If Bot repo is available on local disk, verify directly against bot.py source
    bot_candidates = [
        Path(os.environ.get("BOT_ROOT", "")),
        STANDALONE_ROOT.parent / "wt_tts_financial_safety_r1",
        STANDALONE_ROOT.parent / "bot telegram",
    ]
    for candidate in bot_candidates:
        bot_py = candidate / "bot.py"
        if bot_py.is_file():
            content = bot_py.read_text(encoding="utf-8", errors="ignore")
            assert 'VIDEO_SUBTITLE_MODE_CREATE = "subtitle_create"' in content
            assert 'VIDEO_SUBTITLE_MODE_TRANSLATE = "subtitle_translate"' in content
            assert 'VIDEO_SUBTITLE_MODE_DUB = "dub"' in content
            assert 'VIDEO_SUBTITLE_MODE_SUBTITLE_PLUS_DUB = "subtitle_plus_dub"' in content
            break


# -----------------------------------------------------------------------------
# C. CURRENT WEB FIELD SETS EXACTLY
# -----------------------------------------------------------------------------
def test_c_current_web_field_sets_exactly(portal_js_source: str):
    """Prove FIELD_SETS.subtitleCreate, subtitleTranslate, and dubbing field sets."""
    # subtitleCreate
    create_match = re.search(r"subtitleCreate:\s*\[(.*?)\]\s*,\s*\n\s*subtitleTranslate:", portal_js_source, re.DOTALL)
    assert create_match is not None, "Missing FIELD_SETS.subtitleCreate"
    create_block = create_match.group(1)
    assert 'name: "source"' in create_block
    assert 'name: "duration_seconds"' in create_block
    assert 'name: "output_format"' in create_block

    # subtitleTranslate
    trans_match = re.search(r"subtitleTranslate:\s*\[(.*?)\]\s*,\s*\n\s*dubbing:", portal_js_source, re.DOTALL)
    assert trans_match is not None, "Missing FIELD_SETS.subtitleTranslate"
    trans_block = trans_match.group(1)
    assert 'name: "source"' in trans_block
    assert 'name: "target_language"' in trans_block
    assert 'name: "duration_seconds"' in trans_block
    assert 'name: "output_format"' in trans_block

    # dubbing
    dub_match = re.search(r"dubbing:\s*\[(.*?)\n\s*\]\s*,\s*\n\s*(?://|documentPdf:)", portal_js_source, re.DOTALL)
    assert dub_match is not None, "Missing FIELD_SETS.dubbing"
    dub_block = dub_match.group(1)
    assert 'name: "source"' in dub_block
    assert 'name: "mode"' in dub_block
    assert 'name: "target_language"' in dub_block
    assert 'name: "voice_profile_id"' in dub_block
    assert 'name: "speed"' in dub_block
    assert 'name: "duration_seconds"' in dub_block
    assert 'name: "output_format"' in dub_block


# -----------------------------------------------------------------------------
# D. HUB HAS NO CANONICAL BUSINESS INPUT FORM
# -----------------------------------------------------------------------------
def test_d_subdub_hub_has_no_business_input_form(portal_js_source: str, audit_data: dict):
    """Prove /subdub Hub registration is presentation/navigation only (fields: [], action: 'none')."""
    assert audit_data["flags"]["SUBDUB_HUB_BUSINESS_INPUT_SURFACE"] == "NO"
    hub_page_match = re.search(
        r'customerPage\(\s*"/subdub",\s*"Sub & Dub Operations Hub",.*?layout:\s*"subdub-operations-hub",\s*type:\s*"subdub-operations-hub",\s*fields:\s*\[\],\s*action:\s*"none"',
        portal_js_source,
        re.DOTALL,
    )
    assert hub_page_match is not None, "Expected /subdub customerPage with fields: [] and action: 'none'"


# -----------------------------------------------------------------------------
# E & F. HUB LACKS COMBO LAUNCHER BUT DUBBING FORM HAS SUBTITLE_PLUS_DUBBING
# -----------------------------------------------------------------------------
def test_e_and_f_combo_differentiation(portal_js_source: str, audit_data: dict):
    """Prove /subdub Hub lacks an explicit Combo launcher, while the /dubbing form DOES contain subtitle_plus_dubbing."""
    assert audit_data["flags"]["HUB_COMBO_LAUNCHER_MISSING"] == "YES"
    assert audit_data["flags"]["WEB_DUBBING_FORM_COMBO_MODE_PRESENT"] == "YES"

    # Hub workflow items in renderSubDubHub
    subdub_hub_match = re.search(r"function renderSubDubHub\(page, context\)\s*\{(.*?)\n  \}", portal_js_source, re.DOTALL)
    assert subdub_hub_match is not None
    hub_body = subdub_hub_match.group(1)
    # The hub launchers only mention /subtitle/formats, /subtitle/assets, /subtitle-studio, /subtitle/create, /dubbing, /translate, /asr
    assert '"/subtitle/create"' in hub_body
    assert '"/dubbing"' in hub_body
    assert '"/translate"' in hub_body
    assert '"/asr"' in hub_body
    assert "subtitle_plus_dub" not in hub_body
    assert "subdub_combo" not in hub_body

    # The dubbing form contains subtitle_plus_dubbing in mode options
    assert 'options: ["dubbing", "subtitle_plus_dubbing"]' in portal_js_source


# -----------------------------------------------------------------------------
# G, H, I. FICTIONAL SUBTITLE-STUDIO WORKBENCH, -15 XU ACTION, FAKE DOWNLOADS
# -----------------------------------------------------------------------------
def test_g_h_i_fictional_subtitle_studio_workbench(portal_js_source: str, audit_data: dict):
    """Prove fictional /subtitle-studio workbench exists with fake alert actions."""
    assert audit_data["flags"]["FICTIONAL_SUBTITLE_STUDIO_WORKBENCH_PRESENT"] == "YES"
    assert audit_data["flags"]["FICTIONAL_UI_USED_AS_AUTHORITY"] == "NO"

    # G: Fictional workbench container
    assert "portal-interactive-subdub-workbench" in portal_js_source
    assert "🟢 Neural SubDub Engine Sẵn Sàng" in portal_js_source

    # H: Fake -15 Xu button with alert()
    assert "BẮT ĐẦU TẠO PHỤ ĐỀ & LỒNG TIẾNG AI (-15 Xu)" in portal_js_source
    assert "alert('Đã kích hoạt render SubDub AI! Video & Phụ đề đang được đồng bộ.')" in portal_js_source

    # I: Fake download buttons with alert()
    assert "alert('Đang tải file phụ đề .SRT')" in portal_js_source
    assert "alert('Đang tải video hoàn chỉnh đã lồng tiếng.')" in portal_js_source


# -----------------------------------------------------------------------------
# J & K. UNSOURCED 99.5% ASR AND TIMELINE MATCH CLAIMS
# -----------------------------------------------------------------------------
def test_j_and_k_unsourced_marketing_claims(portal_js_source: str, audit_data: dict):
    """Prove unbacked marketing claims are hardcoded in renderSubDubHub."""
    assert audit_data["flags"]["UNSOURCED_99_5_ASR_BADGE_PRESENT"] == "YES"
    assert audit_data["flags"]["UNSOURCED_TIMELINE_MATCH_BADGE_PRESENT"] == "YES"

    assert 'qualityBadge: "99.5%"' in portal_js_source
    assert 'qualityLabel: "Độ chính xác ASR"' in portal_js_source
    assert 'safetyBadge: "Timeline Match"' in portal_js_source
    assert 'safetyLabel: "Khớp thời gian hoàn hảo"' in portal_js_source


# -----------------------------------------------------------------------------
# L. CURRENT WEB SRT-ONLY FORM RESTRICTIONS (SEMANTIC GAPS)
# -----------------------------------------------------------------------------
def test_l_current_web_srt_only_form_restrictions(portal_js_source: str, audit_data: dict):
    """Prove subtitleCreate, subtitleTranslate, and dubbing all restrict output_format to ['srt']."""
    assert audit_data["flags"]["WEB_OUTPUT_FORM_VS_BOT_OUTPUT_GAPS_RESOLVED"] == "YES"

    # Each field set hardcodes output_format: options: ["srt"]
    field_sets_snippet = portal_js_source[portal_js_source.find("subtitleCreate:"):portal_js_source.find("documentPdf:")]
    srt_matches = re.findall(r'name:\s*"output_format",.*?options:\s*\["srt"\]', field_sets_snippet, re.DOTALL)
    assert len(srt_matches) == 3, f"Expected 3 occurrences of output_format: ['srt'], found {len(srt_matches)}"


# -----------------------------------------------------------------------------
# M. BOT CANONICAL PRICE KEYS, UNITS, AND DERIVED FORMULAS
# -----------------------------------------------------------------------------
def test_m_bot_canonical_price_keys_units_and_formulas(audit_data: dict):
    """Prove Bot canonical price keys, units, and derived formulas."""
    assert audit_data["flags"]["SUBDUB_PRICING_KEYS_RESOLVED"] == "YES"
    assert audit_data["flags"]["SUBDUB_PRICING_UNITS_RESOLVED"] == "YES"

    keys = audit_data["pricing_authority"]["bot_canonical_keys"]["keys"]
    assert "subtitle_translate_video" in keys
    assert "auto_subtitle_video" in keys
    assert "dub_video" in keys
    assert "subtitle_dub_video" in keys
    assert "auto_subtitle_then_dub" in keys

    assert keys["subtitle_translate_video"]["unit"] == "Xu/ký tự"
    assert keys["auto_subtitle_video"]["unit"] == "Xu"
    assert keys["dub_video"]["unit"] == "Xu/ký tự"
    assert keys["subtitle_dub_video"]["unit"] == "Xu/ký tự"
    assert keys["auto_subtitle_then_dub"]["unit"] == "Xu/ký tự"

    assert keys["subtitle_dub_video"]["derived"] is True
    assert keys["subtitle_dub_video"]["formula"] == "subtitle_translate_video + dub_video"
    assert keys["auto_subtitle_then_dub"]["derived"] is True
    assert keys["auto_subtitle_then_dub"]["formula"] == "auto_subtitle_video + dub_video"


# -----------------------------------------------------------------------------
# N. 0.5 XU/WORD AUTO SCOPE IS NOT GENERIC DUB PRICING
# -----------------------------------------------------------------------------
def test_n_subdub_auto_word_pricing_scope(audit_data: dict):
    """Prove 0.5 Xu/word is an Auto speaker casting component, NOT generic dubbing pricing."""
    assert audit_data["flags"]["SUBDUB_AUTO_WORD_PRICE_SCOPE_RESOLVED"] == "YES"
    auto_word = audit_data["pricing_authority"]["subdub_auto_word"]
    assert auto_word["rate"] == "0.5 Xu/word"
    assert auto_word["is_generic_dub_pricing"] is False


# -----------------------------------------------------------------------------
# O. WEB 15/25/35 STATIC ROWS ARE NOT CANONICAL BOT AUTHORITY
# -----------------------------------------------------------------------------
def test_o_web_static_display_rows_are_not_canonical_bot_authority(audit_data: dict, portal_js_source: str):
    """Prove Web 15, 25, 35 Xu/min rows in portal.js are static display values, not canonical Bot authority."""
    assert audit_data["flags"]["WEB_STATIC_SUBDUB_PRICE_IS_CANONICAL_AUTHORITY"] == "NO"
    web_catalog = audit_data["pricing_authority"]["web_static_display_catalog"]
    assert web_catalog["is_canonical_bot_authority"] is False

    # Check presence of static display rows in portal.js
    assert 'code: "subdub_subtitle"' in portal_js_source
    assert "15 Xu / phút (~1.500 đ)" in portal_js_source
    assert 'code: "subdub_dub"' in portal_js_source
    assert "25 Xu / phút (~2.500 đ)" in portal_js_source
    assert 'code: "subdub_combo"' in portal_js_source
    assert "35 Xu / phút (~3.500 đ)" in portal_js_source


# -----------------------------------------------------------------------------
# P. WEB AND BOT INPUT/OUTPUT CONTRACTS ARE SEPARATED
# -----------------------------------------------------------------------------
def test_p_web_and_bot_input_output_authority_separated(audit_data: dict):
    """Prove input and output authorities are strictly separated between Web and Bot."""
    assert audit_data["flags"]["WEB_AND_BOT_INPUT_AUTHORITY_SEPARATED"] == "YES"
    assert audit_data["flags"]["WEB_AND_BOT_OUTPUT_AUTHORITY_SEPARATED"] == "YES"
    assert audit_data["flags"]["WEB_KEEP_ORIGINAL_AUDIO_AUTHORITY"] == "NO"
    assert audit_data["flags"]["WEB_PROVIDER_VOICE_ID_AUTHORITY"] == "NO"
    assert audit_data["flags"]["WEB_REMOTE_MEDIA_URL_AUTHORITY"] == "NO"
    assert audit_data["flags"]["BOT_OUTPUT_CAPABILITY_RESOLVED"] == "YES"
    assert audit_data["flags"]["WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN"] == "NO"
    assert audit_data["flags"]["WEB_VOICE_PROFILE_AUTHORITY_RESOLVED"] == "YES"
    assert audit_data["flags"]["CLIENT_PROVIDER_VOICE_ID_AUTHORITY"] == "NO"
    assert audit_data["flags"]["BOT_VOICE_RESOLUTION_AUTHORITY_SEPARATE"] == "YES"
