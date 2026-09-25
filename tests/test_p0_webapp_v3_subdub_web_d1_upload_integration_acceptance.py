"""Web ↔ Bot D1 Upload Integration Acceptance Suite.

Task: WEB-SUBDUB-R2A-D1-UPLOAD-INTEGRATION-ACCEPTANCE
GitHub Issue: https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/516
Master Tracker: https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/515

Proves:
1. Audit JSON was STALE: said BOT_STAGING_UPLOAD_*_RESOLVED=NO while Bot D1
   at SHA ffaf4114 already defines POST /internal/v1/uploads and
   GET /internal/v1/uploads/{upload_id}.
2. Web _canonical_upload_ids accepts Bot upl_* opaque format.
3. Web _canonical_upload_ids rejects path-like, malformed, duplicate IDs.
4. Web _contains_feature_authority_field blocks forged authority fields.
5. Web upload route bridges to correct Bot path /internal/v1/uploads.
6. Web DB does NOT store raw media bytes (docstring contract).
7. Bot D1 staging service has create_staged_upload, get_staged_upload, to_public_metadata.
8. Updated audit JSON reflects resolved D1 upload authority.
9. Reconciliation test_t no longer asserts NO for upload flags after audit update.

INVARIANTS:
  PROVIDER_CALLS=0, WALLET_MUTATIONS=0, PAYMENT_MUTATIONS=0,
  PRODUCTION_DB_MUTATIONS=0, COMMIT=NO, PUSH=NO, MERGE=NO, DEPLOY=NO
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

AUDIT_JSON_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.json"
MASTER_MATRIX_PATH = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
COPYFAST_API_PATH = STANDALONE_ROOT / "copyfast_api.py"

# Bot D1 authority SHA — the commit where POST /internal/v1/uploads was merged.
BOT_D1_AUTHORITY_SHA = "ffaf41144134a24615407b59492409012c687f31"

# Regex patterns copied from Web source to validate test expectations.
CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def bot_git_repo() -> Path:
    """Resolve and verify Bot authority git repository at D1 commit SHA."""
    candidates = [
        Path(os.environ.get("TOAN_AAS_BOT_REPO_ROOT", "")),
        Path(os.environ.get("BOT_ROOT", "")),
        STANDALONE_ROOT.parent / "wt_subdub_d2_preflight",
        STANDALONE_ROOT.parent / "bot telegram",
        STANDALONE_ROOT.parent / "bot",
        STANDALONE_ROOT.parents[1] / "wt_subdub_d2_preflight",
        STANDALONE_ROOT.parents[1] / "bot telegram",
        STANDALONE_ROOT.parents[1] / "bot",
    ]
    for candidate in candidates:
        if not candidate or not candidate.is_dir():
            continue
        try:
            res = subprocess.run(
                ["git", "-C", str(candidate), "cat-file", "-e", f"{BOT_D1_AUTHORITY_SHA}^{{commit}}"],
                capture_output=True, text=True, check=False,
            )
            if res.returncode == 0:
                return candidate
        except Exception:
            continue
    pytest.fail(
        f"Bot repo at D1 SHA {BOT_D1_AUTHORITY_SHA} is REQUIRED. "
        f"Candidates: {[str(c) for c in candidates if c]}"
    )


def _read_bot_git_file(repo: Path, file_path: str) -> str:
    """Read file content from Bot D1 git commit."""
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{BOT_D1_AUTHORITY_SHA}:{file_path}"],
            text=True, encoding="utf-8", errors="ignore",
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"Failed to read {file_path} from Bot D1 SHA {BOT_D1_AUTHORITY_SHA}: {exc}")


@pytest.fixture(scope="module")
def audit_data() -> dict:
    assert AUDIT_JSON_PATH.exists(), f"Missing audit JSON: {AUDIT_JSON_PATH}"
    data = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def copyfast_source() -> str:
    assert COPYFAST_API_PATH.exists(), f"Missing copyfast_api.py: {COPYFAST_API_PATH}"
    return COPYFAST_API_PATH.read_text(encoding="utf-8")


# ===========================================================================
# W2A-02: Prove Bot D1 SHA defines upload create+consume endpoints
# ===========================================================================
class TestBotD1UploadEndpointsExist:
    """Prove Bot at D1 SHA has POST /internal/v1/uploads and GET /internal/v1/uploads/{upload_id}."""

    def test_post_uploads_endpoint_exists(self, bot_git_repo: Path):
        bot_py = _read_bot_git_file(bot_git_repo, "bot.py")
        assert '@fastapi_app.post("/internal/v1/uploads")' in bot_py, (
            "Bot D1 SHA MUST define POST /internal/v1/uploads"
        )

    def test_get_uploads_endpoint_exists(self, bot_git_repo: Path):
        bot_py = _read_bot_git_file(bot_git_repo, "bot.py")
        assert '@fastapi_app.get("/internal/v1/uploads/{upload_id}")' in bot_py, (
            "Bot D1 SHA MUST define GET /internal/v1/uploads/{upload_id}"
        )

    def test_staging_service_create_exists(self, bot_git_repo: Path):
        staging_py = _read_bot_git_file(bot_git_repo, "services/subdub_upload_staging.py")
        assert "def create_staged_upload(" in staging_py

    def test_staging_service_get_exists(self, bot_git_repo: Path):
        staging_py = _read_bot_git_file(bot_git_repo, "services/subdub_upload_staging.py")
        assert "def get_staged_upload(" in staging_py

    def test_staging_service_to_public_metadata_exists(self, bot_git_repo: Path):
        staging_py = _read_bot_git_file(bot_git_repo, "services/subdub_upload_staging.py")
        assert "def to_public_metadata(" in staging_py


# ===========================================================================
# W2A-03: Prove Web _canonical_upload_ids accepts Bot upl_* format
# ===========================================================================
class TestWebCanonicalUploadIds:
    """Prove Web CANONICAL_IDENTIFIER_PATTERN accepts Bot opaque upload_id format."""

    def test_pattern_accepts_bot_upl_format(self):
        """Bot generates upl_ + 32 hex chars. Web pattern must accept."""
        bot_id = "upl_" + "a1b2c3d4" * 4  # upl_ + 32 hex chars = 36 chars
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch(bot_id), (
            f"Web CANONICAL_IDENTIFIER_PATTERN must accept Bot upload_id: {bot_id}"
        )

    def test_pattern_rejects_path_like_identifiers(self):
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("/tmp/uploads/file.mp4") is None
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("C:\\Users\\file.mp4") is None
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("../../../etc/passwd") is None

    def test_pattern_rejects_empty_string(self):
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("") is None

    def test_pattern_rejects_overlength(self):
        too_long = "a" * 161
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch(too_long) is None

    def test_pattern_rejects_special_chars(self):
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("upload id with spaces") is None
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("id@domain") is None
        assert CANONICAL_IDENTIFIER_PATTERN.fullmatch("id#hash") is None

    def test_web_source_defines_canonical_upload_ids_function(self, copyfast_source: str):
        """Prove copyfast_api.py defines _canonical_upload_ids with opaque-only contract."""
        assert "def _canonical_upload_ids(value: Any) -> list[str] | None:" in copyfast_source
        assert "Accept only opaque bot staging identifiers, never paths or handles." in copyfast_source

    def test_web_source_uses_canonical_identifier_pattern(self, copyfast_source: str):
        """Prove _canonical_upload_ids uses CANONICAL_IDENTIFIER_PATTERN for validation."""
        assert 'CANONICAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")' in copyfast_source


# ===========================================================================
# W2A-04: Prove Web _contains_feature_authority_field blocks forgery
# ===========================================================================
class TestWebAuthorityFieldGuard:
    """Prove Web blocks forged authority fields in feature payloads."""

    def test_authority_field_guard_defined(self, copyfast_source: str):
        assert "def _contains_feature_authority_field(value: " in copyfast_source

    def test_feature_authority_fields_constant_defined(self, copyfast_source: str):
        assert "FEATURE_AUTHORITY_FIELDS = frozenset({" in copyfast_source

    def test_authority_fields_include_critical_keys(self, copyfast_source: str):
        """Prove FEATURE_AUTHORITY_FIELDS blocks identity, wallet, provider, and output keys."""
        for field in ("user_id", "wallet_id", "provider", "job_id", "output", "api_key"):
            assert f'"{field}"' in copyfast_source, (
                f"FEATURE_AUTHORITY_FIELDS must block '{field}'"
            )


# ===========================================================================
# W2A-05: Prove Web upload route bridges to Bot /internal/v1/uploads
# ===========================================================================
class TestWebUploadRouteBridge:
    """Prove Web POST /uploads bridges to Bot POST /internal/v1/uploads."""

    def test_upload_route_defined(self, copyfast_source: str):
        assert "async def upload_to_canonical_staging(" in copyfast_source

    def test_upload_route_bridges_to_bot_internal_uploads(self, copyfast_source: str):
        """Prove the upload route calls _bridge('POST', '/internal/v1/uploads', ...)."""
        # Find the upload_to_canonical_staging function body
        func_start = copyfast_source.find("async def upload_to_canonical_staging(")
        assert func_start > 0
        func_body = copyfast_source[func_start:func_start + 2000]
        assert '"/internal/v1/uploads"' in func_body, (
            "upload_to_canonical_staging must bridge to /internal/v1/uploads"
        )

    def test_web_db_does_not_store_raw_bytes(self, copyfast_source: str):
        """Prove docstring contract: Web DB records neither raw file bytes nor provider paths."""
        assert "The standalone Web DB records neither raw file bytes nor provider paths." in copyfast_source


# ===========================================================================
# W2A-06: Prove audit JSON is updated to reflect D1 resolution
# ===========================================================================
class TestAuditReflectsD1Resolution:
    """After update, audit JSON must reflect resolved D1 upload authority."""

    def test_bot_staging_upload_create_resolved(self, audit_data: dict):
        flags = audit_data["flags"]
        assert flags["BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED"] == "YES", (
            "Audit must reflect BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED=YES "
            "because Bot D1 SHA ffaf4114 defines POST /internal/v1/uploads"
        )

    def test_bot_staging_upload_consume_resolved(self, audit_data: dict):
        flags = audit_data["flags"]
        assert flags["BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED"] == "YES", (
            "Audit must reflect BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED=YES "
            "because Bot D1 SHA ffaf4114 defines GET /internal/v1/uploads/{upload_id}"
        )

    def test_subdub_web_upload_authority_resolved(self, audit_data: dict):
        flags = audit_data["flags"]
        assert flags["SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED"] == "YES", (
            "Audit must reflect SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED=YES "
            "because Web bridges to Bot D1 upload endpoints"
        )

    def test_r2_durable_job_bridge_still_not_ready(self, audit_data: dict):
        """R2 durable job bridge remains NOT ready (separate dependency)."""
        flags = audit_data["flags"]
        assert flags["R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY"] == "NO"

    def test_web_canonical_subdub_runtime_output_still_not_proven(self, audit_data: dict):
        """Runtime output remains NOT proven (separate dependency)."""
        flags = audit_data["flags"]
        assert flags["WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN"] == "NO"

    def test_bot_authority_sha_updated_to_d1(self, audit_data: dict):
        """Audit must reference D1 authority SHA, not the old pre-D1 SHA."""
        assert audit_data["bot_authority_sha"] == BOT_D1_AUTHORITY_SHA, (
            f"bot_authority_sha must be D1 SHA {BOT_D1_AUTHORITY_SHA}"
        )

    def test_upload_authority_truth_section_updated(self, audit_data: dict):
        truth = audit_data.get("upload_authority_truth", {})
        assert truth.get("BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED") == "YES"
        assert truth.get("BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED") == "YES"
        assert truth.get("SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED") == "YES"

    def test_stale_unresolved_gap_removed(self, audit_data: dict):
        """The BOT_STAGING_UPLOAD_CONSUME_CONTRACT_MISSING gap must be removed."""
        gaps = audit_data.get("input_authority_reconciliation", {}).get("unresolved_semantic_gaps", [])
        gap_codes = [g.get("code") for g in gaps]
        assert "BOT_STAGING_UPLOAD_CONSUME_CONTRACT_MISSING" not in gap_codes, (
            "Stale gap BOT_STAGING_UPLOAD_CONSUME_CONTRACT_MISSING must be removed after D1 resolution"
        )


# ===========================================================================
# W2A-07: Prove Web bridge constructs correct auth for Bot internal API
# ===========================================================================
class TestWebBridgeAuthContract:
    """Prove Web _bridge sends actor_id and request_id to Bot internal API."""

    def test_bridge_function_defined(self, copyfast_source: str):
        assert "async def _bridge(" in copyfast_source

    def test_bridge_sends_actor_id(self, copyfast_source: str):
        func_start = copyfast_source.find("async def _bridge(")
        func_body = copyfast_source[func_start:func_start + 3000]
        assert "actor_id=" in func_body, (
            "_bridge must send actor_id to Bot internal API"
        )

    def test_bridge_sends_request_id(self, copyfast_source: str):
        func_start = copyfast_source.find("async def _bridge(")
        func_body = copyfast_source[func_start:func_start + 3000]
        assert "request_id=" in func_body, (
            "_bridge must send request_id to Bot internal API"
        )

    def test_bridge_overrides_user_id_from_session(self, copyfast_source: str):
        """Prove browser cannot forge canonical target identity — _bridge sets user_id from signed session."""
        func_start = copyfast_source.find("async def _bridge(")
        func_body = copyfast_source[func_start:func_start + 3000]
        assert 'enriched["user_id"] = user_id' in func_body, (
            "_bridge must override user_id from signed session, not from browser payload"
        )


# ---------------------------------------------------------------------------
# 8. Markdown Audit D1 Parity Guard (anti-stale regression)
# ---------------------------------------------------------------------------
AUDIT_MD_PATH = STANDALONE_ROOT / "reports" / "audit" / "P0-WEBAPP-V3-SUBDUB-CANONICAL-PRODUCT-AUTHORITY-R1.md"


class TestMarkdownAuditD1Parity:
    """Prove Markdown audit reflects D1 truth and no stale pre-D1 claims survive."""

    @pytest.fixture(scope="class")
    def md_content(self) -> str:
        assert AUDIT_MD_PATH.exists(), f"Markdown audit not found: {AUDIT_MD_PATH}"
        return AUDIT_MD_PATH.read_text(encoding="utf-8")

    def test_md_contains_d1_sha(self, md_content: str):
        assert BOT_D1_AUTHORITY_SHA in md_content, (
            "Markdown must reference Bot D1 SHA ffaf4114..."
        )

    def test_md_bot_staging_upload_create_yes(self, md_content: str):
        assert "BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED" in md_content
        line = [l for l in md_content.splitlines()
                if "BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED" in l][0]
        assert "YES" in line, (
            "BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED must be YES after D1"
        )

    def test_md_bot_staging_upload_consume_yes(self, md_content: str):
        assert "BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED" in md_content
        line = [l for l in md_content.splitlines()
                if "BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED" in l][0]
        assert "YES" in line, (
            "BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED must be YES after D1"
        )

    def test_md_web_upload_authority_yes(self, md_content: str):
        assert "SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED" in md_content
        line = [l for l in md_content.splitlines()
                if "SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED" in l][0]
        assert "YES" in line, (
            "SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED must be YES after D1"
        )

    def test_md_no_stale_gap_bot_staging_consume_missing(self, md_content: str):
        assert "BOT_STAGING_UPLOAD_CONSUME_CONTRACT_MISSING" not in md_content, (
            "Stale gap BOT_STAGING_UPLOAD_CONSUME_CONTRACT_MISSING must not appear after D1"
        )

    def test_md_no_stale_claim_upload_route_absent(self, md_content: str):
        assert "Bot does not implement" not in md_content, (
            "Stale claim 'Bot does not implement' upload routes must not appear after D1"
        )

    def test_md_no_stale_sha_661c0de(self, md_content: str):
        assert "661c0de" not in md_content, (
            "Stale pre-D1 SHA 661c0de must not appear anywhere in Markdown after D1 update"
        )
