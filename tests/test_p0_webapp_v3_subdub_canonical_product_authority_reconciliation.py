"""Contract and Evidence Suite for SubDub Canonical Product Authority Reconciliation.

Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.SUBDUB.C3.UPLOAD.INPUT.RUNTIME.AUTHORITY.TRUTH
Parent Task: P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1

Enforces:
1. Exact Matrix row for SubDub: real_output=SRT_VTT_LOCAL_ONLY, status=PARTIAL, blocker=AI_DUBBING_BLOCKED_BY_RUNTIME.
2. Mandatory Bot Git Fixture at pinned SHA 661c0de773a68177f5c258843485a0177eb6b6e2 (fails if absent).
3. 4 Bot canonical lanes asserted directly from bot.py and blackboxes at pinned SHA.
4. Exact Web field sets asserted with complete specifications (types, accepts, min/max/step, options).
5. /subdub Hub is presentation/navigation: fields=[], action='none' (no business input form).
6. /subdub Hub lacks explicit Combo launcher, BUT /dubbing form DOES contain subtitle_plus_dubbing.
7. Fictional /subtitle-studio workbench presence: -15 Xu fake action, fake download alerts.
8. Unsourced marketing claims: 99.5% ASR accuracy, Timeline Match.
9. Current Web SRT-only form restrictions (semantic gap on dubbing).
10. Bot canonical price keys (Xu/ký tự, Xu), derived formulas, and defaults directly from bot.py.
11. 0.5 Xu/word Auto scope asserted directly from services/subdub_auto_word_pricing.py.
12. Default output types and fail-closed logic asserted directly from services/subtitle_dub_product_pipeline.py.
13. Web 15/25/35 static rows are NOT canonical Bot pricing authority.
14. Strict separation of Web and Bot input/output authority contracts.
15. SubDub i18n locale key count parity (79 VI, 79 EN) and zero placeholder corruption.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

AUDIT_JSON_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.json"
AUDIT_MD_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.md"
MASTER_MATRIX_PATH = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
PORTAL_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal.js"
PORTAL_I18N_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal-i18n.js"

BOT_AUTHORITY_COMMIT = "661c0de773a68177f5c258843485a0177eb6b6e2"


@pytest.fixture(scope="session")
def bot_git_repo() -> Path:
    """Resolve and verify Bot authority git repository at pinned commit SHA.

    Must fail closed if the pinned commit cannot be verified in the git object database.
    """
    candidates = [
        Path(os.environ.get("TOAN_AAS_BOT_REPO_ROOT", "")),
        Path(os.environ.get("BOT_ROOT", "")),
        STANDALONE_ROOT.parent / "wt_tts_financial_safety_r1",
        STANDALONE_ROOT.parent / "bot telegram",
        STANDALONE_ROOT.parent / "bot",
        STANDALONE_ROOT.parents[1] / "wt_tts_financial_safety_r1",
        STANDALONE_ROOT.parents[1] / "bot telegram",
        STANDALONE_ROOT.parents[1] / "bot",
    ]
    verified_repo: Path | None = None
    for candidate in candidates:
        if not candidate or not candidate.is_dir():
            continue
        try:
            res = subprocess.run(
                ["git", "-C", str(candidate), "cat-file", "-e", f"{BOT_AUTHORITY_COMMIT}^{{commit}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                verified_repo = candidate
                break
        except Exception:
            continue

    if verified_repo is None:
        pytest.fail(
            f"Bot authority repo at pinned SHA {BOT_AUTHORITY_COMMIT} is REQUIRED for this suite. "
            f"Candidates searched: {[str(c) for c in candidates if c]}"
        )
    return verified_repo


def read_bot_git_file(repo: Path, file_path: str) -> str:
    """Read file content directly from pinned Bot git commit."""
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{BOT_AUTHORITY_COMMIT}:{file_path}"],
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to read {file_path} from Bot git commit {BOT_AUTHORITY_COMMIT}: {e}")


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


@pytest.fixture(scope="module")
def portal_i18n_source() -> str:
    assert PORTAL_I18N_JS_PATH.exists(), f"Missing portal-i18n.js: {PORTAL_I18N_JS_PATH}"
    return PORTAL_I18N_JS_PATH.read_text(encoding="utf-8")


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
# B. 4 BOT CANONICAL LANES (DIRECT BOT GIT ASSERTION)
# -----------------------------------------------------------------------------
def test_b_four_bot_canonical_lanes(bot_git_repo: Path, audit_data: dict):
    """Prove Bot has exactly 4 canonical lanes directly from bot.py and blackboxes at pinned SHA."""
    bot_py = read_bot_git_file(bot_git_repo, "bot.py")
    assert 'VIDEO_SUBTITLE_MODE_CREATE = "subtitle_create"' in bot_py
    assert 'VIDEO_SUBTITLE_MODE_TRANSLATE = "subtitle_translate"' in bot_py
    assert 'VIDEO_SUBTITLE_MODE_DUB = "dub"' in bot_py
    assert 'VIDEO_SUBTITLE_MODE_SUBTITLE_PLUS_DUB = "subtitle_plus_dub"' in bot_py

    base_py = read_bot_git_file(bot_git_repo, "services/subdub_blackboxes/base.py")
    assert '_COMBO_MODE = "subtitle_plus_dub"' in base_py
    assert '"subtitle_create":' in base_py
    assert '"subtitle_translate":' in base_py
    assert '"dub":' in base_py

    # Cross-verify audit data matches source truth
    lanes = audit_data.get("bot_canonical_lanes", [])
    assert len(lanes) == 4, f"Expected exactly 4 lanes, found {len(lanes)}"
    lane_modes = {lane["mode"] for lane in lanes}
    expected_modes = {"subtitle_create", "subtitle_translate", "dub", "subtitle_plus_dub"}
    assert lane_modes == expected_modes


# -----------------------------------------------------------------------------
# C. CURRENT WEB FIELD SETS EXACTLY (FULL SPECIFICATION)
# -----------------------------------------------------------------------------
def test_c_current_web_field_sets_exactly(portal_js_source: str):
    """Prove FIELD_SETS.subtitleCreate, subtitleTranslate, and dubbing full specifications."""
    # subtitleCreate
    create_match = re.search(r"subtitleCreate:\s*\[(.*?)\]\s*,\s*\n\s*subtitleTranslate:", portal_js_source, re.DOTALL)
    assert create_match is not None, "Missing FIELD_SETS.subtitleCreate"
    create_block = create_match.group(1)
    assert 'name: "source"' in create_block
    assert 'type: "file"' in create_block
    assert 'accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm"' in create_block
    assert 'requiredUpload: true' in create_block
    assert 'name: "duration_seconds"' in create_block
    assert 'type: "number"' in create_block
    assert 'min: 1' in create_block
    assert 'max: 14_400' in create_block
    assert 'step: 1' in create_block
    assert 'required: true' in create_block
    assert 'name: "output_format"' in create_block
    assert 'control: "select"' in create_block
    assert 'options: ["srt"]' in create_block

    # subtitleTranslate
    trans_match = re.search(r"subtitleTranslate:\s*\[(.*?)\]\s*,\s*\n\s*dubbing:", portal_js_source, re.DOTALL)
    assert trans_match is not None, "Missing FIELD_SETS.subtitleTranslate"
    trans_block = trans_match.group(1)
    assert 'name: "source"' in trans_block
    assert 'type: "file"' in trans_block
    assert 'accept: ".srt,.vtt,.txt,text/plain,text/vtt,application/x-subrip,audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm"' in trans_block
    assert 'requiredUpload: true' in trans_block
    assert 'name: "target_language"' in trans_block
    assert 'control: "select"' in trans_block
    assert 'options: LANGUAGE_OPTIONS' in trans_block
    assert 'required: true' in trans_block
    assert 'name: "duration_seconds"' in trans_block
    assert 'type: "number"' in trans_block
    assert 'min: 1' in trans_block
    assert 'max: 14_400' in trans_block
    assert 'step: 1' in trans_block
    assert 'required: true' in trans_block
    assert 'name: "output_format"' in trans_block
    assert 'control: "select"' in trans_block
    assert 'options: ["srt"]' in trans_block

    # dubbing
    dub_match = re.search(r"dubbing:\s*\[(.*?)\n\s*\]\s*,\s*\n\s*(?://|documentPdf:)", portal_js_source, re.DOTALL)
    assert dub_match is not None, "Missing FIELD_SETS.dubbing"
    dub_block = dub_match.group(1)
    assert 'name: "source"' in dub_block
    assert 'type: "file"' in dub_block
    assert 'accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm"' in dub_block
    assert 'requiredUpload: true' in dub_block
    assert 'name: "mode"' in dub_block
    assert 'control: "select"' in dub_block
    assert 'options: ["dubbing", "subtitle_plus_dubbing"]' in dub_block
    assert 'name: "target_language"' in dub_block
    assert 'control: "select"' in dub_block
    assert 'options: LANGUAGE_OPTIONS' in dub_block
    assert 'required: true' in dub_block
    assert 'name: "voice_profile_id"' in dub_block
    assert 'control: "select"' in dub_block
    assert 'optionsFrom: "voiceProfiles"' in dub_block
    assert 'name: "speed"' in dub_block
    assert 'control: "select"' in dub_block
    assert '{ value: "1.0", label: "Bình thường (1.0×)" }' in dub_block
    assert '{ value: "0.9", label: "Chậm (0.9×)" }' in dub_block
    assert '{ value: "1.5", label: "Nhanh (1.5×)" }' in dub_block
    assert 'name: "duration_seconds"' in dub_block
    assert 'type: "number"' in dub_block
    assert 'min: 1' in dub_block
    assert 'max: 14_400' in dub_block
    assert 'step: 1' in dub_block
    assert 'required: true' in dub_block
    assert 'name: "output_format"' in dub_block
    assert 'control: "select"' in dub_block
    assert 'options: ["srt"]' in dub_block


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
# M. BOT CANONICAL PRICE KEYS, UNITS, AND DERIVED FORMULAS (DIRECT BOT GIT ASSERTION)
# -----------------------------------------------------------------------------
def test_m_bot_canonical_price_keys_units_and_formulas(bot_git_repo: Path, audit_data: dict):
    """Prove Bot canonical price keys, units, and derived formulas directly from bot.py source."""
    bot_py = read_bot_git_file(bot_git_repo, "bot.py")

    # Assert CANONICAL_PRICE_KEYS contains all 5 SubDub keys
    assert '"subtitle_translate_video"' in bot_py
    assert '"auto_subtitle_video"' in bot_py
    assert '"dub_video"' in bot_py
    assert '"subtitle_dub_video"' in bot_py
    assert '"auto_subtitle_then_dub"' in bot_py

    # Assert CANONICAL_PRICE_UNITS
    assert '"subtitle_translate_video": "Xu/ký tự"' in bot_py
    assert '"auto_subtitle_video": "Xu"' in bot_py
    assert '"dub_video": "Xu/ký tự"' in bot_py
    assert '"subtitle_dub_video": "Xu/ký tự"' in bot_py
    assert '"auto_subtitle_then_dub": "Xu/ký tự"' in bot_py

    # Assert CANONICAL_DERIVED_PRICE_KEYS and FORMULAS
    assert 'CANONICAL_DERIVED_PRICE_KEYS = {"subtitle_dub_video", "auto_subtitle_then_dub"}' in bot_py
    assert '"subtitle_dub_video": ("subtitle_translate_video", "dub_video")' in bot_py
    assert '"auto_subtitle_then_dub": ("auto_subtitle_video", "dub_video")' in bot_py

    # Assert defaults and rates
    assert "VIDEO_ONLY_SUBTITLE_TRANSLATE_RATE_XU = 0.1" in bot_py
    assert "VIDEO_ONLY_DUB_DEFAULT_RATE_XU = 0.10" in bot_py
    assert "auto_subtitle = 0" in bot_py

    # Cross-verify audit data flags
    assert audit_data["flags"]["SUBDUB_PRICING_KEYS_RESOLVED"] == "YES"
    assert audit_data["flags"]["SUBDUB_PRICING_UNITS_RESOLVED"] == "YES"


# -----------------------------------------------------------------------------
# N. 0.5 XU/WORD AUTO SCOPE (DIRECT BOT GIT ASSERTION)
# -----------------------------------------------------------------------------
def test_n_subdub_auto_word_pricing_scope(bot_git_repo: Path, audit_data: dict):
    """Prove 0.5 Xu/word is an Auto speaker casting component, NOT generic dubbing pricing, directly from source."""
    auto_pricing_py = read_bot_git_file(bot_git_repo, "services/subdub_auto_word_pricing.py")

    assert 'AUTO_XU_PER_WORD = Decimal("0.5")' in auto_pricing_py
    assert "Pure word counting and pricing policy for SubDub Auto speaker casting." in auto_pricing_py
    assert "def count_billable_words(text: str) -> int:" in auto_pricing_py

    # Cross-verify audit data flags
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
# P. WEB AND BOT INPUT/OUTPUT CONTRACTS ARE SEPARATED & ALL C3 FLAGS RESOLVED
# -----------------------------------------------------------------------------
def test_p_web_and_bot_input_output_authority_separated(audit_data: dict):
    """Prove input and output authorities are strictly separated between Web and Bot, with all C3 decisions resolved."""
    flags = audit_data["flags"]

    # First Red & Bot Git Fixture Flags
    assert flags["FIRST_RED_BOT_SOURCE_ASSERTION_OPTIONAL"] == "PROVEN"
    assert flags["FIRST_RED_SELF_REFERENTIAL_BOT_EVIDENCE"] == "PROVEN"
    assert flags["BOT_AUTHORITY_COMMIT_REQUIRED"] == "YES"
    assert flags["BOT_SOURCE_MISSING_FAILS_FOCUSED_SUITE"] == "YES"

    # Input and Upload Authority Reality (Fail-closed NO due to unresolved semantic & staging gaps)
    assert flags["SUBDUB_INPUT_CONTRACT_RESOLVED"] == "NO"
    assert flags["SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED"] == "NO"
    assert flags["BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED"] == "NO"
    assert flags["BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED"] == "NO"
    assert flags["R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY"] == "NO"

    # Zero Self-Referential Authority Gates
    assert flags["SELF_REFERENTIAL_AUTHORITY_GATE_COUNT"] == 0

    # Admin Traceability Truth (Fail-closed NO until Admin is built)
    assert flags["ADMIN_SUBDUB_JOB_TRACE_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED"] == "NO"

    # Existing Separations
    assert flags["WEB_AND_BOT_INPUT_AUTHORITY_SEPARATED"] == "YES"
    assert flags["WEB_AND_BOT_OUTPUT_AUTHORITY_SEPARATED"] == "YES"
    assert flags["WEB_KEEP_ORIGINAL_AUDIO_AUTHORITY"] == "NO"
    assert flags["WEB_PROVIDER_VOICE_ID_AUTHORITY"] == "NO"
    assert flags["WEB_REMOTE_MEDIA_URL_AUTHORITY"] == "NO"
    assert flags["BOT_OUTPUT_CAPABILITY_RESOLVED"] == "YES"
    assert flags["WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN"] == "NO"
    assert flags["WEB_VOICE_PROFILE_SELECTION_AUTHORITY_RESOLVED"] == "NO"
    assert flags["CLIENT_PROVIDER_VOICE_ID_AUTHORITY"] == "NO"
    assert flags["BOT_VOICE_RESOLUTION_AUTHORITY_SEPARATE"] == "YES"


# -----------------------------------------------------------------------------
# Q. BOT PIPELINE DEFAULT OUTPUT TYPES AND FAIL CLOSED (DIRECT BOT GIT ASSERTION)
# -----------------------------------------------------------------------------
def test_q_bot_pipeline_default_output_types_and_fail_closed(bot_git_repo: Path):
    """Prove default output types and fail-closed logic directly from services/subtitle_dub_product_pipeline.py."""
    pipeline_py = read_bot_git_file(bot_git_repo, "services/subtitle_dub_product_pipeline.py")

    # Assert default output type logic
    assert "if mode in {VIDEO_SUBTITLE_MODE_CREATE, VIDEO_SUBTITLE_MODE_TRANSLATE}:" in pipeline_py
    assert 'return "burn" if is_video_source else "srt"' in pipeline_py
    assert "if mode == VIDEO_SUBTITLE_MODE_DUB:" in pipeline_py
    assert 'return "video" if is_video_source else "audio"' in pipeline_py
    assert "if mode == VIDEO_SUBTITLE_MODE_SUBTITLE_PLUS_DUB:" in pipeline_py
    assert 'return "video_subtitle" if is_video_source else "audio"' in pipeline_py

    # Assert fail closed if no output produced
    assert "if not (srt_bytes or audio_bytes or video_output):" in pipeline_py
    assert '"status": "NO_OUTPUT_BYTES"' in pipeline_py
    assert '"error_code": "output_empty"' in pipeline_py


# -----------------------------------------------------------------------------
# R. SUBDUB I18N LOCALE KEY COUNTS AND PURITY
# -----------------------------------------------------------------------------
def test_r_subdub_locale_key_counts_and_purity(portal_i18n_source: str, audit_data: dict):
    """Prove SubDub i18n locale key counts, parity, and lack of placeholder corruption."""
    vi_part = portal_i18n_source[:portal_i18n_source.find("en: {")]
    en_part = portal_i18n_source[portal_i18n_source.find("en: {"):portal_i18n_source.find("zh: {")]

    vi_keys = re.findall(r'"([a-zA-Z0-9_\.\-]+)":\s*"', vi_part)
    en_keys = re.findall(r'"([a-zA-Z0-9_\.\-]+)":\s*"', en_part)

    subdub_vi = [k for k in vi_keys if any(x in k.lower() for x in ["subtitle", "dub", "asr"])]
    subdub_en = [k for k in en_keys if any(x in k.lower() for x in ["subtitle", "dub", "asr"])]

    assert len(subdub_vi) == 79, f"Expected 79 SubDub VI keys, found {len(subdub_vi)}"
    assert len(subdub_en) == 79, f"Expected 79 SubDub EN keys, found {len(subdub_en)}"
    assert set(subdub_vi) == set(subdub_en), "Mismatch between VI and EN SubDub keys"

    # Cross-verify against audit data
    assert audit_data["locale_purity"]["subdub_vi_keys_count"] == 79
    assert audit_data["locale_purity"]["subdub_en_keys_count"] == 79
    assert audit_data["locale_purity"]["raw_placeholder_leaks"] == 0


# -----------------------------------------------------------------------------
# S. FIRST RED: ASSET VAULT FEATURE UPLOAD AUTHORITY CLAIM FALSE
# -----------------------------------------------------------------------------
def test_s_first_red_asset_vault_feature_upload_authority_claim_false(audit_data: dict):
    """Prove Asset Vault is NOT the canonical feature upload authority for SubDub jobs."""
    flags = audit_data["flags"]
    assert flags["FIRST_RED_ASSET_VAULT_FEATURE_UPLOAD_AUTHORITY_CLAIM_FALSE"] == "PROVEN"
    assert flags["CURRENT_WEB_FEATURE_UPLOAD_IDENTIFIER"] == "upload_id"
    assert flags["CURRENT_WEB_FEATURE_UPLOAD_STORAGE_AUTHORITY"] == "BOT_OWNED_STAGING"
    assert flags["ASSET_ID_IS_GENERIC_SUBDUB_UPLOAD_AUTHORITY"] == "NO"

    # Verify copyfast_api source: uses _canonical_upload_ids and transfers to bot-owned staging
    copyfast_api_path = STANDALONE_ROOT / "copyfast_api.py"
    copyfast_api_src = copyfast_api_path.read_text(encoding="utf-8")
    assert "def _canonical_upload_ids(value: Any) -> list[str] | None:" in copyfast_api_src
    assert "Accept only opaque bot staging identifiers, never paths or handles." in copyfast_api_src
    assert "The standalone Web DB records neither raw file bytes nor provider paths." in copyfast_api_src
    assert '"/internal/v1/uploads"' in copyfast_api_src


# -----------------------------------------------------------------------------
# T. BOT STAGING UPLOAD CONTRACT STATUS (FAIL-CLOSED NO)
# -----------------------------------------------------------------------------
def test_t_bot_staging_upload_contract_status(bot_git_repo: Path, audit_data: dict):
    """Prove Bot at pinned commit lacks /internal/v1/uploads and staging lookup route."""
    flags = audit_data["flags"]
    assert flags["BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED"] == "NO"
    assert flags["BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED"] == "NO"
    assert flags["SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED"] == "NO"
    assert flags["SECOND_SUBDUB_UPLOAD_AUTHORITY_CREATED"] == "NO"
    assert flags["RAW_BROWSER_PATH_ACCEPTED"] == 0
    assert flags["REMOTE_MEDIA_URL_ACCEPTED"] == 0

    # Pinned Bot commit verification: bot.py does not define /internal/v1/uploads
    bot_py = read_bot_git_file(bot_git_repo, "bot.py")
    assert "/internal/v1/uploads" not in bot_py
    assert "/internal/v1/voice/profiles" not in bot_py


# -----------------------------------------------------------------------------
# U. OUTPUT FORMAT CONTRADICTION & UNRESOLVED INPUT CONTRACT
# -----------------------------------------------------------------------------
def test_u_output_format_contradiction_and_unresolved_input_contract(portal_js_source: str, bot_git_repo: Path, audit_data: dict):
    """Prove Web forms hardcode srt-only while Bot canonical pipeline requires media/burn output."""
    flags = audit_data["flags"]
    assert flags["CURRENT_WEB_OUTPUT_FORMAT_CONTRACT_COMPATIBLE_WITH_BOT"] == "NO"
    assert flags["WEB_DUBBING_SRT_ONLY_SEMANTIC_GAP"] == "PROVEN"
    assert flags["R2_OUTPUT_AUTHORITY_DECISION_REQUIRED"] == "YES"
    assert flags["SUBDUB_INPUT_CONTRACT_RESOLVED"] == "NO"

    # Web hardcodes srt in dubbing form
    dub_start = portal_js_source.find("dubbing:")
    dub_end = portal_js_source.find("documentPdf:")
    field_sets_snippet = portal_js_source[dub_start:dub_end]
    assert 'options: ["srt"]' in field_sets_snippet

    # Bot outputs video or audio for dubbing
    pipeline_py = read_bot_git_file(bot_git_repo, "services/subtitle_dub_product_pipeline.py")
    assert "if mode == VIDEO_SUBTITLE_MODE_DUB:" in pipeline_py
    assert 'return "video" if is_video_source else "audio"' in pipeline_py


# -----------------------------------------------------------------------------
# V. DURATION SECONDS AUTHORITY TRUTH
# -----------------------------------------------------------------------------
def test_v_duration_seconds_authority_truth(portal_js_source: str, bot_git_repo: Path, audit_data: dict):
    """Prove Web client duration_seconds is unvalidated user input, while Bot enforces ffprobe duration."""
    flags = audit_data["flags"]
    assert flags["WEB_DURATION_SECONDS_IS_MEDIA_TRUTH"] == "NO"
    assert flags["BOT_MEDIA_DURATION_PROBE_AUTHORITY_RESOLVED"] == "YES"
    assert flags["R2_MUST_REVALIDATE_MEDIA_DURATION"] == "YES"

    # Web accepts arbitrary numeric 1..14400 from client
    assert 'name: "duration_seconds"' in portal_js_source
    assert "min: 1" in portal_js_source
    assert "max: 14_400" in portal_js_source

    # Bot probes duration via ffprobe
    bot_py = read_bot_git_file(bot_git_repo, "bot.py")
    assert "ffprobe_duration" in bot_py
    assert "subdub_duration_gate_payload" in bot_py


# -----------------------------------------------------------------------------
# W. VOICE PROFILE SELECTION AUTHORITY
# -----------------------------------------------------------------------------
def test_w_voice_profile_selection_authority(portal_js_source: str, bot_git_repo: Path, audit_data: dict):
    """Prove Web voice profile selection proxies to missing Bot endpoint, and client has no provider voice ID authority."""
    flags = audit_data["flags"]
    assert flags["WEB_VOICE_PROFILE_SELECTION_AUTHORITY_RESOLVED"] == "NO"
    assert flags["CLIENT_PROVIDER_VOICE_ID_AUTHORITY"] == "NO"

    # Web form references voiceProfiles
    assert 'optionsFrom: "voiceProfiles"' in portal_js_source

    # Bot pinned commit lacks /internal/v1/voice/profiles
    bot_py = read_bot_git_file(bot_git_repo, "bot.py")
    assert "/internal/v1/voice/profiles" not in bot_py


# -----------------------------------------------------------------------------
# X. DIRECT SOURCE RUNTIME STAGE AUTHORITIES (REPLACING CIRCULAR ASSERTIONS)
# -----------------------------------------------------------------------------
def test_x_direct_source_runtime_stage_authorities(bot_git_repo: Path, audit_data: dict):
    """Prove ASR, Translation, TTS, and Mux/Render authorities directly from Bot source files."""
    flags = audit_data["flags"]
    assert flags["ASR_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF"] == "PASS"
    assert flags["TRANSLATION_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF"] == "PASS"
    assert flags["TTS_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF"] == "PASS"
    assert flags["MUX_RENDER_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF"] == "PASS"
    assert flags["SELF_REFERENTIAL_AUTHORITY_GATE_COUNT"] == 0

    pipeline_py = read_bot_git_file(bot_git_repo, "services/subtitle_dub_product_pipeline.py")
    tts_routing_py = read_bot_git_file(bot_git_repo, "services/subdub_tts_language_routing.py")
    auto_pricing_py = read_bot_git_file(bot_git_repo, "services/subdub_auto_word_pricing.py")

    # ASR source proof
    assert "prepare_subtitles" in pipeline_py
    assert "asr_provider" in pipeline_py

    # Translation source proof
    assert "translation_provider" in pipeline_py

    # TTS source proof
    assert "def resolve_subdub_tts_language_route" in tts_routing_py
    assert 'AUTO_XU_PER_WORD = Decimal("0.5")' in auto_pricing_py
    assert "synthesize_segments" in pipeline_py
    assert "resolve_voice_id" in pipeline_py

    # Mux / Render source proof
    assert "ffmpeg_ready" in pipeline_py
    assert "dub_mux_enabled" in pipeline_py
    assert "render_video" in pipeline_py


# -----------------------------------------------------------------------------
# Y. LOCALE VISIBLE COPY PURITY & UNLOCALIZED LABELS ENUMERATION
# -----------------------------------------------------------------------------
def test_y_locale_visible_copy_purity(portal_js_source: str, audit_data: dict):
    """Prove visible copy purity FAIL with exactly 12 unlocalized strings in Vietnamese views."""
    flags = audit_data["flags"]
    assert flags["SUBDUB_I18N_KEY_PARITY"] == "PASS"
    assert flags["SUBDUB_VI_VISIBLE_COPY_PURITY"] == "FAIL"
    assert flags["MIXED_VI_VISIBLE_LABEL_COUNT"] == 12

    unlocalized_labels = [
        "🟢 Neural SubDub Engine Sẵn Sàng",
        "🎙️ AI SubDub Studio — Tạo Phụ Đề & Lồng Tiếng Chuyên Nghiệp",
        "Timeline Match",
        "Transcript projects",
        "Web-native subtitle authoring",
        "Manual cue authoring",
        "Web-native deterministic tool",
        "Sub & Dub Operations Hub",
        "AI Subtitle & Dubbing",
        "SRT / VTT Format Lab",
        "Subtitle Asset Operations",
        "Subtitle Studio Workspace",
    ]
    for label in unlocalized_labels:
        assert label in portal_js_source, f"Expected unlocalized label '{label}' in portal.js"


# -----------------------------------------------------------------------------
# Z. ADMIN SUBDUB TRACE GAPS DIRECT SOURCE PROOF
# -----------------------------------------------------------------------------
def test_z_admin_subdub_trace_gaps_direct_source_proof(portal_js_source: str, audit_data: dict):
    """Prove generic admin views lack SubDub lane, multi-stage, failure attribution, and artifact traces."""
    flags = audit_data["flags"]
    assert flags["ADMIN_SUBDUB_TRACE_GAPS_DIRECT_SOURCE_PROOF"] == "PASS"
    assert flags["ADMIN_SUBDUB_JOB_TRACE_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED"] == "NO"
    assert flags["ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED"] == "NO"

    # portal.js registers admin jobs routes
    assert 'adminPage("/admin/jobs"' in portal_js_source
    assert 'adminPage("/admin/jobs/failed"' in portal_js_source

    # Admin table renderer around lines 30830-30850 lacks subdub_lane and multi-stage tracking
    jobs_start = portal_js_source.find('if (module === "failed-jobs")')
    jobs_end = portal_js_source.find('if (module === "providers")')
    admin_jobs_section = portal_js_source[jobs_start:jobs_end]
    assert "subdub_lane" not in admin_jobs_section
    assert "asr_stage" not in admin_jobs_section
    assert "stage_pipeline" not in admin_jobs_section


# -----------------------------------------------------------------------------
# AA. R2 DURABLE JOB BRIDGE AUTHORITY READINESS (FAIL-CLOSED NO)
# -----------------------------------------------------------------------------
def test_aa_r2_durable_job_bridge_authority_readiness(audit_data: dict):
    """Prove R2 durable job bridge cannot be marked ready due to unresolved upload, output format, duration, and voice gaps."""
    flags = audit_data["flags"]
    assert flags["R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY"] == "NO"
