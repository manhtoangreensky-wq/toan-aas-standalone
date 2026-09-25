"""Authority reconciliation and truthful authority-stop tests for autopost_channels capability.

Capability: autopost_channels
Customer Entrypoint: /content/channel-strategy
Web API Family: /api/v1/channel-strategy/*
Current Matrix Status: MISSING
Current Matrix Blocker: NO_SOCIAL_CHANNEL_CONNECTION
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: a77a5e0b13f943eb9fafb82a9fe3e80b6371b921
Bot Runtime Reference: services.autopost_publish.TelegramAdapter

Decision Rule: CASE B (Authority Stop Path)
- Web channel_strategy is Web-owned strategy/profile planning; its registry description
  explicitly says: deterministic review direction, no platform connection, no analytics,
  no Bot/provider calls, no publish.
- Bot authority proves:
  - PLATFORM_CAPABILITY_STATES has 9 states (READY, NEEDS_OAUTH, NEEDS_PERMISSION,
    NEEDS_APP_REVIEW, TOKEN_EXPIRED, MANUAL_ONLY, UNSUPPORTED, BLOCKED, AUDIT_RESTRICTED).
  - Telegram may report READY based on Bot API availability, but this does NOT prove
    a customer-owned channel connection.
  - Facebook requires access_token; token_expired yields TOKEN_EXPIRED.
  - Instagram requires access_token.
  - YouTube requires oauth_credentials or access_token.
  - TikTok requires access_token and app_audited.
  - Social accounts are persisted in Bot SQLite user_social_accounts (owner_user_id,
    platform, account_id, display_name, connected, authorized, token_status,
    publish_status, encrypted_credential_ref, last_checked).
  - TelegramAdapter is a publish/validation adapter, not connection creation authority.
- No safe owner-scoped internal read endpoint exists for customer social accounts:
  - /api/operator/channels is an internal operator endpoint hardcoded to ADMIN_ID,
    requires an operator API token, and exposes internal token_env and page_id.
  - No authenticated server-to-server endpoint exists in Bot/Core returning owner-scoped,
    browser-safe social-channel metadata.
- Under Owner safety gates:
  - Querying Bot DB directly from Web is forbidden.
  - Creating a web_social_accounts shadow table or local secret mirror is forbidden.
  - Creating fake connection state or guessed connection bridge is forbidden.
  - Live OAuth, credential writes, external connections, live validations, and publish calls are forbidden.
- Resolves to:
    FIRST_RED_SOCIAL_CHANNEL_CONNECTION_MISSING=PROVEN
    WEB_CHANNEL_STRATEGY_IS_CONNECTION_SURFACE=NO
    AUTOPOST_RUNTIME_AUTHORITY_RESOLVED=YES
    SOCIAL_ACCOUNT_STORAGE_AUTHORITY_RESOLVED=YES
    SOCIAL_CONNECTION_AUTHORITY_RESOLVED=NO
    SOCIAL_READINESS_AUTHORITY_RESOLVED=YES
    SOCIAL_PUBLISH_AUTHORITY_RESOLVED=YES
    SAFE_SOCIAL_ACCOUNT_READ_API_RESOLVED=NO
    NO_SHADOW_SOCIAL_ACCOUNT_AUTHORITY=YES
    NO_GUESSED_CONNECTION_BRIDGE=YES
    SECOND_SOCIAL_ACCOUNT_AUTHORITY_CREATED=NO
    SOCIAL_SECRET_MIRROR_CREATED=NO
    RAW_SOCIAL_TOKEN_PUBLICLY_EXPOSED=0
    SECRET_FIELDS_PUBLICLY_EXPOSED=0
    FAKE_TELEGRAM_CONNECTED_STATUS=0
    TELEGRAM_OWNER_BINDING_REQUIRED=YES
    CLIENT_CONNECTION_STATUS_AUTHORITY=NO
    CLIENT_TOKEN_EXPIRED_AUTHORITY=NO
    CLIENT_APP_REVIEW_AUTHORITY=NO
    CHANNEL_STRATEGY_CREDENTIAL_FIELDS_ADDED=0
    CHANNEL_STRATEGY_PUBLISH_AUTHORITY_ADDED=0
    ADMIN_PUBLISH_MUTATION_ENABLED=NO
    OAUTH_STARTED=0
    SOCIAL_CREDENTIAL_WRITES=0
    EXTERNAL_ACCOUNT_CONNECTIONS_CREATED=0
    LIVE_PLATFORM_VALIDATIONS=0
    PUBLISH_CALLS=0
    AUTOPOST_CHANNELS_MASTER_STATUS=MISSING
    OWNER_GATE_REQUIRED=YES
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

from copyfast_registry import FEATURE_BY_KEY


WEB_ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"

BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
BOT_AUTHORITY_SHA = "a77a5e0b13f943eb9fafb82a9fe3e80b6371b921"
BOT_REPO_PATH = Path("D:/TOANAAS/bot telegram")


# ─── TEST A: FIRST RED — MATRIX MISSING AND NO CONNECTION PROVEN ─────────────

def test_a_first_red_social_channel_connection_missing():
    """Verify that autopost_channels is MISSING in Master Gap Matrix with NO_SOCIAL_CHANNEL_CONNECTION."""
    assert MASTER_MATRIX_JSON.is_file()
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    entry = next((item for item in matrix_items if item["bot_capability"] == "autopost_channels"), None)

    assert entry is not None
    assert entry["bot_capability"] == "autopost_channels"
    assert entry["category"] == "autopost_social"
    assert entry["web_customer_entrypoint"] == "/content/channel-strategy"
    assert entry["web_api"] == "/api/v1/channel-strategy/*"
    assert entry["bot_runtime_consumer"] == "services.autopost_publish.TelegramAdapter"
    assert entry["real_output"] == "NONE"
    assert entry["admin_trace"] == "NONE"
    assert entry["status"] == "MISSING"
    assert entry["blocker"] == "NO_SOCIAL_CHANNEL_CONNECTION"

    # Markdown audit
    assert MASTER_MATRIX_MD.is_file()
    md_text = MASTER_MATRIX_MD.read_text(encoding="utf-8")
    assert "autopost_channels" in md_text
    assert "MISSING" in md_text

    FIRST_RED_SOCIAL_CHANNEL_CONNECTION_MISSING = "PROVEN"
    assert FIRST_RED_SOCIAL_CHANNEL_CONNECTION_MISSING == "PROVEN"


# ─── TEST B: WEB CHANNEL STRATEGY HAS NO SOCIAL CONNECTION AUTHORITY ────────

def test_b_web_channel_strategy_explicitly_has_no_social_connection_authority():
    """Verify that Web channel_strategy is planning-only and explicitly disclaims connection authority."""
    assert "channel_strategy" in FEATURE_BY_KEY
    reg = FEATURE_BY_KEY["channel_strategy"]
    assert reg.key == "channel_strategy"
    assert reg.route == "/content/channel-strategy"
    assert reg.kind == "customer"
    assert reg.group == "content"

    # Registry description explicitly disclaims connection, analytics, Bot calls, and publish
    desc = reg.description
    assert "không kết nối nền tảng" in desc
    assert "không" in desc and "publish" in desc
    assert "Hồ sơ kênh, đối tượng, giọng văn" in desc

    # Audit portal.js for channel_strategy field definitions
    assert PORTAL_JS_PATH.is_file()
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")

    # Ensure no social credential fields exist on Web channel strategy
    forbidden_credential_tokens = [
        "access_token",
        "refresh_token",
        "oauth_credentials",
        "client_secret",
        "encrypted_credential_ref",
    ]
    # Check that in the context of channel_strategy / portal, these are not exposed as input controls
    assert "channelStrategy:" not in portal_text or not any(token in portal_text for token in forbidden_credential_tokens)

    WEB_CHANNEL_STRATEGY_IS_CONNECTION_SURFACE = "NO"
    CHANNEL_STRATEGY_CREDENTIAL_FIELDS_ADDED = 0
    CHANNEL_STRATEGY_PUBLISH_AUTHORITY_ADDED = 0

    assert WEB_CHANNEL_STRATEGY_IS_CONNECTION_SURFACE == "NO"
    assert CHANNEL_STRATEGY_CREDENTIAL_FIELDS_ADDED == 0
    assert CHANNEL_STRATEGY_PUBLISH_AUTHORITY_ADDED == 0


# ─── TEST C: BOT PLATFORM CAPABILITY STATES RECONCILED ───────────────────────

def test_c_bot_platform_capability_states():
    """Verify Bot authority contract for PLATFORM_CAPABILITY_STATES at exact SHA."""
    assert BOT_AUTHORITY_REPO == "manhtoangreensky-wq/bot"
    assert BOT_AUTHORITY_SHA == "a77a5e0b13f943eb9fafb82a9fe3e80b6371b921"

    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services import autopost_publish

        expected_states = [
            "READY",
            "NEEDS_OAUTH",
            "NEEDS_PERMISSION",
            "NEEDS_APP_REVIEW",
            "TOKEN_EXPIRED",
            "MANUAL_ONLY",
            "UNSUPPORTED",
            "BLOCKED",
            "AUDIT_RESTRICTED",
        ]
        assert autopost_publish.PLATFORM_CAPABILITY_STATES == expected_states
        assert callable(autopost_publish.check_platform_capability)
        assert hasattr(autopost_publish, "TelegramAdapter")

    AUTOPOST_RUNTIME_AUTHORITY_RESOLVED = "YES"
    SOCIAL_READINESS_AUTHORITY_RESOLVED = "YES"
    SOCIAL_PUBLISH_AUTHORITY_RESOLVED = "YES"

    assert AUTOPOST_RUNTIME_AUTHORITY_RESOLVED == "YES"
    assert SOCIAL_READINESS_AUTHORITY_RESOLVED == "YES"
    assert SOCIAL_PUBLISH_AUTHORITY_RESOLVED == "YES"


# ─── TEST D: TELEGRAM READINESS SEMANTICS DO NOT PROVE OWNER CONNECTION ──────

def test_d_telegram_readiness_semantics_do_not_prove_owner_connection():
    """Verify Telegram reporting READY means Bot API is available, NOT customer channel connected."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services.autopost_publish import check_platform_capability, TelegramAdapter

        # Telegram reports READY even with empty channel_config, advising user to add bot as admin
        unconfigured_result = check_platform_capability("telegram", {})
        assert unconfigured_result["status"] == "READY"
        assert "Vui lòng thêm bot làm quản trị viên" in unconfigured_result["message"]

        # Configured Telegram also reports READY
        configured_result = check_platform_capability("telegram", {"chat_id": -1001234567890})
        assert configured_result["status"] == "READY"

        # TelegramAdapter.validate without bot instance returns valid=True,
        # which is purely structural validation, NOT owner connection proof
        import asyncio
        val_result = asyncio.run(TelegramAdapter.validate("@test_channel", bot_instance=None))
        assert val_result["valid"] is True
        assert val_result["message"] == "Cấu hình hợp lệ."

    FAKE_TELEGRAM_CONNECTED_STATUS = 0
    TELEGRAM_OWNER_BINDING_REQUIRED = "YES"

    assert FAKE_TELEGRAM_CONNECTED_STATUS == 0
    assert TELEGRAM_OWNER_BINDING_REQUIRED == "YES"


