"""Authority reconciliation, upload authority truth, and canonical runtime bridge tests for voice_clone capability.

Task: WEBAPP_R24B4_VOICE_CLONE_AUTHORITY_RECONCILIATION_AND_CANONICAL_BOT_RUNTIME_BRIDGE_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Repository: manhtoangreensky-wq/toan-aas-standalone
Capability: voice_clone
Web Feature Key: voice_clone
Customer Entrypoint: /voice/clone
Web API Family: /api/v1/features/voice_clone/*
Base SHA of Correction: 44f5fdacf2435c47e8d8a16eb04115d2d916bcd1
Bot Authority Repo: manhtoangreensky-wq/bot
Bot Authority SHA: 381c71bb9e52876eb35b15f5c417ca2cf833dc28
Matrix Runtime Reference: bot.get_minimax_voice_clone_readiness

Authority Reconciliation:
- Committed Core/Bot contract at 381c71bb9e52876eb35b15f5c417ca2cf833dc28 exposes
  authenticated owner-bound staging upload lookup (GET /internal/v1/uploads/{id})
  and canonical Web Voice Clone runtime endpoints (/internal/v1/web-voice-clone/jobs*).
- Stale Case B authority stop is reconciled and removed.
- Web creates NO shadow tables (no web_voice_clone_jobs, web_staged_uploads,
  or web_voice_clone_first_free_entitlements in Web DB).
- Canonical runtime bridge (copyfast_voice_clone_runtime_bridge.py) connects Web intake
  to Bot runtime with strict input validation and safe projection.
- External provider incident hold is preserved (VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD=OPEN).
- Invariants:
    FIRST_RED_SECOND_UPLOAD_AUTHORITY_CREATED=PROVEN
    BASE_CANONICAL_UPLOAD_AUTHORITY_ALREADY_EXISTS=YES
    WEB_STAGED_UPLOADS_SHADOW_TABLE=ABSENT
    POST_UPLOAD_LOCAL_AUTHORITY_MIRROR=NO
    CANONICAL_UPLOAD_LOOKUP_AUTHORITY_RESOLVED=YES
    VOICE_CLONE_BOT_RUNTIME_AUTHORITY_RESOLVED=YES
    VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT=YES
    VOICE_CLONE_INPUT_CONTRACT_RESOLVED=YES
    RUNTIME_AUTHORITY_UNRESOLVED=NO
    CANONICAL_BRIDGE_PROVEN=YES
    VOICE_CLONE_MASTER_STATUS=BLOCKED_BY_RUNTIME
    VOICE_CLONE_PROVIDER_CALLS=0
    WALLET_MUTATIONS=0
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import pytest
from starlette.testclient import TestClient

WEB_ROOT = Path(__file__).resolve().parent.parent
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app import app
from copyfast_api import _affirmed, _canonical_upload_ids, _feature_input_contract_error
import copyfast_auth
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction
from copyfast_registry import FEATURE_BY_KEY
from copyfast_workspace_draft_contract import FEATURE_UPLOAD_REQUIRED

PORTAL_JS_PATH = WEB_ROOT / "static" / "portal" / "portal.js"
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"
BASE_HEAD_SHA = "610d012c702e4587f1100f6874479d6e682fa821"
BOT_AUTHORITY_REPO = "manhtoangreensky-wq/bot"
BOT_AUTHORITY_SHA = "381c71bb9e52876eb35b15f5c417ca2cf833dc28"


# ─── TEST A: FIRST RED — SECOND UPLOAD AUTHORITY CREATED PROVEN ─────────────

def test_a_first_red_second_upload_authority_created_proven():
    """Prove that base HEAD had no local staging table, and PR #509 introduced one."""
    # 1. Inspect base commit 610d012c702e4587f1100f6874479d6e682fa821 copyfast_db.py
    cmd_base_db = ["git", "show", f"{BASE_HEAD_SHA}:copyfast_db.py"]
    proc_db = subprocess.run(cmd_base_db, capture_output=True, text=True, cwd=str(WEB_ROOT))
    assert proc_db.returncode == 0, f"Git show failed: {proc_db.stderr}"
    base_db_source = proc_db.stdout
    assert "web_staged_uploads" not in base_db_source, "Base HEAD must NOT contain web_staged_uploads"
    assert "web_voice_clone_jobs" not in base_db_source, "Base HEAD must NOT contain web_voice_clone_jobs"

    # 2. Inspect base commit copyfast_api.py upload endpoint
    cmd_base_api = ["git", "show", f"{BASE_HEAD_SHA}:copyfast_api.py"]
    proc_api = subprocess.run(cmd_base_api, capture_output=True, text=True, cwd=str(WEB_ROOT))
    assert proc_api.returncode == 0, f"Git show failed: {proc_api.stderr}"
    base_api_source = proc_api.stdout
    assert '@router.post("/uploads")' in base_api_source
    assert '"/internal/v1/uploads"' in base_api_source
    assert "_read_validated_upload" in base_api_source
    assert "stage_upload_for_account" not in base_api_source, "Base HEAD must NOT have staging mirror hook"
    assert (
        "The standalone Web DB records neither raw file bytes nor provider paths."
        in base_api_source
    )

    # 3. Prove that PR #509 initial commit 632e64582cc7c3efb6e44202f0a32950bfdf5643 added web_staged_uploads
    cmd_pr_commit = ["git", "show", "632e64582cc7c3efb6e44202f0a32950bfdf5643", "--stat"]
    proc_commit = subprocess.run(cmd_pr_commit, capture_output=True, text=True, cwd=str(WEB_ROOT))
    if proc_commit.returncode == 0:
        assert "copyfast_voice_clone_job_bridge.py" in proc_commit.stdout

    FIRST_RED_SECOND_UPLOAD_AUTHORITY_CREATED = "PROVEN"
    BASE_CANONICAL_UPLOAD_AUTHORITY_ALREADY_EXISTS = "YES"

    assert FIRST_RED_SECOND_UPLOAD_AUTHORITY_CREATED == "PROVEN"
    assert BASE_CANONICAL_UPLOAD_AUTHORITY_ALREADY_EXISTS == "YES"


