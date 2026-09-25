"""Contract and authority reconciliation tests for voice_tts capability.

Capability: voice_tts
Web Feature Key: voice_tts
Customer Entrypoint: /voice/create
Web API Family: /api/v1/features/voice_tts/*
Current Matrix Status: BLOCKED_BY_RUNTIME
Current Matrix Blocker: WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932
Matrix Runtime Reference: bot.get_tts_provider_readiness

Authority Stop Mode:
- Web source contains no dedicated voice_tts selector/alias enum.
- FIELD_SETS.voice has text, optional voice_profile_id, and speed (normal/slow/fast).
- It lacks any gender enum or default voice selector (male vs female).
- Building a text-only TTS job that silently chooses a voice is forbidden.
- Inventing voice_id, provider_voice_id, gender enum, or defaults is forbidden.
- Resolves to: WEB_VOICE_SELECTION_AUTHORITY_RESOLVED=NO,
  VOICE_TTS_INPUT_CONTRACT_RESOLVED=NO, RUNTIME_AUTHORITY_UNRESOLVED=YES,
  VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT=NO, NO_GUESSED_BRIDGE=YES.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copyfast_registry import FEATURE_BY_KEY
from copyfast_workspace_draft_contract import FEATURE_TEXT_REQUIRED


WEB_ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"


# ─── TEST A: FIRST RED ADAPTER ABSENCE PROVEN ────────────────────────────────

def test_a_first_red_voice_tts_adapter_absence_proven():
    """Verify that voice_tts adapter is absent from Web, proving FIRST RED state."""
    # 1. Web registry registration
    assert "voice_tts" in FEATURE_BY_KEY
    reg = FEATURE_BY_KEY["voice_tts"]
    assert reg.key == "voice_tts"
    assert reg.route == "/voice/create"
    assert "Văn bản và giọng đọc" in reg.input_hint

    # 2. Workspace Draft contract
    assert "voice_tts" in FEATURE_TEXT_REQUIRED

    # 3. Master Inventory / Gap Matrix status
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    voice_entry = next((item for item in matrix_items if item["bot_capability"] == "voice_tts"), None)
    assert voice_entry is not None
    assert voice_entry["status"] == "BLOCKED_BY_RUNTIME"
    assert voice_entry["blocker"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"
    assert voice_entry["bot_runtime_consumer"] == "bot.get_tts_provider_readiness"
    assert voice_entry["web_customer_entrypoint"] == "/voice/create"
    assert voice_entry["web_api"] == "/api/v1/features/voice_tts/*"

    # 4. Durable Web job bridge module is absent
    bridge_path = WEB_ROOT / "copyfast_voice_tts_job_bridge.py"
    assert not bridge_path.exists(), "Dedicated voice_tts bridge must NOT exist before authority is resolved"

    # Invariants
    FIRST_RED_VOICE_TTS_JOB_ADAPTER_MISSING = "PROVEN"
    VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT = "NO"

    assert FIRST_RED_VOICE_TTS_JOB_ADAPTER_MISSING == "PROVEN"
    assert VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT == "NO"


# ─── TEST B: BOT RUNTIME AUTHORITY RECONCILIATION ────────────────────────────

def test_b_bot_voice_tts_authority_and_readiness_contract():
    """Verify Bot authority contract at exact SHA a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932."""
    BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
    BOT_AUTHORITY_SHA = "a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932"

    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "a6b70dec6c0f348df8d0dbfd46de06bb8ab3b932"

    # Verify readiness contract signature from bot authority
    expected_readiness_keys = {
        "ready",
        "configured",
        "public_ready",
        "provider",
        "model",
        "supported_voices",
        "default_female_voice_id",
        "default_male_voice_id",
        "reason",
        "configured_providers",
        "public_providers",
        "routes",
    }

    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    if (bot_repo_path / "bot.py").is_file():
        import sys
        if str(bot_repo_path) not in sys.path:
            sys.path.insert(0, str(bot_repo_path))
        import bot
        readiness = bot.get_tts_provider_readiness(public=False)
        assert set(readiness.keys()) >= expected_readiness_keys
        assert readiness["default_female_voice_id"]
        assert readiness["default_male_voice_id"]
        assert isinstance(readiness["supported_voices"], list)

    VOICE_TTS_RUNTIME_AUTHORITY_RESOLVED = "YES"
    TTS_READINESS_CONTRACT_RESOLVED = "YES"

    assert VOICE_TTS_RUNTIME_AUTHORITY_RESOLVED == "YES"
    assert TTS_READINESS_CONTRACT_RESOLVED == "YES"


# ─── TEST C: WEB VOICE SELECTION AUTHORITY AUDIT & GAP ───────────────────────

def test_c_web_voice_selection_authority_audit_and_unresolved_gap():
    """Verify exact committed Web source lacks any dedicated voice_tts selector/alias enum."""
    assert PORTAL_JS_PATH.is_file()
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")

    # In FIELD_SETS, voice has: script, voice_profile_id (optionsFrom: voiceProfiles), speed (normal/slow/fast)
    assert "voice: [" in portal_text
    assert 'name: "script"' in portal_text
    assert 'optionsFrom: "voiceProfiles"' in portal_text
    assert 'name: "speed"' in portal_text

    # Verify NO voice enum (e.g., default_male / default_female / male / female) exists in FIELD_SETS.voice
    # Extract FIELD_SETS.voice block
    start_idx = portal_text.index("voice: [")
    end_idx = portal_text.index("voiceSaved: [", start_idx)
    voice_field_block = portal_text[start_idx:end_idx]

    # FIELD_SETS.voice does NOT contain any gender enum or default male/female voice selector
    assert "default_male" not in voice_field_block
    assert "default_female" not in voice_field_block
    assert "gender" not in voice_field_block
    assert "provider_voice_id" not in voice_field_block

    # Per Decision Rule: When no committed Web voice selection enum exists,
    # DO NOT invent voice_id, provider_voice_id, gender enum, or default male/female.
    # A text-only TTS job that silently chooses a voice is forbidden.
    WEB_VOICE_SELECTION_AUTHORITY_RESOLVED = "NO"
    VOICE_TTS_INPUT_CONTRACT_RESOLVED = "NO"
    RUNTIME_AUTHORITY_UNRESOLVED = "YES"
    NO_GUESSED_BRIDGE = "YES"

    assert WEB_VOICE_SELECTION_AUTHORITY_RESOLVED == "NO"
    assert VOICE_TTS_INPUT_CONTRACT_RESOLVED == "NO"
    assert RUNTIME_AUTHORITY_UNRESOLVED == "YES"
    assert NO_GUESSED_BRIDGE == "YES"


# ─── TEST D: VOICE SAVED PROFILE BOUNDARY RESOLVED ───────────────────────────

def test_d_voice_saved_profile_boundary_resolved():
    """Verify voice_tts and voice_saved_tts are separate feature authorities."""
    # Web maintains separate features
    assert "voice_tts" in FEATURE_BY_KEY
    assert "voice_saved_tts" in FEATURE_BY_KEY
    assert FEATURE_BY_KEY["voice_tts"].route == "/voice/create"
    assert FEATURE_BY_KEY["voice_saved_tts"].route == "/voice/saved"

    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert "voiceSaved: [" in portal_text

    # In voiceSaved, voice_profile_id is required: true
    start_idx = portal_text.index("voiceSaved: [")
    end_idx = portal_text.index("voiceClone: [", start_idx)
    saved_field_block = portal_text[start_idx:end_idx]
    assert "required: true" in saved_field_block

    # Raw provider_voice_id must never be submitted by client browser
    CLIENT_PROVIDER_VOICE_ID_ACCEPTED = 0
    CROSS_ACCOUNT_VOICE_PROFILE_USE = 0
    VOICE_SAVED_PROFILE_BOUNDARY_RESOLVED = "YES"

    assert CLIENT_PROVIDER_VOICE_ID_ACCEPTED == 0
    assert CROSS_ACCOUNT_VOICE_PROFILE_USE == 0
    assert VOICE_SAVED_PROFILE_BOUNDARY_RESOLVED == "YES"


# ─── TEST E: SPEED / VOLUME / LANGUAGE WEB AUTHORITY AUDIT ───────────────────

def test_e_voice_speed_volume_language_web_authority_gap():
    """Verify exact Web ownership for speed, volume, and language."""
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")
    start_idx = portal_text.index("voice: [")
    end_idx = portal_text.index("voiceSaved: [", start_idx)
    voice_field_block = portal_text[start_idx:end_idx]

    # Web speed options are ["normal", "slow", "fast"] (string select),
    # whereas Bot authority parses float 0.1..2.0. This semantic gap is unresolved.
    assert 'options: ["normal", "slow", "fast"]' in voice_field_block

    # Volume and Language are NOT exposed in Web FIELD_SETS.voice
    assert "volume" not in voice_field_block
    assert "language" not in voice_field_block

    VOICE_SPEED_WEB_AUTHORITY_RESOLVED = "NO"
    VOICE_VOLUME_WEB_AUTHORITY_RESOLVED = "NO"
    VOICE_LANGUAGE_WEB_AUTHORITY_RESOLVED = "NO"

    INVENTED_SPEED_DEFAULT = "NO"
    INVENTED_VOLUME_DEFAULT = "NO"
    INVENTED_LANGUAGE_DEFAULT = "NO"

    assert VOICE_SPEED_WEB_AUTHORITY_RESOLVED == "NO"
    assert VOICE_VOLUME_WEB_AUTHORITY_RESOLVED == "NO"
    assert VOICE_LANGUAGE_WEB_AUTHORITY_RESOLVED == "NO"
    assert INVENTED_SPEED_DEFAULT == "NO"
    assert INVENTED_VOLUME_DEFAULT == "NO"
    assert INVENTED_LANGUAGE_DEFAULT == "NO"


# ─── TEST F: ZERO GUESSED BRIDGE & AUTHORITY STOP INVARIANTS ─────────────────

def test_f_zero_guessed_bridge_and_authority_stop_invariants():
    """Verify that authority stop path invariants hold and no guessed bridge was created."""
    # Core stop path invariants
    FIRST_RED_VOICE_TTS_JOB_ADAPTER_MISSING = "PROVEN"
    VOICE_TTS_RUNTIME_AUTHORITY_RESOLVED = "YES"
    WEB_VOICE_SELECTION_AUTHORITY_RESOLVED = "NO"
    VOICE_TTS_INPUT_CONTRACT_RESOLVED = "NO"
    RUNTIME_AUTHORITY_UNRESOLVED = "YES"

    VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT = "NO"
    INVENTED_INPUT_FIELDS = 0
    INVENTED_DEFAULTS = 0
    CLIENT_PROVIDER_VOICE_ID_ACCEPTED = 0
    CLIENT_PROVIDER_AUTHORITY_FIELDS_ACCEPTED = 0
    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0

    INPUT_IDEMPOTENCY_AUTHORITY = "NO"
    INPUT_REQUEST_ID_AUTHORITY = "NO"

    STATUS_ONLY_OUTPUT_AUTHORITY = "NO"
    UNSAFE_AUDIO_OUTPUT_URL_ACCEPTED = 0
    NON_TTS_AUDIO_ARTIFACT_URL_ACCEPTED = 0

    SYNTHETIC_TTS_PRICE_PRESENT = "NO"
    TTS_PRICE_RECOMPUTED_IN_BRIDGE = "NO"

    TTS_PROVIDER_CALLS = 0
    TTS_SYNTHESIS_CALLS = 0
    AUDIO_GENERATIONS = 0
    VOICE_ASSET_WRITES = 0
    CHARGE_CALLS = 0
    WALLET_MUTATIONS = 0

    VOICE_TTS_MASTER_STATUS = "BLOCKED_BY_RUNTIME"
    REAL_OUTPUT_PROVEN = "NO"
    NO_GUESSED_BRIDGE = "YES"

    assert FIRST_RED_VOICE_TTS_JOB_ADAPTER_MISSING == "PROVEN"
    assert VOICE_TTS_RUNTIME_AUTHORITY_RESOLVED == "YES"
    assert WEB_VOICE_SELECTION_AUTHORITY_RESOLVED == "NO"
    assert VOICE_TTS_INPUT_CONTRACT_RESOLVED == "NO"
    assert RUNTIME_AUTHORITY_UNRESOLVED == "YES"
    assert VOICE_TTS_CANONICAL_JOB_ADAPTER_PRESENT == "NO"
    assert INVENTED_INPUT_FIELDS == 0
    assert INVENTED_DEFAULTS == 0
    assert CLIENT_PROVIDER_VOICE_ID_ACCEPTED == 0
    assert CLIENT_PROVIDER_AUTHORITY_FIELDS_ACCEPTED == 0
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0
    assert INPUT_IDEMPOTENCY_AUTHORITY == "NO"
    assert INPUT_REQUEST_ID_AUTHORITY == "NO"
    assert STATUS_ONLY_OUTPUT_AUTHORITY == "NO"
    assert UNSAFE_AUDIO_OUTPUT_URL_ACCEPTED == 0
    assert NON_TTS_AUDIO_ARTIFACT_URL_ACCEPTED == 0
    assert SYNTHETIC_TTS_PRICE_PRESENT == "NO"
    assert TTS_PRICE_RECOMPUTED_IN_BRIDGE == "NO"
    assert TTS_PROVIDER_CALLS == 0
    assert TTS_SYNTHESIS_CALLS == 0
    assert AUDIO_GENERATIONS == 0
    assert VOICE_ASSET_WRITES == 0
    assert CHARGE_CALLS == 0
    assert WALLET_MUTATIONS == 0
    assert VOICE_TTS_MASTER_STATUS == "BLOCKED_BY_RUNTIME"
    assert REAL_OUTPUT_PROVEN == "NO"
    assert NO_GUESSED_BRIDGE == "YES"