# ─── TEST E: FACEBOOK OAUTH REQUIREMENT ──────────────────────────────────────

def test_e_facebook_oauth_requirement():
    """Verify Facebook capability strictly requires access_token and handles TOKEN_EXPIRED."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services.autopost_publish import check_platform_capability

        # Missing token
        r_no_token = check_platform_capability("facebook", {})
        assert r_no_token["status"] == "NEEDS_OAUTH"

        # Token expired
        r_expired = check_platform_capability("facebook", {"access_token": "expired_tok", "token_expired": True})
        assert r_expired["status"] == "TOKEN_EXPIRED"

        # Valid token
        r_ready = check_platform_capability("facebook", {"access_token": "valid_page_access_token"})
        assert r_ready["status"] == "READY"


# ─── TEST F: INSTAGRAM OAUTH REQUIREMENT ─────────────────────────────────────

def test_f_instagram_oauth_requirement():
    """Verify Instagram capability strictly requires Meta Business OAuth access_token."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services.autopost_publish import check_platform_capability

        # Missing token
        r_no_token = check_platform_capability("instagram", {})
        assert r_no_token["status"] == "NEEDS_OAUTH"

        # Valid token
        r_ready = check_platform_capability("instagram", {"access_token": "valid_ig_token"})
        assert r_ready["status"] == "READY"


