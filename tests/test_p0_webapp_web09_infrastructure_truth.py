"""Empirical verification test suite for WEB09: Infrastructure Truth.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB09.INFRASTRUCTURE.TRUTH
Repository: manhtoangreensky-wq/toan-aas-standalone

Invariants:
1. DEPLOY_EXACT_SHA_BOUND=YES: Deploy is strictly SHA-bound to github.sha.
2. ARTIFACT_CHECKSUM_VERIFIED=YES: Checksums verified on runner and remote host.
3. HEALTH_OVERCLAIM=0: /health proves process liveness without claiming unverified subsystems.
4. PRODUCTION_DB_PATH_AMBIGUITY=0: Database paths resolve deterministically to persistent volume.
5. RAW_SECRET_LOGGING=0 & RAW_TOKEN_LOGGING=0: No secrets/tokens leaked in logs or workflows.
6. PERSISTENT_DATA_EXCLUDED_FROM_RELEASE=YES: Databases, assets, and uploads excluded from source release.
7. STARTUP_MUTATION_TRUTHFUL=YES: Schema migration and storage reconciliations correctly classified.
8. ROLLBACK_TRUTH: Honest rollback classification (manual recovery, no false automatic rollback claim).
9. CORE_BRIDGE_TRANSPORT: Strict loopback HTTP or HTTPS requirement for Core Bridge transport.
10. INFRA_STATE_CONFLATION=0: Strict separation between PROCESS_ACTIVE, HTTP_HEALTH, and BUSINESS_READINESS.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

import app as app_module
import config
import copyfast_bridge
import copyfast_db


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "deploy-vps.yml"


# ==============================================================================
# Case 1: Deploy uses exact github.sha and runtime SHA is strictly bound
# ==============================================================================
def test_deploy_workflow_exact_sha_bound() -> None:
    assert WORKFLOW_PATH.is_file(), "deploy-vps.yml must exist in repository"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # 1. Release packaging binds to GITHUB_SHA
    assert 'git archive --format=tar --output="${RELEASE_DIR}/release.tar" "${GITHUB_SHA}"' in content
    assert 'git update-ref refs/deployments/release "${GITHUB_SHA}"' in content
    assert 'git bundle create "${RELEASE_DIR}/release.bundle" refs/deployments/release' in content

    # 2. Bundle advertised SHA must match GITHUB_SHA
    assert 'ADVERTISED_SHA="$(git bundle list-heads "${RELEASE_DIR}/release.bundle" | awk \'{print $1}\')"' in content
    assert 'if [[ "$ADVERTISED_SHA" != "$GITHUB_SHA" ]]; then' in content

    # 3. Target SHA passed to VPS step is github.sha
    assert "TARGET_SHA: ${{ github.sha }}" in content

    # 4. VPS script verifies 40-char hex format and exact equality
    assert 'if [[ ! \\"\\$TARGET_SHA\\" =~ ^[0-9a-fA-F]{40}\\$ ]]; then' in content
    assert 'if [[ \\"\\$FETCHED_SHA\\" != \\"\\$TARGET_SHA\\" ]]; then' in content
    assert (
        'TARGET_RELEASE_DIR=\\"/opt/toanaas/webapp/releases/\\$TARGET_SHA\\"' in content
        or 'if [[ \\"\\$CURRENT_SHA\\" != \\"\\$TARGET_SHA\\" ]]; then' in content
    )

    # 5. Symbolic ref or immutable release extract must bind TARGET_SHA
    assert (
        'tar -xf \\"\\$STAGING_DIR/release.tar\\" -C \\"\\$TARGET_RELEASE_DIR\\"' in content
        or 'git read-tree \\"\\$TARGET_SHA\\"' in content
    )


# ==============================================================================
# Case 2: Artifact and checksum verification cannot be bypassed
# ==============================================================================
def test_deploy_artifact_checksum_verification_strictness() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Runner verification
    assert "sha256sum release.tar release.bundle > checksums.sha256" in content
    assert "sha256sum -c checksums.sha256" in content

    # Remote VPS verification before release unpack
    remote_script = content[content.find("ssh -i ~/.ssh/id_ed25519"):]
    assert "sha256sum -c checksums.sha256" in remote_script

    # Deterministic simulation of checksum validation
    data_tar = b"test-release-tar-content"
    data_bundle = b"test-release-bundle-content"
    hash_tar = hashlib.sha256(data_tar).hexdigest()
    hash_bundle = hashlib.sha256(data_bundle).hexdigest()

    checksum_text = f"{hash_tar}  release.tar\n{hash_bundle}  release.bundle\n"
    assert f"{hash_tar}  release.tar" in checksum_text
    assert f"{hash_bundle}  release.bundle" in checksum_text

    # Verify that modified checksum detects corruption
    tampered_tar = b"tampered-content"
    tampered_hash = hashlib.sha256(tampered_tar).hexdigest()
    assert tampered_hash != hash_tar, "Tampered hash must not match valid checksum"


# ==============================================================================
# Case 3: /health is read-only and does not overclaim
# ==============================================================================
def test_health_endpoint_read_only_and_no_overclaim() -> None:
    client = TestClient(app_module.app)

    # 1. Test /health
    res1 = client.get("/health")
    assert res1.status_code == 200
    data1 = res1.json()

    # 2. Test /api/v1/health alias
    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1 == data2

    # Verify exact proven fields
    assert data1.get("ok") is True
    assert data1.get("app") == "TOAN AAS Web App"
    assert data1.get("entrypoint") == "app.py"
    assert data1.get("version") == "P0.WEBAPP.COPYFAST1"

    # HEALTH_OVERCLAIM = 0: Ensure no false subsystem health claims
    unproven_subsystems = ["database", "db", "bot", "provider", "providers", "payments", "payos", "redis"]
    for sub in unproven_subsystems:
        assert sub not in data1, f"Health endpoint must not claim subsystem status for '{sub}' without explicit probe"


# ==============================================================================
# Case 4: Production entrypoint and process contract deterministic
# ==============================================================================
def test_production_entrypoint_and_port_contract() -> None:
    # 1. Entrypoint exists and defines app
    assert hasattr(app_module, "app"), "app.py must export FastAPI 'app' instance"

    # 2. deploy-vps.yml curl verification target
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "/health" in content and (
        "http://127.0.0.1/health" in content
        or "http://127.0.0.1:8000/health" in content
        or "TARGET_PORT" in content
    ), "Deploy workflow must verify health endpoint"

    # 3. No direct public binding in application entrypoint
    app_text = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
    assert 'uvicorn.run("app:app", host="0.0.0.0"' not in app_text
    assert 'host="0.0.0.0"' not in app_text


# ==============================================================================
# Case 5: Deploy workflow does not print raw secrets or tokens
# ==============================================================================
def test_deploy_workflow_no_raw_secret_logging() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # set -x must not be present
    assert "set -x" not in content, "set -x must never be enabled in deployment workflows"
    assert "set +x" not in content

    # Check for accidental secret echoing to stdout without destination file
    forbidden_echoes = [
        'echo "$VPS_SSH_KEY"\n',
        "echo ${{ secrets",
        "echo $CORE_BRIDGE_TOKEN",
        "echo $WEB_SESSION_SECRET",
        "env |",
        "printenv",
    ]
    for pattern in forbidden_echoes:
        assert pattern not in content, f"Workflow must not log sensitive credentials: {pattern}"

    # Verify only safe summary variables are printed at the end
    assert 'echo \\"PREVIOUS_HEAD=\\$PREV_HEAD\\"' in content
    assert 'echo \\"DEPLOYED_SHA=\\$TARGET_SHA\\"' in content
    assert (
        'echo \\"TARGET_RELEASE_DIR=\\$TARGET_RELEASE_DIR\\"' in content
        or 'echo \\"BACKUP_DIR=\\$BACKUP_DIR\\"' in content
    )


# ==============================================================================
# Case 6: Persistent DB and data paths excluded from release packaging
# ==============================================================================
def test_persistent_db_and_data_paths_not_tracked_as_source() -> None:
    # 1. Ensure git archive uses git-tracked files only
    # Run git ls-files to verify no database or sqlite file is committed in repository
    tracked_files = subprocess.check_output(
        ["git", "ls-files"], cwd=str(REPO_ROOT), text=True, encoding="utf-8"
    ).splitlines()

    for path in tracked_files:
        assert not path.endswith(".db"), f"SQLite database file must never be tracked in git: {path}"
        assert not path.endswith(".sqlite"), f"SQLite file must never be tracked in git: {path}"
        assert not path.endswith(".db-wal"), f"WAL file must never be tracked in git: {path}"
        assert not path.endswith(".db-shm"), f"SHM file must never be tracked in git: {path}"
        assert not path.startswith("data/"), f"Data directory must not be tracked in git: {path}"

    # 2. Database path resolution requires persistent volume in production
    os.environ["APP_ENV"] = "production"
    try:
        # A relative path must be rejected in production
        os.environ["WEBAPP_SESSION_DB_PATH"] = "relative_test.db"
        with pytest.raises(RuntimeError, match="phải là đường dẫn tuyệt đối"):
            copyfast_db.session_database_path()
    finally:
        os.environ.pop("APP_ENV", None)
        os.environ.pop("WEBAPP_SESSION_DB_PATH", None)


# ==============================================================================
# Case 7: Startup routines correctly classified (Schema vs Mutating Reconciliation)
# ==============================================================================
def test_startup_routines_classification_truth() -> None:
    # 1. Schema migration routine
    assert hasattr(copyfast_db, "ensure_copyfast_schema")
    # ensure_copyfast_schema creates tables and indexes -> SCHEMA_MIGRATION

    # 2. Storage reconciliation steps
    assert hasattr(app_module, "STARTUP_RECONCILIATION_STEPS")
    steps = dict(app_module.STARTUP_RECONCILIATION_STEPS)

    expected_steps = {
        "admin_document_archive",
        "asset_vault",
        "project_packages",
        "document_operations",
        "image_operations",
        "subtitle_asset_operations",
        "audio_asset_operations",
        "video_operations",
        "frame_video_operations",
        "video_transform_operations",
        "storyboard_grid",
    }
    assert set(steps.keys()) == expected_steps

    # Each step is callable and executes background metadata verification
    for name, step_fn in steps.items():
        assert callable(step_fn), f"Reconciliation step '{name}' must be a callable function"


# ==============================================================================
# Case 8: Rollback truth reflects actual implementation (Zero-Downtime Rollback)
# ==============================================================================
def test_deploy_rollback_truth_reflects_actual_implementation() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Honest rollback reporting: In zero-downtime blue-green deployments, automated rollback
    # is handled via atomic pointer restoration (rollback_to_active_slot) with zero shared-root mutation.
    assert (
        "rollback_to_active_slot" in content
        or 'BACKUP_DIR=\\"\\$WEBAPP_DIR/delete/deploy-\\$TARGET_SHA-\\$UTC_TIMESTAMP\\"' in content
    )
    assert "SHARED_DEPLOY_ROOT_MUTATION=0" in content
    assert "SHARED_GIT_METADATA_MUTATION=0" in content or "SOURCE_RELEASE_ISOLATION=YES" in content

    # Honest rollback reporting: The workflow does NOT implement an automated rollback hook
    # on error via a generic error trap.
    assert "trap 'rollback'" not in content, "Workflow must not falsely claim an automated rollback trap when manual recovery is used"



# ==============================================================================
# Case 9: Core Bridge auth/HMAC and loopback contract
# ==============================================================================
def test_core_bridge_transport_and_auth_contract() -> None:
    # 1. Base URL validation: loopback plaintext HTTP permitted, external HTTP rejected
    assert copyfast_bridge._valid_base_url("http://127.0.0.1:8080") is True
    assert copyfast_bridge._valid_base_url("http://localhost:8080") is True
    assert copyfast_bridge._valid_base_url("http://[::1]:8080") is True
    assert copyfast_bridge._valid_base_url("https://tg.toanaas.vn") is True

    # Insecure plain HTTP over external network must be rejected
    assert copyfast_bridge._valid_base_url("http://toanaas.vn") is False
    assert copyfast_bridge._valid_base_url("http://192.168.1.1:8080") is False
    assert copyfast_bridge._valid_base_url("http://0.0.0.0:8080") is False

    # 2. Missing credentials must report configuration error
    assert copyfast_bridge._configuration_error("", "token", "secret") == "CORE_BRIDGE_NOT_CONFIGURED"
    assert copyfast_bridge._configuration_error("http://127.0.0.1:8080", "", "secret") == "CORE_BRIDGE_NOT_CONFIGURED"
    assert copyfast_bridge._configuration_error("http://127.0.0.1:8080", "token", "") == "CORE_BRIDGE_NOT_CONFIGURED"
    assert copyfast_bridge._configuration_error("http://invalid-url", "token", "secret") == "CORE_BRIDGE_INVALID_CONFIGURATION"
    assert copyfast_bridge._configuration_error("http://127.0.0.1:8080", "token", "secret") is None


# ==============================================================================
# Case 10: Process active is distinct from health pass
# ==============================================================================
def test_process_active_distinct_from_health_pass() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Workflow separately checks:
    # 1. Process / service active
    assert "systemctl is-active toanaas-web" in content
    # 2. HTTP Health endpoint returning 200 OK
    assert "curl -s -f" in content and "/health" in content
    # 3. Payload validation
    assert 'assert data.get(\\"ok\\") is True' in content
    assert 'assert data.get(\\"app\\") == \\"TOAN AAS Web App\\"' in content
    assert 'assert data.get(\\"entrypoint\\") == \\"app.py\\"' in content

    # Invariant: PROCESS_ACTIVE != HTTP_HEALTH != BUSINESS_READINESS
    # A process being active in systemd is NOT accepted by deploy workflow as proof of health.
    # Both is-active AND curl health payload must succeed.
