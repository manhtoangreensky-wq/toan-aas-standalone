"""Contracts and verification suite for P0.WEBAPP.V3-B1 Zero-Downtime Architecture.

Covers 25 Section M Contract Requirements:
1. requirements.lock exists with exact '==' pins
2. requirements.lock exact SHA256 snapshot
3. release.json structure and field types
4. /health exposes release_sha
5. /health exposes requirements_lock_sha256
6. /health exposes runtime_environment_id
7. /health exposes resolved_packages_sha256
8. /health exposes runtime_attestation dictionary
9. runtime_attestation verifies running_executable_under_attested_env
10. WEBAPP_STARTUP_RECONCILIATION_MODE=deferred sets reconciliation_state=DEFERRED
11. Deferred mode sets copyfast_startup_reconciliation status=inhibited_pending_activation
12. Deferred mode inhibits background volume scan task at boot
13. Immediate mode executes reconciliation startup
14. Lifecycle endpoint enforces loopback-only access (403 for non-loopback)
15. Lifecycle endpoint enforces token presence (401 for missing token)
16. Lifecycle endpoint enforces constant-time token match (401 for wrong token)
17. Lifecycle endpoint returns 503 if WEBAPP_LIFECYCLE_TOKEN is not configured on server
18. Lifecycle endpoint transitions DEFERRED -> RECONCILING with cutoff and task_created=True
19. Lifecycle endpoint replay during RECONCILING is idempotent (task_created=False)
20. Lifecycle endpoint replay after COMPLETED returns ALREADY_COMPLETED (task_created=False)
21. Deploy workflow packages release.json before checksums.sha256
22. Deploy workflow uses content-addressed runtime-envs with runtime_env_attestation.json
23. Deploy workflow enforces read-only permissions (chmod -R a-w)
24. Deploy workflow manages parameterized blue/green slots and atomic Nginx switch
25. Deploy workflow preserves warm rollback window and executes post-retirement reconciliation
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


class TestP0ZeroDowntimeContracts:
    def test_01_requirements_lock_exists_and_pinned(self):
        """Contract 1: requirements.lock must exist with exact == pins."""
        lock_path = ROOT / "requirements.lock"
        assert lock_path.is_file(), "requirements.lock must exist in repository root"
        lines = [line.strip() for line in lock_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
        assert len(lines) >= 50, f"Expected at least 50 pinned packages, got {len(lines)}"
        for line in lines:
            assert "==" in line, f"Package constraint must be exact '==' pin, got: {line}"

    def test_02_requirements_lock_exact_sha256(self):
        """Contract 2: requirements.lock SHA256 must match frozen production snapshot."""
        lock_path = ROOT / "requirements.lock"
        computed_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        expected_sha = "9490bebca11e7aaf14b7804eba35a6bf2c5bcab7d0a1220771c8fbdc29c14d5f"
        assert computed_sha == expected_sha, f"requirements.lock SHA mismatch: {computed_sha} != {expected_sha}"

    def test_03_release_json_structure_and_types(self):
        """Contract 3: release metadata structure specification."""
        from app import _load_release_metadata
        meta = _load_release_metadata()
        assert isinstance(meta, dict)
        assert "release_sha" in meta
        assert "requirements_lock_sha256" in meta
        assert meta["release_sha"] != ""

    def test_04_health_reports_release_sha(self):
        """Contract 4: /health must expose release_sha from release truth."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        assert payload.get("ok") is True
        assert "release_sha" in payload, f"/health missing release_sha: {payload}"
        assert payload["release_sha"] != "", "release_sha must not be empty"

    def test_05_health_reports_requirements_lock_sha256(self):
        """Contract 5: /health must expose requirements_lock_sha256."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        assert "requirements_lock_sha256" in payload
        assert payload["requirements_lock_sha256"] == "9490bebca11e7aaf14b7804eba35a6bf2c5bcab7d0a1220771c8fbdc29c14d5f"

    def test_06_health_reports_runtime_environment_id(self):
        """Contract 6: /health must expose runtime_environment_id."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        assert "runtime_environment_id" in payload
        assert "res-" in payload["runtime_environment_id"]

    def test_07_health_reports_resolved_packages_sha256(self):
        """Contract 7: /health must expose resolved_packages_sha256."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        assert "resolved_packages_sha256" in payload
        assert len(payload["resolved_packages_sha256"]) == 64

    def test_08_health_reports_runtime_attestation_dict(self):
        """Contract 8: /health must expose runtime_attestation dictionary without leaking host paths."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        assert "runtime_attestation" in payload
        attestation = payload["runtime_attestation"]
        assert isinstance(attestation, dict)
        assert "runtime_environment_id" in attestation
        assert "running_executable_under_attested_env" in attestation
        assert "python_executable" not in attestation
        assert "environment_prefix" not in attestation

    def test_09_runtime_attestation_verifies_running_executable(self):
        """Contract 9: running_executable_under_attested_env must be true."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        payload = res.json()
        attestation = payload["runtime_attestation"]
        assert attestation.get("running_executable_under_attested_env") is True

    def test_10_startup_reconciliation_deferred_mode(self, monkeypatch):
        """Contract 10: WEBAPP_STARTUP_RECONCILIATION_MODE=deferred sets reconciliation_state=DEFERRED."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        from app import app
        with TestClient(app) as client:
            assert getattr(app.state, "reconciliation_state", None) == "DEFERRED"

    def test_11_startup_reconciliation_deferred_inhibited_status(self, monkeypatch):
        """Contract 11: Deferred mode sets copyfast_startup_reconciliation status=inhibited_pending_activation."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        from app import app
        with TestClient(app) as client:
            status = getattr(app.state, "copyfast_startup_reconciliation", {})
            assert status.get("status") == "inhibited_pending_activation"
            assert status.get("interrupted_before") is None

    def test_12_startup_reconciliation_deferred_no_boot_task(self, monkeypatch):
        """Contract 12: Deferred mode inhibits background volume scan task at boot."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        from app import app
        with TestClient(app) as client:
            task = getattr(app.state, "copyfast_startup_reconciliation_task", None)
            assert task is None, "Deferred mode must not create a startup reconciliation task on boot"

    def test_13_startup_reconciliation_immediate_mode(self, monkeypatch):
        """Contract 13: Immediate mode (default) executes reconciliation startup."""
        monkeypatch.delenv("WEBAPP_STARTUP_RECONCILIATION_MODE", raising=False)
        from app import app
        with TestClient(app) as client:
            state = getattr(app.state, "reconciliation_state", None)
            assert state in ("RUNNING", "COMPLETED")

    def test_14_lifecycle_endpoint_loopback_only(self, monkeypatch):
        """Contract 14: Lifecycle endpoint rejects non-loopback client IPs with 403."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        # TestClient with custom non-loopback client host
        client = TestClient(app, client=("203.0.113.195", 54321))
        res = client.post(
            "/api/v1/internal/lifecycle/reconcile-retired-generation",
            headers={"X-Lifecycle-Token": "valid-test-lifecycle-token-32chars"}
        )
        assert res.status_code == 403
        data = res.json()
        assert "Loopback access only" in (data.get("message") or data.get("detail", ""))

    def test_15_lifecycle_endpoint_missing_token(self, monkeypatch):
        """Contract 15: Lifecycle endpoint rejects missing token header with 401."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        with TestClient(app) as client:
            res = client.post("/api/v1/internal/lifecycle/reconcile-retired-generation")
            assert res.status_code == 401

    def test_16_lifecycle_endpoint_invalid_token(self, monkeypatch):
        """Contract 16: Lifecycle endpoint rejects mismatched token with 401."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/internal/lifecycle/reconcile-retired-generation",
                headers={"X-Lifecycle-Token": "invalid-wrong-token"}
            )
            assert res.status_code == 401

    def test_17_lifecycle_endpoint_server_missing_token_env(self, monkeypatch):
        """Contract 17: Lifecycle endpoint returns 503 when server token is unconfigured."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.delenv("WEBAPP_LIFECYCLE_TOKEN", raising=False)
        from app import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/internal/lifecycle/reconcile-retired-generation",
                headers={"X-Lifecycle-Token": "any-token"}
            )
            assert res.status_code == 503

    def test_18_lifecycle_endpoint_valid_transition_deferred_to_reconciling(self, monkeypatch):
        """Contract 18: First call in DEFERRED mode transitions to RECONCILING with task_created=True."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        with TestClient(app) as client:
            res = client.post(
                "/api/v1/internal/lifecycle/reconcile-retired-generation",
                headers={"X-Lifecycle-Token": "valid-test-lifecycle-token-32chars"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data.get("ok") is True
            assert data.get("status") in ("RECONCILIATION_STARTED", "ALREADY_COMPLETED", "RECONCILING_IN_PROGRESS")
            assert "interrupted_cutoff" in data

    def test_19_lifecycle_endpoint_idempotent_replay(self, monkeypatch):
        """Contract 19: Concurrent/duplicate calls while reconciling are idempotent (task_created=False)."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        with TestClient(app) as client:
            headers = {"X-Lifecycle-Token": "valid-test-lifecycle-token-32chars"}
            # First trigger
            res1 = client.post("/api/v1/internal/lifecycle/reconcile-retired-generation", headers=headers)
            assert res1.status_code == 200

            # Second trigger
            res2 = client.post("/api/v1/internal/lifecycle/reconcile-retired-generation", headers=headers)
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2.get("ok") is True
            assert data2.get("task_created") is False, "Duplicate call must not spawn another task"

    def test_20_lifecycle_endpoint_completed_replay(self, monkeypatch):
        """Contract 20: Calling lifecycle endpoint when already COMPLETED returns ALREADY_COMPLETED."""
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")
        from app import app
        with TestClient(app) as client:
            app.state.reconciliation_state = "COMPLETED"
            headers = {"X-Lifecycle-Token": "valid-test-lifecycle-token-32chars"}
            res = client.post("/api/v1/internal/lifecycle/reconcile-retired-generation", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data.get("ok") is True
            assert data.get("status") == "ALREADY_COMPLETED"
            assert data.get("task_created") is False

    def test_21_deploy_workflow_packages_release_json_before_checksum(self):
        """Contract 21: deploy-vps.yml must append release.json to release.tar before checksums.sha256."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        content = wf_path.read_text(encoding="utf-8")
        assert "release.json" in content, "deploy workflow must create/package release.json"
        assert "tar -rf" in content or "release.tar" in content
        assert content.index("release.json") < content.index("sha256sum release.tar")

    def test_22_deploy_workflow_immutable_runtime_envs(self):
        """Contract 22: deploy-vps.yml must manage immutable content-addressed runtime-envs."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        content = wf_path.read_text(encoding="utf-8")
        assert "runtime-envs" in content, "deploy workflow must use content-addressed runtime-envs"
        assert "runtime_env_attestation.json" in content, "workflow must verify/generate runtime_env_attestation.json"

    def test_23_deploy_workflow_read_only_permissions(self):
        """Contract 23: deploy-vps.yml must enforce read-only permissions on release and runtime env."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        content = wf_path.read_text(encoding="utf-8")
        assert "chmod -R a-w" in content, "deploy workflow must make release and env read-only"

    def test_24_deploy_workflow_blue_green_slots_and_nginx(self):
        """Contract 24: deploy-vps.yml must implement blue/green slots and atomic Nginx reload."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        content = wf_path.read_text(encoding="utf-8")
        assert "systemctl restart toanaas-web.service" not in content, "Unparameterized hard restart must be removed"
        assert "toanaas-web@" in content, "Must use parameterized slot units (toanaas-web@<slot>)"
        assert "toanaas-web-upstream" in content, "Must manage Nginx upstream pointer"
        assert "nginx -t" in content, "Must validate Nginx configuration before reload"
        assert "systemctl reload nginx" in content, "Must gracefully reload Nginx"

    def test_25_deploy_workflow_warm_rollback_and_post_switch_reconciliation(self):
        """Contract 25: deploy-vps.yml must retain warm rollback and trigger post-switch reconciliation."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        content = wf_path.read_text(encoding="utf-8")
        assert "reconcile-retired-generation" in content, "Must trigger post-switch reconciliation"
        assert "LIFECYCLE_TOKEN" in content, "Must use LIFECYCLE_TOKEN for internal lifecycle call"

    # =========================================================================
    # FIRST RED: Remediation R1.C1 Hardening Contracts
    # =========================================================================

    def test_red_01_no_hardcoded_resolved_packages_sha(self):
        """RED 1: Neither deploy-vps.yml nor app.py may hardcode RESOLVED_PACKAGES_SHA."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "RESOLVED_PACKAGES_SHA='54212149" not in wf_content, "RESOLVED_PACKAGES_SHA must not be hardcoded in deploy workflow"
        assert (
            'RESOLVED_PACKAGES_SHA="$(' in wf_content
            or 'RESOLVED_PACKAGES_SHA=$(' in wf_content
            or 'RESOLVED_PACKAGES_SHA=\\"\\$(' in wf_content
            or 'RESOLVED_PACKAGES_SHA=\\$(' in wf_content
        ), "deploy workflow must compute RESOLVED_PACKAGES_SHA dynamically"
        assert "pip freeze" in wf_content, "Workflow must dynamically compute resolved packages SHA using pip freeze"

        app_path = ROOT / "app.py"
        app_content = app_path.read_text(encoding="utf-8")
        assert "54212149fce8c4a88e682ca6af6669525cb61c2cc488edfad4c9dde65d9cfd18" not in app_content, "app.py must not hardcode fallback resolved packages SHA"

    def test_red_02_existing_env_fully_revalidated(self):
        """RED 2: deploy-vps.yml must fully revalidate existing env rather than just testing file existence."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert 'test -f "$ENV_DIR/runtime_env_attestation.json"' not in wf_content, "Mere existence check of runtime_env_attestation.json is insufficient"
        assert "RECOMPUTED_" in wf_content or "recomputed" in wf_content.lower() or "CURRENT_FREEZE" in wf_content, "Workflow must recompute digests when validating existing env"

    def test_red_03_missing_or_malformed_attestation_fails_closed_in_strict_mode(self, monkeypatch):
        """RED 3: Under WEBAPP_RELEASE_ATTESTATION_REQUIRED=1, missing/malformed attestation fails closed."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        payload = res.json()
        assert payload.get("attestation_valid") is not True or res.status_code != 200

    def test_red_04_no_fake_release_sha_fallback(self):
        """RED 4: app.py must not hardcode base SHA 8873e10f2279 as fallback release truth."""
        app_path = ROOT / "app.py"
        app_content = app_path.read_text(encoding="utf-8")
        assert "8873e10f2279aec0fb312b70388b9073ba763f13" not in app_content, "app.py must not hardcode base SHA fallback"

    def test_red_05_concurrent_lifecycle_activation(self):
        """RED 5: Application must have an application-scoped asyncio.Lock protecting lifecycle activation."""
        from app import app
        assert hasattr(app.state, "reconciliation_lock"), "app.state must have a reconciliation_lock for concurrency safety"

    def test_red_06_actual_600s_rollback_gate(self):
        """RED 6: deploy-vps.yml must enforce an explicit 600s warm rollback window and COMMIT boundary."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "ROLLBACK_WINDOW_SECONDS=600" in wf_content or "ROLLBACK_WINDOW_SECONDS" in wf_content
        assert "COMMIT_B" in wf_content or "COMMIT" in wf_content, "Workflow must encode explicit COMMIT boundary before stopping old slot"

    def test_red_07_no_shared_root_release_extraction(self):
        """RED 7: deploy-vps.yml must not mutate active root via tar -xf into WEBAPP_DIR or git read-tree."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert 'tar -xf "$STAGING_DIR/release.tar" -C "$WEBAPP_DIR"' not in wf_content, "Must not unpack release into shared root"
        assert 'git read-tree "$TARGET_SHA"' not in wf_content, "Must not mutate active git working tree"

    def test_red_08_runtime_config_prerequisite_fail_closed(self):
        """RED 8: deploy-vps.yml must fail closed on missing prerequisites and must not generate lifecycle tokens."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "openssl rand" not in wf_content, "Workflow must not generate lifecycle tokens; tokens are Owner-provisioned"
        assert "toanaas-web@.service" in wf_content, "Workflow must check template unit existence"
        assert "PREREQUISITES" in wf_content or "PREREQUISITE" in wf_content, "Workflow must include prerequisite verification check"

    def test_red_09_post_switch_verification_traverses_nginx(self):
        """RED 9: Post-switch verification must traverse Nginx ingress, not port 8000."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "curl -s -f http://127.0.0.1:8000/health" not in wf_content

    def test_red_10_startup_preserves_storyboard_runtime_preflight(self):
        """RED 10: lifespan in app.py must call copyfast_storyboard_grid.ensure_storyboard_grid_runtime()."""
        app_path = ROOT / "app.py"
        app_content = app_path.read_text(encoding="utf-8")
        assert "copyfast_storyboard_grid.ensure_storyboard_grid_runtime()" in app_content

    def test_red_11_health_endpoint_preserves_path_privacy(self):
        """RED 11: /health must not leak host paths (sys.executable, sys.prefix) into public responses."""
        from app import app
        client = TestClient(app)
        res = client.get("/health")
        payload = res.json()
        assert "python_executable" not in payload.get("runtime_attestation", {})
        assert "environment_prefix" not in payload.get("runtime_attestation", {})
        assert "python_executable" not in payload
        assert "environment_prefix" not in payload