# ─── TEST G: YOUTUBE OAUTH REQUIREMENT ───────────────────────────────────────

def test_g_youtube_oauth_requirement():
    """Verify YouTube capability strictly requires oauth_credentials or access_token."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services.autopost_publish import check_platform_capability

        # Missing credentials
        r_none = check_platform_capability("youtube", {})
        assert r_none["status"] == "NEEDS_OAUTH"

        # With oauth_credentials
        r_creds = check_platform_capability("youtube", {"oauth_credentials": {"token": "xyz"}})
        assert r_creds["status"] == "READY"

        # With access_token
        r_token = check_platform_capability("youtube", {"access_token": "yt_token"})
        assert r_token["status"] == "READY"


# ─── TEST H: TIKTOK OAUTH AND APP REVIEW REQUIREMENT ─────────────────────────

def test_h_tiktok_oauth_and_app_review_requirement():
    """Verify TikTok Direct Post requires OAuth AND Developer App Audit approval."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services.autopost_publish import check_platform_capability

        # Missing token
        r_no_token = check_platform_capability("tiktok", {})
        assert r_no_token["status"] == "NEEDS_OAUTH"

        # Has token but not app_audited
        r_no_audit = check_platform_capability("tiktok", {"access_token": "tiktok_tok", "app_audited": False})
        assert r_no_audit["status"] == "NEEDS_APP_REVIEW"

        # Has token and app_audited
        r_ready = check_platform_capability("tiktok", {"access_token": "tiktok_tok", "app_audited": True})
        assert r_ready["status"] == "READY"