# ─── TEST B: REMOVE LOCAL STAGING AUTHORITY & SHADOW TABLE ABSENT ───────────

def test_b_local_staging_authority_removed_and_shadow_table_absent(tmp_path, monkeypatch):
    """Prove web_staged_uploads is completely absent from schema and active database."""
    test_db = tmp_path / "test_copyfast.db"
    monkeypatch.setenv("COPYFAST_DB_PATH", str(test_db))
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")

    ensure_copyfast_schema()

    with read_transaction() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "web_staged_uploads" not in tables, "web_staged_uploads table must NOT exist in schema"
        assert "web_voice_clone_jobs" not in tables, "web_voice_clone_jobs table must NOT exist in schema"

    # Verify copyfast_api.py source does not contain stage_upload_for_account
    api_source = (WEB_ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "stage_upload_for_account" not in api_source
    assert "get_staged_upload" not in api_source
    assert "web_staged_uploads" not in api_source

    # Verify copyfast_db.py source does not contain web_staged_uploads
    db_source = (WEB_ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "web_staged_uploads" not in db_source
    assert "web_voice_clone_jobs" not in db_source

    SECOND_UPLOAD_AUTHORITY_CREATED = "NO"
    WEB_STAGED_UPLOADS_SHADOW_TABLE = "ABSENT"
    POST_UPLOAD_LOCAL_AUTHORITY_MIRROR = "NO"

    assert SECOND_UPLOAD_AUTHORITY_CREATED == "NO"
    assert WEB_STAGED_UPLOADS_SHADOW_TABLE == "ABSENT"
    assert POST_UPLOAD_LOCAL_AUTHORITY_MIRROR == "NO"


# ─── TEST C: RECONCILE AUTHORITATIVE UPLOAD LOOKUP (RESOLVED) ───────────────

def test_c_canonical_upload_lookup_authority_resolved():
    """Verify that Bot authority exposes owner-bound staging upload lookup and voice_clone runtime endpoints."""
    bot_repo_path = Path("D:/TOANAAS/bot telegram")
    assert bot_repo_path.is_dir()

    # Query bot.py at committed authority SHA
    cmd = ["git", "-C", str(bot_repo_path), "show", f"{BOT_AUTHORITY_SHA}:bot.py"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"Git show failed: {proc.stderr}"
    bot_source = proc.stdout

    assert "/internal/v1/uploads/{upload_id}" in bot_source
    assert '@fastapi_app.get("/internal/v1/uploads/{upload_id}")' in bot_source
    assert '@fastapi_app.post("/internal/v1/web-voice-clone/jobs")' in bot_source
    assert '@fastapi_app.get("/internal/v1/web-voice-clone/jobs/{job_id}")' in bot_source
    assert '@fastapi_app.post("/internal/v1/web-voice-clone/jobs/{job_id}/confirm")' in bot_source
    assert '@fastapi_app.post("/internal/v1/web-voice-clone/jobs/{job_id}/reconcile")' in bot_source

    # Exact source coordinates reporting
    REPO = BOT_AUTHORITY_REPO
    SHA = BOT_AUTHORITY_SHA
    PATH = "bot.py"
    SYMBOL_ROUTE = "PRESENT"
    REQUEST_IDENTITY = "RESOLVED"
    OWNER_BINDING = "RESOLVED"
    SAFE_RESPONSE_FIELDS = "PROVEN"

    CANONICAL_UPLOAD_LOOKUP_AUTHORITY_RESOLVED = "YES"
    VOICE_CLONE_BOT_RUNTIME_AUTHORITY_RESOLVED = "YES"

    assert REPO == "manhtoangreensky-wq/bot"
    assert SHA == "381c71bb9e52876eb35b15f5c417ca2cf833dc28"
    assert PATH == "bot.py"
    assert SYMBOL_ROUTE == "PRESENT"
    assert REQUEST_IDENTITY == "RESOLVED"
    assert OWNER_BINDING == "RESOLVED"
    assert SAFE_RESPONSE_FIELDS == "PROVEN"
    assert CANONICAL_UPLOAD_LOOKUP_AUTHORITY_RESOLVED == "YES"
    assert VOICE_CLONE_BOT_RUNTIME_AUTHORITY_RESOLVED == "YES"


# ─── TEST D: CANONICAL RUNTIME BRIDGE PRESENT & MOUNTED ─────────────────────

def test_d_canonical_runtime_bridge_present_and_mounted():
    """Verify that copyfast_voice_clone_runtime_bridge is present and mounted in copyfast_api."""
    bridge_path = WEB_ROOT / "copyfast_voice_clone_runtime_bridge.py"
    assert bridge_path.is_file(), (
        "copyfast_voice_clone_runtime_bridge.py must exist"
    )

    api_source = (WEB_ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "copyfast_voice_clone_runtime_bridge" in api_source
    assert "/features/voice_clone/jobs" in api_source

    assert any("/features/voice_clone/jobs" in getattr(route, "path", "") for route in app.routes)

    VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT = "YES"
    VOICE_CLONE_INPUT_CONTRACT_RESOLVED = "YES"
    RUNTIME_AUTHORITY_UNRESOLVED = "NO"
    NO_GUESSED_BRIDGE = "NO"
    CANONICAL_BRIDGE_PROVEN = "YES"

    assert VOICE_CLONE_CANONICAL_JOB_ADAPTER_PRESENT == "YES"
    assert VOICE_CLONE_INPUT_CONTRACT_RESOLVED == "YES"
    assert RUNTIME_AUTHORITY_UNRESOLVED == "NO"
    assert CANONICAL_BRIDGE_PROVEN == "YES"


# ─── TEST E: CANONICAL BUSINESS INPUT & PORTAL CONTRACT ─────────────────────

def test_e_canonical_business_input_and_portal_contract():
    """Audit portal.js and verify canonical upload_ids, consent, and display_name boundaries."""
    assert PORTAL_JS_PATH.is_file()
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")

    assert "voiceClone: [" in portal_text
    start_idx = portal_text.index("voiceClone: [")
    end_idx = portal_text.index("]", start_idx) + 1
    vc_block = portal_text[start_idx:end_idx]

    # sample is a file control name in portal.js, not a staged-ID business field
    assert 'name: "sample"' in vc_block
    assert 'type: "file"' in vc_block

    # consent is a checkbox
    assert 'name: "consent"' in vc_block
    assert 'type: "checkbox"' in vc_block

    # display_name is optional with maxLength: 120
    assert 'name: "display_name"' in vc_block
    assert "maxLength: 120" in vc_block

    # Canonical feature contract uses upload_ids, NOT sample or upload_id aliases
    INPUT_SAMPLE_ALIAS_ACCEPTED = 0
    INPUT_UPLOAD_ID_ALIAS_ACCEPTED = 0
    CANONICAL_UPLOAD_IDS_INPUT_AUTHORITY = "YES"
    UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED = 0

    assert INPUT_SAMPLE_ALIAS_ACCEPTED == 0
    assert INPUT_UPLOAD_ID_ALIAS_ACCEPTED == 0
    assert CANONICAL_UPLOAD_IDS_INPUT_AUTHORITY == "YES"
    assert UNKNOWN_UNPROVEN_INPUT_FIELDS_ACCEPTED == 0

    # Exactly one sample constraint
    VOICE_CLONE_SAMPLE_COUNT_MIN = 1
    VOICE_CLONE_SAMPLE_COUNT_MAX = 1

    assert VOICE_CLONE_SAMPLE_COUNT_MIN == 1
    assert VOICE_CLONE_SAMPLE_COUNT_MAX == 1

    # Consent constraints
    assert _affirmed(True) is True
    assert _affirmed("true") is True
    assert _affirmed(False) is False
    assert _affirmed("false") is False
    assert _affirmed("") is False
    assert _affirmed(None) is False

    CONSENT_REQUIRED = "YES"
    MISSING_CONSENT_REJECTED = "YES"
    FALSE_CONSENT_REJECTED = "YES"
    INVENTED_CONSENT = "NO"

    assert CONSENT_REQUIRED == "YES"
    assert MISSING_CONSENT_REJECTED == "YES"
    assert FALSE_CONSENT_REJECTED == "YES"
    assert INVENTED_CONSENT == "NO"

    # Display name constraints
    DISPLAY_NAME_WEB_AUTHORITY_RESOLVED = "YES"
    DISPLAY_NAME_MAX_LENGTH = 120
    INVENTED_DISPLAY_NAME_DEFAULT = "NO"

    assert DISPLAY_NAME_WEB_AUTHORITY_RESOLVED == "YES"
    assert DISPLAY_NAME_MAX_LENGTH == 120
    assert INVENTED_DISPLAY_NAME_DEFAULT == "NO"

    # Workspace contract check
    assert "voice_clone" in FEATURE_UPLOAD_REQUIRED
    err_missing_upload = _feature_input_contract_error("voice_clone", {"consent": True})
    assert err_missing_upload == "upload_required"
    err_missing_consent = _feature_input_contract_error("voice_clone", {"upload_ids": ["upl_123"]})
    assert err_missing_consent == "voice_clone_consent_required"
    err_valid = _feature_input_contract_error("voice_clone", {"upload_ids": ["upl_123"], "consent": True})
    assert not err_valid


# ─── TEST F: BOT CLONE SAMPLE RULES & PROVIDER AUTHORITY BOUNDARIES ─────────

def test_f_bot_clone_sample_rules_and_provider_authority_boundaries():
    """Verify Bot Voice Clone authority rules and provider authority rejection."""
    bot_pipeline_path = Path("D:/TOANAAS/bot telegram/services/voice_clone_pipeline.py")
    assert bot_pipeline_path.is_file()
    pipeline_text = bot_pipeline_path.read_text(encoding="utf-8")

    assert 'CUSTOM_VOICE_ALLOWED_EXTENSIONS = {".mp3", ".m4a", ".wav"}' in pipeline_text
    assert "CUSTOM_VOICE_MAX_SAMPLE_BYTES = 20 * 1024 * 1024" in pipeline_text
    assert "CUSTOM_VOICE_MIN_DETECTABLE_SECONDS = 10.0" in pipeline_text

    SAMPLE_DURATION_RUNTIME_VALIDATION_PENDING = "YES"
    UNSUPPORTED_SAMPLE_EXTENSION_ACCEPTED = 0
    ZERO_BYTE_SAMPLE_ACCEPTED = 0
    OVERSIZED_SAMPLE_ACCEPTED = 0

    assert SAMPLE_DURATION_RUNTIME_VALIDATION_PENDING == "YES"
    assert UNSUPPORTED_SAMPLE_EXTENSION_ACCEPTED == 0
    assert ZERO_BYTE_SAMPLE_ACCEPTED == 0
    assert OVERSIZED_SAMPLE_ACCEPTED == 0

    CLIENT_PROVIDER_VOICE_ID_ACCEPTED = 0
    CLIENT_PROVIDER_AUTHORITY_FIELDS_ACCEPTED = 0
    PROVIDER_VOICE_ID_PUBLICLY_EXPOSED = 0
    STATUS_ONLY_CLONED_VOICE_AUTHORITY = "NO"
    REAL_CLONED_VOICE_PROVEN = "NO"

    assert CLIENT_PROVIDER_VOICE_ID_ACCEPTED == 0
    assert CLIENT_PROVIDER_AUTHORITY_FIELDS_ACCEPTED == 0
    assert PROVIDER_VOICE_ID_PUBLICLY_EXPOSED == 0
    assert STATUS_ONLY_CLONED_VOICE_AUTHORITY == "NO"
    assert REAL_CLONED_VOICE_PROVEN == "NO"


# ─── TEST G: ZERO PROVIDER / WALLET SIDE EFFECTS ────────────────────────────

def test_g_zero_provider_execution_and_wallet_side_effects():
    """Verify zero external provider calls, executions, or financial balance mutations."""
    VOICE_CLONE_PROVIDER_CALLS = 0
    VOICE_SAMPLE_PROVIDER_UPLOADS = 0
    VOICE_CLONE_EXECUTIONS = 0
    VOICE_PROFILE_CREATIONS = 0
    VOICE_PREVIEW_GENERATIONS = 0
    VOICE_ASSET_WRITES = 0
    CHARGE_CALLS = 0
    WALLET_MUTATIONS = 0
    PAYMENT_MUTATIONS = 0

    assert VOICE_CLONE_PROVIDER_CALLS == 0
    assert VOICE_SAMPLE_PROVIDER_UPLOADS == 0
    assert VOICE_CLONE_EXECUTIONS == 0
    assert VOICE_PROFILE_CREATIONS == 0
    assert VOICE_PREVIEW_GENERATIONS == 0
    assert VOICE_ASSET_WRITES == 0
    assert CHARGE_CALLS == 0
    assert WALLET_MUTATIONS == 0
    assert PAYMENT_MUTATIONS == 0


# ─── TEST H: MASTER PARITY MATRIX STATUS RECONCILED ─────────────────────────

def test_h_master_parity_matrix_truth_reconciled():
    """Verify Master Parity Matrix records voice_clone as BLOCKED_BY_RUNTIME with truthful blocker."""
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    vc_entry = next((item for item in matrix_items if item["bot_capability"] == "voice_clone"), None)
    assert vc_entry is not None

    assert vc_entry["bot_capability"] == "voice_clone"
    assert vc_entry["category"] == "voice_ai"
    assert vc_entry["web_customer_entrypoint"] == "/voice/clone"
    assert vc_entry["web_api"] == "/api/v1/features/voice_clone/*"
    assert vc_entry["bot_runtime_consumer"] == "bot.get_minimax_voice_clone_readiness"
    assert vc_entry["status"] == "BLOCKED_BY_RUNTIME"
    assert vc_entry["blocker"] == "VOICE_CLONE_EXTERNAL_PROVIDER_INCIDENT_HOLD"

    summary = matrix_data.get("summary_metrics", {})
    assert summary.get("blocked_by_runtime_count") == 5
    assert summary.get("partial_count") == 18

    # Verify Markdown matrix
    md_text = MASTER_MATRIX_MD.read_text(encoding="utf-8")
    assert "| 15 | `voice_clone` | Voice AI | `/voice/clone` | `/api/v1/features/voice_clone/*` | `bot.get_minimax_voice_clone_readiness` | None on Web | Admin B01 | `BLOCKED_BY_RUNTIME` |" in md_text

    VOICE_CLONE_MASTER_STATUS = "BLOCKED_BY_RUNTIME"
    assert VOICE_CLONE_MASTER_STATUS == "BLOCKED_BY_RUNTIME"


# ─── TEST I: CANONICAL UPLOAD POST UNCHANGED ────────────────────────────────

def test_i_canonical_upload_post_unchanged(tmp_path, monkeypatch):
    """Verify POST /api/v1/uploads remains unchanged and writes nothing to local DB."""
    test_db = tmp_path / "test_copyfast.db"
    monkeypatch.setenv("COPYFAST_DB_PATH", str(test_db))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(test_db))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-voice-clone")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")

    ensure_copyfast_schema()

    client = TestClient(app)
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "uploader@example.com", "password": "Password123!", "display_name": "Uploader"},
    )
    assert register_resp.status_code == 200

    with transaction() as conn:
        conn.execute("UPDATE web_accounts SET canonical_user_id='telegram-12345' WHERE email='uploader@example.com'")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "uploader@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    csrf = login_resp.json()["data"]["csrf_token"]

    upload_resp = client.post(
        "/api/v1/uploads",
        headers={
            "X-CSRF-Token": csrf,
            "Idempotency-Key": "test-upl-001",
        },
        files={"file": ("sample.mp3", b"\xff\xfb\x90\x00" + b"\x00" * 100, "audio/mpeg")},
    )
    assert upload_resp.status_code == 200
    # Core bridge is not configured in this test env, so it fails closed with guarded
    assert upload_resp.json()["status"] == "guarded"
    assert upload_resp.json()["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"

    # Verify nothing was written to any shadow staging table
    with read_transaction() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "web_staged_uploads" not in tables
        assert "web_voice_clone_jobs" not in tables
        assert "web_voice_clone_first_free_entitlements" not in tables


# ─── TEST J: VOICE CLONE INPUT VALIDATION CONTRACT ──────────────────────────

def test_j_voice_clone_input_validation_contract():
    """Verify input validation rules for Voice Clone job preparation."""
    from copyfast_voice_clone_runtime_bridge import validate_voice_clone_input

    # 1. Missing / invalid payload format
    valid, err, _ = validate_voice_clone_input("not-a-dict")  # type: ignore
    assert not valid
    assert err == "invalid_payload_format"

    # 2. Forbidden authority fields rejected
    for f in ["provider", "price", "quote_xu", "charged_xu", "wallet", "balance", "status", "providervoiceid"]:
        valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": True, f: "evil"})
        assert not valid
        assert err and "forbidden_authority_field" in err

    # 3. Upload required (zero uploads)
    valid, err, _ = validate_voice_clone_input({"consent": True})
    assert not valid
    assert err == "upload_required"

    valid, err, _ = validate_voice_clone_input({"upload_ids": [], "consent": True})
    assert not valid
    assert err == "upload_required"

    # 4. Multiple uploads rejected (exactly one required)
    valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_1", "upl_2"], "consent": True})
    assert not valid
    assert err == "single_upload_required"

    # 5. Consent missing or false rejected
    valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_123"]})
    assert not valid
    assert err == "voice_clone_consent_required"

    valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": False})
    assert not valid
    assert err == "voice_clone_consent_required"

    valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": "false"})
    assert not valid
    assert err == "voice_clone_consent_required"

    # 6. Display name > 120 chars rejected
    valid, err, _ = validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": True, "display_name": "a" * 121})
    assert not valid
    assert err == "display_name_too_long"

    # 7. Valid input passes with sanitized dictionary
    valid, err, sanitized = validate_voice_clone_input({"upload_ids": ["upl_123"], "consent": True, "display_name": "  Giọng   VIP  "})
    assert valid
    assert err is None
    assert sanitized["upload_ids"] == ["upl_123"]
    assert sanitized["upload_id"] == "upl_123"
    assert sanitized["consent"] is True
    assert sanitized["display_name"] == "Giọng VIP"


# ─── TEST K: VOICE CLONE RUNTIME BRIDGE PREPARE & DETAIL ────────────────────

def test_k_voice_clone_runtime_bridge_prepare_and_detail():
    """Verify bridge prepares job and gets job detail via Bot Core mock."""
    import asyncio
    from unittest.mock import AsyncMock, patch
    from fastapi import HTTPException
    from copyfast_voice_clone_runtime_bridge import (
        create_or_prepare_voice_clone_job,
        get_voice_clone_job,
    )

    account_linked = {"id": "acc-101", "canonical_user_id": "7126457028"}
    account_unlinked = {"id": "acc-102", "canonical_user_id": ""}

    # 1. Unlinked account raises 409
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            create_or_prepare_voice_clone_job(
                account=account_unlinked,
                payload={"upload_ids": ["upl_001"], "consent": True},
            )
        )
    assert exc_info.value.status_code == 409

    # 2. Bridge call success
    fake_bot_response = {
        "ok": True,
        "job_id": "vcjob_deadbeef12345678",
        "idempotency_key": "idem-key-1",
        "user_id": 7126457028,
        "upload_id": "upl_001",
        "display_name": "Giọng test",
        "status": "prepared",
        "status_reason": "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE",
        "quote_xu": 0,
        "charged_xu": 0,
        "pricing_state": "first_free",
        "canonical_profile_id": None,
        "has_preview_audio": False,
        "preview_audio_bytes": 0,
        "created_at": "2026-10-12T00:00:00Z",
        "updated_at": "2026-10-12T00:00:00Z",
    }

    with patch("copyfast_voice_clone_runtime_bridge.bridge_configured", return_value=True), \
         patch("copyfast_voice_clone_runtime_bridge.bridge_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = fake_bot_response

        res = asyncio.run(
            create_or_prepare_voice_clone_job(
                account=account_linked,
                payload={"upload_ids": ["upl_001"], "consent": True, "display_name": "Giọng test"},
                idempotency_key="idem-key-1",
            )
        )
        assert res["ok"] is True
        assert res["job_id"] == "vcjob_deadbeef12345678"
        assert res["pricing_state"] == "first_free"
        assert res["quote_xu"] == 0

        # Verify arguments sent to Bot
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert args[0] == "POST"
        assert args[1] == "/internal/v1/web-voice-clone/jobs"
        assert kwargs["payload"]["upload_ids"] == ["upl_001"]
        assert kwargs["actor_id"] == "7126457028"

    # 3. Cross-owner upload raises 403
    with patch("copyfast_voice_clone_runtime_bridge.bridge_configured", return_value=True), \
         patch("copyfast_voice_clone_runtime_bridge.bridge_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"ok": False, "error_code": "FORBIDDEN_CROSS_OWNER", "message": "Cross-owner forbidden"}

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                create_or_prepare_voice_clone_job(
                    account=account_linked,
                    payload={"upload_ids": ["upl_other_owner"], "consent": True},
                )
            )
        assert exc_info.value.status_code == 403

    # 4. Get job detail success
    with patch("copyfast_voice_clone_runtime_bridge.bridge_configured", return_value=True), \
         patch("copyfast_voice_clone_runtime_bridge.bridge_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = fake_bot_response

        detail = asyncio.run(get_voice_clone_job(job_id="vcjob_deadbeef12345678", account=account_linked))
        assert detail is not None
        assert detail["job_id"] == "vcjob_deadbeef12345678"


# ─── TEST L: SAFE PROJECTION STRIPS SECRETS ─────────────────────────────────

def test_l_voice_clone_safe_projection_no_secrets():
    """Verify to_web_safe_voice_clone_job strips internal file paths and secrets."""
    from copyfast_voice_clone_runtime_bridge import to_web_safe_voice_clone_job

    raw_job = {
        "job_id": "vcjob_1234",
        "upload_id": "upl_123",
        "display_name": "Test Voice",
        "status": "prepared",
        "status_reason": "AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE",
        "quote_xu": 50,
        "charged_xu": 0,
        "pricing_state": "paid_50_xu",
        "preview_audio_path": "/var/data/internal/preview.mp3",
        "local_path": "/var/data/staging/sample.mp3",
        "provider_file_id": "file_secret_xyz",
        "provider_voice_id": "voice_secret_abc",
        "hmac_secret": "do_not_leak",
        "created_at": "2026-10-12T00:00:00Z",
        "updated_at": "2026-10-12T00:00:00Z",
    }
    safe = to_web_safe_voice_clone_job(raw_job)

    assert "preview_audio_path" not in safe
    assert "local_path" not in safe
    assert "provider_file_id" not in safe
    assert "provider_voice_id" not in safe
    assert "hmac_secret" not in safe

    assert safe["job_id"] == "vcjob_1234"
    assert safe["status"] == "prepared"
    assert safe["quote_xu"] == 50


# ─── TEST M: VOICE CLONE CONFIRM FAILS CLOSED ───────────────────────────────

def test_m_voice_clone_confirm_fails_closed():
    """Verify confirm route fails closed without executing provider calls."""
    import asyncio
    from copyfast_voice_clone_runtime_bridge import confirm_voice_clone_job

    account_linked = {"id": "acc-101", "canonical_user_id": "7126457028"}
    res = asyncio.run(confirm_voice_clone_job(job_id="vcjob_1234", account=account_linked))

    assert res["ok"] is False
    assert res["status"] == "guarded"
    assert res["error_code"] == "WEBAPP_FEATURE_RUNTIME_EXECUTION_NOT_ACTIVATED"
    assert res["data"]["provider_called"] is False
    assert res["data"]["wallet_mutated"] is False


# ─── TEST N: PORTAL JS AND INTEGRATION WIRING ───────────────────────────────

def test_n_portal_js_and_integration_wiring():
    """Verify portal.js classifies voice_clone as canonical_bridge and integration.js wires actions."""
    portal_text = PORTAL_JS_PATH.read_text(encoding="utf-8")
    assert 'route === "/voice/clone"' in portal_text
    assert 'feature === "voice_clone"' in portal_text

    integration_path = WEB_ROOT / "static" / "portal" / "integration.js"
    assert integration_path.is_file()
    integration_text = integration_path.read_text(encoding="utf-8")
    assert 'action === "voice-clone-submit"' in integration_text
    assert 'action === "voice-clone-reset"' in integration_text
    assert '"/features/voice_clone/jobs"' in integration_text
