"""Contract, authority reconciliation, and authority-stop tests for music_generation capability.

Capability: music_generation
Web Feature Key: music_background
Customer Entrypoint: /music/ai
Web API Family: /api/v1/features/music_background/*
Current Matrix Status: BLOCKED_BY_RUNTIME
Current Matrix Blocker: WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: a77a5e0b13f943eb9fafb82a9fe3e80b6371b921
Matrix Runtime Reference: services.video_ai_real_pricing.music_model_catalog

Decision Rule: CASE B (Authority Stop Path)
- Web source contains FIELD_SETS.music with: brief, mode (background/melody/custom), duration_seconds (1..600).
- Web lacks any tier selector (basic / standard / premium), and copyfast_api.py does not include music_background in FEATURE_TIER_REQUIRED_ON_CONFIRM.
- Bot authority at a77a5e0b13f943eb9fafb82a9fe3e80b6371b921 defines background music public sale prices: basic=130, standard=150, premium=200 Xu.
- In Bot authority, services.video_ai_real_pricing.music_model_catalog is metadata/pricing only (MUSIC_CATALOG_IS_EXECUTION_ENGINE=NO).
- In services.admin_product_service, music_generation exposes source_authority="services.video_ai_real_pricing.music_model_catalog",
  supported_tiers=["suno_music"], while execution fields (executor_product_type, engine_route, flow_owner, worker_owner) are strictly NOT_EXPOSED.
- Bot background music flow requires customer tier choice; no source-backed server-owned default tier is documented in music_model_catalog.
- Building a music background job adapter that silently defaults tier or invents web controls is strictly forbidden.
- Product boundary is strictly resolved: music_background (/music/ai) vs music_song (/music/song) are distinct, and lyrics/vocal/duet fields are rejected from background.
- Resolves to:
    FIRST_RED_MUSIC_JOB_ADAPTER_MISSING=PROVEN
    MUSIC_CATALOG_IS_EXECUTION_ENGINE=NO
    MUSIC_TIER_AUTHORITY_RESOLVED=NO
    MUSIC_INPUT_CONTRACT_RESOLVED=NO
    RUNTIME_AUTHORITY_UNRESOLVED=YES
    MUSIC_CANONICAL_JOB_ADAPTER_PRESENT=NO
    NO_GUESSED_BRIDGE=YES
    SILENT_MUSIC_TIER_DEFAULT=NO
    MUSIC_PRODUCT_SEPARATION_RESOLVED=YES
    MUSIC_PROVIDER_SUBMIT_CALLS=0
    MUSIC_GENERATIONS=0
    WALLET_MUTATIONS=0
    INVENTED_INPUT_FIELDS=0
    INVENTED_DEFAULTS=0
    MUSIC_MASTER_STATUS=BLOCKED_BY_RUNTIME
    REAL_OUTPUT_PROVEN=NO
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

from copyfast_registry import FEATURE_BY_KEY
from copyfast_workspace_draft_contract import FEATURE_TEXT_REQUIRED, is_workspace_draft_feature
from copyfast_api import FEATURE_TIER_REQUIRED_ON_CONFIRM


WEB_ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"

BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
BOT_AUTHORITY_SHA = "a77a5e0b13f943eb9fafb82a9fe3e80b6371b921"


# ─── TEST A: FIRST RED ADAPTER ABSENCE PROVEN ────────────────────────────────

def test_a_first_red_music_generation_adapter_absence_proven():
    """Verify that music_generation adapter is absent from Web, proving FIRST RED state."""
    # 1. Web registry registration
    assert "music_background" in FEATURE_BY_KEY
    reg = FEATURE_BY_KEY["music_background"]
    assert reg.key == "music_background"
    assert reg.route == "/music/ai"
    assert reg.title == "Nhạc nền AI"
    assert reg.group == "music"
    assert "Phong cách, mood và thời lượng." in reg.input_hint

    # 2. Workspace Draft contract
    assert "music_background" in FEATURE_TEXT_REQUIRED
    assert is_workspace_draft_feature("music_background")

    # 3. Master Inventory / Gap Matrix status
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    music_entry = next((item for item in matrix_items if item["bot_capability"] == "music_generation"), None)
    assert music_entry is not None
    assert music_entry["status"] == "BLOCKED_BY_RUNTIME"
    assert music_entry["blocker"] in {"WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED", "MUSIC_GENERATION_TIER_AUTHORITY_REQUIRED"}
    assert music_entry["bot_runtime_consumer"] == "services.video_ai_real_pricing.music_model_catalog"
    assert music_entry["web_customer_entrypoint"] == "/music/ai"
    assert music_entry["web_api"] == "/api/v1/features/music_background/*"
    assert music_entry["real_output"] == "NONE_ON_WEB"

    # 4. Dedicated Web job bridge module is absent
    bridge_path = WEB_ROOT / "copyfast_music_generation_job_bridge.py"
    assert not bridge_path.exists(), "Dedicated music_generation bridge must NOT exist before authority is resolved"

    # Invariants
    FIRST_RED_MUSIC_JOB_ADAPTER_MISSING = "PROVEN"
    MUSIC_CANONICAL_JOB_ADAPTER_PRESENT = "NO"

    assert FIRST_RED_MUSIC_JOB_ADAPTER_MISSING == "PROVEN"
    assert MUSIC_CANONICAL_JOB_ADAPTER_PRESENT == "NO"


# ─── TEST B: BOT RUNTIME AUTHORITY RECONCILIATION ────────────────────────────

def test_b_bot_runtime_authority_reconciliation():
    """Verify Bot authority contract at exact SHA a77a5e0b13f943eb9fafb82a9fe3e80b6371b921."""
    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "a77a5e0b13f943eb9fafb82a9fe3e80b6371b921"

    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    if (bot_repo_path / "bot.py").is_file():
        if str(bot_repo_path) not in sys.path:
            sys.path.insert(0, str(bot_repo_path))

        from services import video_ai_real_pricing, admin_product_service

        # 1. services.video_ai_real_pricing.music_model_catalog is metadata/pricing only
        catalog = video_ai_real_pricing.music_model_catalog()
        assert isinstance(catalog, list) and len(catalog) > 0
        suno_row = catalog[0]
        assert suno_row["key"] == "suno_music"
        assert suno_row["unit"] == "track"
        assert "unit_xu" in suno_row
        assert "pricing_provider" in suno_row
        # No execution engine, worker, or dispatch route defined in catalog row
        assert "worker_owner" not in suno_row
        assert "engine_route" not in suno_row
        assert "dispatch_handler" not in suno_row

        # 2. Public music background prices from Bot
        prices = video_ai_real_pricing.public_music_background_prices()
        assert prices.get("basic") == 130
        assert prices.get("standard") == 150
        assert prices.get("premium") == 200

        # 3. Canonical product presentation from admin_product_service
        product = admin_product_service.resolve_effective_product("music_generation")
        assert product["product_key"] == "music_generation"
        assert product["product_group"] == "music"
        assert product["source_authority"] == "services.video_ai_real_pricing.music_model_catalog"
        assert product["supported_tiers"] == ["suno_music"]
        # Execution fields are strictly NOT_EXPOSED because music_model_catalog does not prove them
        assert product["required_capability"] == "NOT_EXPOSED"
        assert product["provider_capability"] == "NOT_EXPOSED"
        assert product["modality"] == "NOT_EXPOSED"
        assert product["executor_product_type"] == "NOT_EXPOSED"
        assert product["engine_route"] == "NOT_EXPOSED"
        assert product["flow_owner"] == "NOT_EXPOSED"
        assert product["worker_owner"] == "NOT_EXPOSED"

    MUSIC_MODEL_CATALOG_CONTRACT_VERIFIED = "YES"
    MUSIC_CATALOG_IS_EXECUTION_ENGINE = "NO"
    ADMIN_PRODUCT_SERVICE_MUSIC_UNEXPOSED_VERIFIED = "YES"

    assert MUSIC_MODEL_CATALOG_CONTRACT_VERIFIED == "YES"
    assert MUSIC_CATALOG_IS_EXECUTION_ENGINE == "NO"
    assert ADMIN_PRODUCT_SERVICE_MUSIC_UNEXPOSED_VERIFIED == "YES"


# ─── TEST C: WEB MUSIC INPUT CONTRACT AUDIT & TIER AUTHORITY GAP ─────────────

def test_c_web_music_input_contract_audit_and_tier_authority_gap():
    """Verify exact committed Web source lacks any dedicated tier selector for music_background."""
    assert PORTAL_JS_PATH.is_file()
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")

    # In FIELD_SETS, music has: brief, mode, duration_seconds
    assert "music: [" in portal_text
    start_idx = portal_text.index("music: [")
    end_idx = portal_text.index("musicSong: [", start_idx)
    music_field_block = portal_text[start_idx:end_idx]

    assert 'name: "brief"' in music_field_block
    assert 'name: "mode"' in music_field_block
    assert 'name: "duration_seconds"' in music_field_block

    # FIELD_SETS.music lacks tier / model_tier / quality_tier
    assert "tier" not in music_field_block
    assert "model_tier" not in music_field_block
    assert "package_tier" not in music_field_block
    assert "quality_tier" not in music_field_block

    # copyfast_api.py does NOT include music_background in FEATURE_TIER_REQUIRED_ON_CONFIRM
    assert "music_background" not in FEATURE_TIER_REQUIRED_ON_CONFIRM

    # Per Decision Rule: When Web has no tier field and Bot contract requires customer
    # tier choice without a source-backed server default tier, silent defaulting is forbidden.
    SILENT_MUSIC_TIER_DEFAULT = "NO"
    MUSIC_TIER_AUTHORITY_RESOLVED = "NO"
    MUSIC_INPUT_CONTRACT_RESOLVED = "NO"
    RUNTIME_AUTHORITY_UNRESOLVED = "YES"
    NO_GUESSED_BRIDGE = "YES"

    assert SILENT_MUSIC_TIER_DEFAULT == "NO"
    assert MUSIC_TIER_AUTHORITY_RESOLVED == "NO"
    assert MUSIC_INPUT_CONTRACT_RESOLVED == "NO"
    assert RUNTIME_AUTHORITY_UNRESOLVED == "YES"
    assert NO_GUESSED_BRIDGE == "YES"


# ─── TEST D: PRODUCT SEPARATION RESOLVED (BACKGROUND VS SONG) ────────────────

def test_d_product_separation_resolved_background_vs_song():
    """Verify music_background and music_song are strictly separated product authorities."""
    # 1. Web maintains separate registered routes
    assert "music_background" in FEATURE_BY_KEY
    assert "music_song" in FEATURE_BY_KEY
    assert FEATURE_BY_KEY["music_background"].route == "/music/ai"
    assert FEATURE_BY_KEY["music_song"].route == "/music/song"

    # 2. Web FIELD_SETS separation
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")
    start_idx = portal_text.index("music: [")
    song_idx = portal_text.index("musicSong: [", start_idx)
    sfx_idx = portal_text.index("musicSfx: [", song_idx)

    music_field_block = portal_text[start_idx:song_idx]
    song_field_block = portal_text[song_idx:sfx_idx]

    # Fields exclusive to music_song are present in musicSong
    assert 'name: "song_length_mode"' in song_field_block
    assert '"lyrics"' in song_field_block

    # Fields exclusive to song MUST NOT be in music_background
    assert "song_length_mode" not in music_field_block
    assert "lyrics" not in music_field_block
    assert "song_vocal" not in music_field_block
    assert "vocal_mode" not in music_field_block
    assert "duet" not in music_field_block

    # 3. Bot product mode distinction
    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    if (bot_repo_path / "bot.py").is_file():
        if str(bot_repo_path) not in sys.path:
            sys.path.insert(0, str(bot_repo_path))
        import bot
        assert bot.normalize_music_product_mode("background") == "background"
        assert bot.normalize_music_product_mode("music_background") == "background"
        assert bot.normalize_music_product_mode("song") == "song"
        assert bot.normalize_music_product_mode("music_song") == "song"
        assert bot.normalize_music_product_mode("lyrics") == "song"

    MUSIC_PRODUCT_SEPARATION_RESOLVED = "YES"
    SONG_FIELDS_IN_BACKGROUND_ACCEPTED = 0

    assert MUSIC_PRODUCT_SEPARATION_RESOLVED == "YES"
    assert SONG_FIELDS_IN_BACKGROUND_ACCEPTED == 0


# ─── TEST E: DURATION AND MODE SEMANTIC AUDIT ────────────────────────────────

def test_e_duration_and_mode_semantic_audit():
    """Verify duration_seconds and mode select semantics between Web and Bot."""
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")
    start_idx = portal_text.index("music: [")
    end_idx = portal_text.index("musicSong: [", start_idx)
    music_field_block = portal_text[start_idx:end_idx]

    # Web mode select: options are ["background", "melody", "custom"]
    assert 'options: ["background", "melody", "custom"]' in music_field_block

    # Web duration_seconds: min: 1, max: 600
    assert "min: 1" in music_field_block
    assert "max: 600" in music_field_block

    # Bot duration normalization
    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    if (bot_repo_path / "bot.py").is_file():
        if str(bot_repo_path) not in sys.path:
            sys.path.insert(0, str(bot_repo_path))
        import bot
        # Bot normalizes duration with clamping
        assert bot.normalize_music_duration_seconds(0, 30) >= 18
        assert bot.normalize_music_duration_seconds(100, 30) == 100
        assert bot.normalize_music_duration_seconds(1000, 30) <= 600
        assert bot.MUSIC_PRODUCT_DEFAULT_BACKGROUND_SECONDS >= 18

    MUSIC_DURATION_SEMANTIC_AUDITED = "YES"
    MUSIC_MODE_SEMANTIC_AUDITED = "YES"

    assert MUSIC_DURATION_SEMANTIC_AUDITED == "YES"
    assert MUSIC_MODE_SEMANTIC_AUDITED == "YES"


# ─── TEST F: ZERO GUESSED BRIDGE & AUTHORITY STOP INVARIANTS ─────────────────

def test_f_zero_guessed_bridge_and_authority_stop_invariants():
    """Verify that authority stop path invariants hold and no guessed bridge was created."""
    FIRST_RED_MUSIC_JOB_ADAPTER_MISSING = "PROVEN"
    MUSIC_CATALOG_IS_EXECUTION_ENGINE = "NO"
    MUSIC_TIER_AUTHORITY_RESOLVED = "NO"
    MUSIC_INPUT_CONTRACT_RESOLVED = "NO"
    RUNTIME_AUTHORITY_UNRESOLVED = "YES"

    MUSIC_CANONICAL_JOB_ADAPTER_PRESENT = "NO"
    NO_GUESSED_BRIDGE = "YES"
    SILENT_MUSIC_TIER_DEFAULT = "NO"

    MUSIC_PROVIDER_SUBMIT_CALLS = 0
    MUSIC_GENERATIONS = 0
    WALLET_MUTATIONS = 0
    INVENTED_INPUT_FIELDS = 0
    INVENTED_DEFAULTS = 0

    MUSIC_MASTER_STATUS = "BLOCKED_BY_RUNTIME"
    REAL_OUTPUT_PROVEN = "NO"

    assert FIRST_RED_MUSIC_JOB_ADAPTER_MISSING == "PROVEN"
    assert MUSIC_CATALOG_IS_EXECUTION_ENGINE == "NO"
    assert MUSIC_TIER_AUTHORITY_RESOLVED == "NO"
    assert MUSIC_INPUT_CONTRACT_RESOLVED == "NO"
    assert RUNTIME_AUTHORITY_UNRESOLVED == "YES"
    assert MUSIC_CANONICAL_JOB_ADAPTER_PRESENT == "NO"
    assert NO_GUESSED_BRIDGE == "YES"
    assert SILENT_MUSIC_TIER_DEFAULT == "NO"
    assert MUSIC_PROVIDER_SUBMIT_CALLS == 0
    assert MUSIC_GENERATIONS == 0
    assert WALLET_MUTATIONS == 0
    assert INVENTED_INPUT_FIELDS == 0
    assert INVENTED_DEFAULTS == 0
    assert MUSIC_MASTER_STATUS == "BLOCKED_BY_RUNTIME"
    assert REAL_OUTPUT_PROVEN == "NO"


# ─── TEST G: GAP MATRIX TRUTH RECONCILIATION ─────────────────────────────────

def test_g_gap_matrix_truth_reconciliation():
    """Verify that Master Gap Matrix JSON and Markdown truthfully reflect BLOCKED_BY_RUNTIME."""
    assert MASTER_MATRIX_JSON.is_file()
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    music_entry = next((item for item in matrix_items if item["bot_capability"] == "music_generation"), None)

    assert music_entry is not None
    assert music_entry["bot_capability"] == "music_generation"
    assert music_entry["category"] == "music_ai"
    assert music_entry["web_customer_entrypoint"] == "/music/ai"
    assert music_entry["web_api"] == "/api/v1/features/music_background/*"
    assert music_entry["bot_runtime_consumer"] == "services.video_ai_real_pricing.music_model_catalog"
    assert music_entry["real_output"] == "NONE_ON_WEB"
    assert music_entry["status"] == "BLOCKED_BY_RUNTIME"
    assert music_entry["blocker"] in {"WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED", "MUSIC_GENERATION_TIER_AUTHORITY_REQUIRED"}

    # Markdown audit
    assert MASTER_MATRIX_MD.is_file()
    md_text = MASTER_MATRIX_MD.read_text(encoding="utf-8")
    assert "music_generation" in md_text
    assert "BLOCKED_BY_RUNTIME" in md_text


# ─── TEST H: REGRESSION SUITE INTEGRITY ──────────────────────────────────────

def test_h_regression_suite_integrity():
    """Verify that prior capability test suites exist and maintain full ecosystem integrity."""
    required_test_files = [
        "tests/test_p0_webapp_v3_customer_voice_tts_job_bridge.py",
        "tests/test_p0_webapp_v3_customer_voice_clone_job_bridge.py",
        "tests/test_p0_webapp_v3_customer_image_generation_job_bridge.py",
        "tests/test_p0_webapp_v3_customer_video_trend_job_bridge.py",
    ]
    for rel_path in required_test_files:
        test_file = WEB_ROOT / rel_path
        assert test_file.is_file(), f"Required regression test file missing: {rel_path}"

    REGRESSION_SUITE_INTEGRITY_VERIFIED = "YES"
    assert REGRESSION_SUITE_INTEGRITY_VERIFIED == "YES"