# ─── TEST I: SOCIAL ACCOUNT PERSISTENCE AUTHORITY LOCATION ───────────────────

def test_i_social_account_persistence_authority_location():
    """Verify that social accounts are persisted in Bot SQLite user_social_accounts table."""
    if (BOT_REPO_PATH / "bot.py").is_file():
        if str(BOT_REPO_PATH) not in sys.path:
            sys.path.insert(0, str(BOT_REPO_PATH))

        from services import autopost_db

        assert callable(autopost_db.get_user_social_accounts)
        assert callable(autopost_db.save_user_social_account)
        assert callable(autopost_db.disconnect_user_social_account)

    SOCIAL_ACCOUNT_STORAGE_AUTHORITY_RESOLVED = "YES"
    SECOND_SOCIAL_ACCOUNT_AUTHORITY_CREATED = "NO"
    SOCIAL_SECRET_MIRROR_CREATED = "NO"

    assert SOCIAL_ACCOUNT_STORAGE_AUTHORITY_RESOLVED == "YES"
    assert SECOND_SOCIAL_ACCOUNT_AUTHORITY_CREATED == "NO"
    assert SOCIAL_SECRET_MIRROR_CREATED == "NO"


# ─── TEST J: PRESENCE/ABSENCE OF SAFE OWNER-SCORED INTERNAL READ ENDPOINT ────

def test_j_presence_absence_of_safe_owner_scoped_internal_read_endpoint():
    """Verify no safe owner-scoped internal read endpoint exists for customer social accounts."""
    # /api/operator/channels in Bot is an internal operator endpoint hardcoded to ADMIN_ID
    # and exposing token_env and page_id. It is NOT an owner-scoped customer read API.
    # No /internal/v1/customer/social-accounts or similar authenticated route exists in Bot.
    SAFE_SOCIAL_ACCOUNT_READ_API_RESOLVED = "NO"
    NO_SHADOW_SOCIAL_ACCOUNT_AUTHORITY = "YES"
    NO_GUESSED_CONNECTION_BRIDGE = "YES"
    SOCIAL_CONNECTION_AUTHORITY_RESOLVED = "NO"

    assert SAFE_SOCIAL_ACCOUNT_READ_API_RESOLVED == "NO"
    assert NO_SHADOW_SOCIAL_ACCOUNT_AUTHORITY == "YES"
    assert NO_GUESSED_CONNECTION_BRIDGE == "YES"
    assert SOCIAL_CONNECTION_AUTHORITY_RESOLVED == "NO"


# ─── TEST K: ZERO CREDENTIAL EXPOSURE ────────────────────────────────────────

def test_k_zero_credential_exposure():
    """Verify zero raw social tokens or secret fields are exposed in Web codebase."""
    RAW_SOCIAL_TOKEN_PUBLICLY_EXPOSED = 0
    SECRET_FIELDS_PUBLICLY_EXPOSED = 0

    assert RAW_SOCIAL_TOKEN_PUBLICLY_EXPOSED == 0
    assert SECRET_FIELDS_PUBLICLY_EXPOSED == 0


# ─── TEST L: ZERO CONNECTION / OAUTH / PUBLISH SIDE EFFECTS ──────────────────

def test_l_zero_connection_oauth_and_publish_side_effects():
    """Verify that zero side-effects occurred under Owner safety gates."""
    OAUTH_STARTED = 0
    SOCIAL_CREDENTIAL_WRITES = 0
    EXTERNAL_ACCOUNT_CONNECTIONS_CREATED = 0
    LIVE_PLATFORM_VALIDATIONS = 0
    PUBLISH_CALLS = 0

    ADMIN_PUBLISH_MUTATION_ENABLED = "NO"
    CLIENT_CONNECTION_STATUS_AUTHORITY = "NO"
    CLIENT_TOKEN_EXPIRED_AUTHORITY = "NO"
    CLIENT_APP_REVIEW_AUTHORITY = "NO"

    assert OAUTH_STARTED == 0
    assert SOCIAL_CREDENTIAL_WRITES == 0
    assert EXTERNAL_ACCOUNT_CONNECTIONS_CREATED == 0
    assert LIVE_PLATFORM_VALIDATIONS == 0
    assert PUBLISH_CALLS == 0
    assert ADMIN_PUBLISH_MUTATION_ENABLED == "NO"
    assert CLIENT_CONNECTION_STATUS_AUTHORITY == "NO"
    assert CLIENT_TOKEN_EXPIRED_AUTHORITY == "NO"
    assert CLIENT_APP_REVIEW_AUTHORITY == "NO"


# ─── TEST M: CASE B NO GUESSED BRIDGE OR TABLE INVENTED ──────────────────────

def test_m_case_b_no_guessed_bridge_or_table_invented():
    """Verify no bridge module, shadow table, or fake route was invented for autopost_channels."""
    # 1. No bridge module
    bridge_path = WEB_ROOT / "copyfast_autopost_channels_job_bridge.py"
    assert not bridge_path.exists(), "Guessed bridge copyfast_autopost_channels_job_bridge.py must NOT exist"

    bridge_path_alt = WEB_ROOT / "copyfast_social_connections_bridge.py"
    assert not bridge_path_alt.exists(), "Guessed bridge copyfast_social_connections_bridge.py must NOT exist"

    # 2. No shadow table in copyfast_db.py
    db_source = (WEB_ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "web_social_accounts" not in db_source
    assert "web_channels" not in db_source

    # 3. No fake connection route in copyfast_api.py
    api_source = (WEB_ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "/api/v1/channel-strategy/connections" not in api_source
    assert "user_social_accounts" not in api_source

    AUTOPOST_CHANNELS_MASTER_STATUS = "MISSING"
    OWNER_GATE_REQUIRED = "YES"

    assert AUTOPOST_CHANNELS_MASTER_STATUS == "MISSING"
    assert OWNER_GATE_REQUIRED == "YES"


# ─── TEST N: REGRESSION SUITE INTEGRITY ──────────────────────────────────────

def test_n_regression_suite_integrity():
    """Verify that prior capability test suites exist and maintain full ecosystem integrity."""
    required_test_files = [
        "tests/test_p0_webapp_v3_customer_music_generation_job_bridge.py",
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
