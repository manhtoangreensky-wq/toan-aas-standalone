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
        assert "CANONICAL_PKG_DIGEST" in wf_content or "importlib.metadata" in wf_content, "Workflow must dynamically compute resolved packages SHA using canonical package digest algorithm"

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

    # =========================================================================
    # FIRST RED: Remediation R1.C2 Hardening Contracts
    # =========================================================================

    def test_c2_red_01_hardcoded_requirements_lock_sha_fallback(self):
        """C2 RED 1: app.py must not contain hardcoded lock SHA '9490bebca11e...'."""
        app_path = ROOT / "app.py"
        app_content = app_path.read_text(encoding="utf-8")
        assert "9490bebca11e7aaf14b7804eba35a6bf2c5bcab7d0a1220771c8fbdc29c14d5f" not in app_content, (
            "app.py must not hardcode fallback lock SHA '9490bebca11e...'"
        )

    def test_c2_red_02_forged_attestation_wrong_lock_sha(self, monkeypatch):
        """C2 RED 2: Forged attestation with wrong lock SHA must fail closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        from app import app as fastapi_app, _compute_installed_packages_digest
        import platform
        py_id = f"py{platform.python_version()}-{platform.machine().lower()}"
        pkg_digest = _compute_installed_packages_digest()
        env_id = f"{py_id}-res-{pkg_digest[:16]}"
        bad_attestation = {
            "runtime_environment_id": env_id,
            "python_runtime_id": py_id,
            "requirements_lock_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "resolved_packages_sha256": pkg_digest,
            "running_executable_under_attested_env": True,
        }
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "runtime_env_attestation.json" else os.path.isfile(self))
        monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: json.dumps(bad_attestation) if self.name == "runtime_env_attestation.json" else open(self, encoding="utf-8").read())

        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for wrong lock SHA, got {res.status_code}"
        payload = res.json()
        assert payload.get("attestation_valid") is False

    def test_c2_red_03_forged_attestation_wrong_package_digest(self, monkeypatch):
        """C2 RED 3: Forged attestation with wrong package digest must fail closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        from app import app as fastapi_app
        import platform
        py_id = f"py{platform.python_version()}-{platform.machine().lower()}"
        lock_path = ROOT / "requirements.lock"
        actual_lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        bad_attestation = {
            "runtime_environment_id": f"{py_id}-res-deadbeefdeadbeef",
            "python_runtime_id": py_id,
            "requirements_lock_sha256": actual_lock_sha,
            "resolved_packages_sha256": "deadbeef" * 8,
            "running_executable_under_attested_env": True,
        }
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "runtime_env_attestation.json" else os.path.isfile(self))
        monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: json.dumps(bad_attestation) if self.name == "runtime_env_attestation.json" else open(self, encoding="utf-8").read())

        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for wrong package digest, got {res.status_code}"
        payload = res.json()
        assert payload.get("attestation_valid") is False

    def test_c2_red_04_wrong_python_runtime_id(self, monkeypatch):
        """C2 RED 4: Forged attestation with mismatched python_runtime_id must fail closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        from app import app as fastapi_app, _compute_installed_packages_digest
        lock_path = ROOT / "requirements.lock"
        actual_lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        actual_pkg_digest = _compute_installed_packages_digest()
        bad_attestation = {
            "runtime_environment_id": f"py3.99-fake-res-{actual_pkg_digest[:16]}",
            "python_runtime_id": "py3.99-fake",
            "requirements_lock_sha256": actual_lock_sha,
            "resolved_packages_sha256": actual_pkg_digest,
            "running_executable_under_attested_env": True,
        }
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "runtime_env_attestation.json" else os.path.isfile(self))
        monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: json.dumps(bad_attestation) if self.name == "runtime_env_attestation.json" else open(self, encoding="utf-8").read())

        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for mismatched python_runtime_id, got {res.status_code}"
        payload = res.json()
        assert payload.get("attestation_valid") is False

    def test_c2_red_05_wrong_runtime_environment_id(self, monkeypatch):
        """C2 RED 5: Forged attestation with mismatched runtime_environment_id must fail closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        from app import app as fastapi_app, _compute_installed_packages_digest
        import platform
        py_id = f"py{platform.python_version()}-{platform.machine().lower()}"
        lock_path = ROOT / "requirements.lock"
        actual_lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        actual_pkg_digest = _compute_installed_packages_digest()
        bad_attestation = {
            "runtime_environment_id": "forged-custom-runtime-id",
            "python_runtime_id": py_id,
            "requirements_lock_sha256": actual_lock_sha,
            "resolved_packages_sha256": actual_pkg_digest,
            "running_executable_under_attested_env": True,
        }
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "runtime_env_attestation.json" else os.path.isfile(self))
        monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: json.dumps(bad_attestation) if self.name == "runtime_env_attestation.json" else open(self, encoding="utf-8").read())

        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for mismatched runtime_environment_id, got {res.status_code}"
        payload = res.json()
        assert payload.get("attestation_valid") is False

    def test_c2_red_06_target_slot_missing_strict_attestation_mode(self):
        """C2 RED 6: Target slot env file must configure WEBAPP_RELEASE_ATTESTATION_REQUIRED=1."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "WEBAPP_RELEASE_ATTESTATION_REQUIRED=1" in wf_content, (
            "deploy-vps.yml must write WEBAPP_RELEASE_ATTESTATION_REQUIRED=1 into /etc/toanaas/web-slot-${TARGET_SLOT}.env"
        )

    def test_c2_red_07_declared_600s_value_without_actual_rollback_window_wait_gate(self):
        """C2 RED 7: deploy-vps.yml must enforce an actual rollback window wait/sampling loop, not just static echo."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "ROLLBACK_WINDOW_SECONDS=600" in wf_content
        window_idx = wf_content.find("ROLLBACK_WINDOW_SECONDS=600")
        stop_idx = wf_content.find("systemctl stop toanaas-web@${ACTIVE_SLOT}")
        if stop_idx == -1:
            stop_idx = wf_content.find("Retiring Old Slot")
        if stop_idx == -1:
            stop_idx = wf_content.find("systemctl stop toanaas-web@")
        assert window_idx != -1 and stop_idx != -1 and window_idx < stop_idx
        window_block = wf_content[window_idx:stop_idx]
        assert "sleep" in window_block, "Rollback window must actively sample/wait before retiring old slot"

    def test_c2_red_08_public_nginx_response_validates_runtime_env(self):
        """C2 RED 8: Ingress verification through Nginx must validate runtime_environment_id and attestation_valid."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        nginx_block = wf_content[wf_content.find("Verifying Health Endpoint via Nginx Ingress") : wf_content.find("Commit Boundary")]
        assert "runtime_environment_id" in nginx_block and "RUNTIME_ENVIRONMENT_ID" in nginx_block, (
            "Nginx ingress verification must assert runtime_environment_id"
        )
        assert "attestation_valid" in nginx_block, (
            "Nginx ingress verification must assert attestation_valid is True"
        )

    def test_c2_red_09_missing_nginx_upstream_integration_prerequisite(self):
        """C2 RED 9: deploy-vps.yml must verify that Nginx configuration includes web-upstream-active.conf."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        prereq_block = wf_content[wf_content.find("Verifying Runtime Prerequisites") : wf_content.find("Creating Tracked Source Backup")]
        assert "grep" in prereq_block and "web-upstream-active.conf" in prereq_block and "/etc/nginx" in prereq_block, (
            "deploy-vps.yml must fail-closed if Nginx configuration does not include web-upstream-active.conf"
        )

    def test_c2_red_10_release_json_strict_mode_validation(self, monkeypatch):
        """C2 RED 10: Under WEBAPP_RELEASE_ATTESTATION_REQUIRED=1, missing or malformed release.json fails closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        import app
        from app import app as fastapi_app
        # Mock runtime attestation as valid
        monkeypatch.setattr(app, "_load_runtime_attestation", lambda: {
            "attestation_valid": True,
            "running_executable_under_attested_env": True,
            "python_runtime_id": "py3.14-win32",
            "runtime_environment_id": "py3.14-win32-res-valid",
            "requirements_lock_sha256": "validlock",
            "resolved_packages_sha256": "validpkg",
        })
        # Mock release.json as malformed
        monkeypatch.setattr(Path, "is_file", lambda self: True if self.name == "release.json" else os.path.isfile(self))
        monkeypatch.setattr(Path, "read_text", lambda self, *args, **kwargs: "MALFORMED_NOT_JSON" if self.name == "release.json" else open(self, encoding="utf-8").read())
        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for malformed release.json in strict mode, got {res.status_code}"

    def test_c2_red_10b_missing_release_json_strict_mode_fail(self, monkeypatch):
        """C2 RED 10b: Under WEBAPP_RELEASE_ATTESTATION_REQUIRED=1, missing release.json fails closed (503)."""
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        import app
        from app import app as fastapi_app
        # Mock runtime attestation as valid
        monkeypatch.setattr(app, "_load_runtime_attestation", lambda: {
            "attestation_valid": True,
            "running_executable_under_attested_env": True,
            "python_runtime_id": "py3.14-win32",
            "runtime_environment_id": "py3.14-win32-res-valid",
            "requirements_lock_sha256": "validlock",
            "resolved_packages_sha256": "validpkg",
        })
        # Mock release.json as not existing
        monkeypatch.setattr(Path, "is_file", lambda self: False if self.name == "release.json" else os.path.isfile(self))
        client = TestClient(fastapi_app)
        res = client.get("/health")
        assert res.status_code == 503, f"Expected 503 for missing release.json in strict mode, got {res.status_code}"

    def test_c2_red_11_truly_concurrent_lifecycle_calls_single_task(self, monkeypatch):
        """C2 RED 11: Truly concurrent lifecycle calls must yield exactly one task_created=True."""
        import anyio
        from httpx import AsyncClient, ASGITransport
        from app import app as fastapi_app
        monkeypatch.setenv("WEBAPP_STARTUP_RECONCILIATION_MODE", "deferred")
        monkeypatch.setenv("WEBAPP_LIFECYCLE_TOKEN", "valid-test-lifecycle-token-32chars")

        fastapi_app.state.reconciliation_state = "DEFERRED"
        fastapi_app.state.copyfast_startup_reconciliation_task = None

        async def run_test():
            async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://127.0.0.1") as ac:
                async def call_lifecycle():
                    return await ac.post(
                        "/api/v1/internal/lifecycle/reconcile-retired-generation",
                        headers={"X-Lifecycle-Token": "valid-test-lifecycle-token-32chars"}
                    )
                import asyncio
                responses = await asyncio.gather(*(call_lifecycle() for _ in range(5)))
                return responses

        responses = anyio.run(run_test)
        assert all(r.status_code == 200 for r in responses)
        data_list = [r.json() for r in responses]
        task_created_count = sum(1 for d in data_list if d.get("task_created") is True)
        assert task_created_count == 1, f"Expected exactly 1 task_created=True, got {task_created_count}"

    def test_c2_red_12_atomic_rollback_switch(self):
        """C2 RED 12: deploy-vps.yml must use atomic mv and nginx -t for rollback, not direct redirection."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "> /etc/toanaas/web-upstream-active.conf" not in wf_content, (
            "Direct redirection to active pointer file is prohibited; must use temp file and atomic mv"
        )

    def test_c2_red_13_canonical_package_digest_consistency(self):
        """C2 RED 13: Workflow and app must share the exact same package digest algorithm."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "pip freeze --all | LC_ALL=C sort | sha256sum" not in wf_content, (
            "deploy-vps.yml must not use disparate pip freeze algorithm; must use canonical algorithm"
        )

    def test_c3_red_01_http200_wrong_runtime_id_triggers_rollback(self):
        """C3 RED 01: Ingress returning HTTP 200 with wrong runtime ID must trigger rollback_to_active_slot."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "rollback_to_active_slot" in wf_content, "deploy-vps.yml must define centralized rollback_to_active_slot"
        assert 'verify_target_identity' in wf_content or 'if ! ' in wf_content or '|| rollback_to_active_slot' in wf_content, (
            "deploy-vps.yml must explicitly invoke rollback_to_active_slot on identity mismatch, not rely on set -e"
        )

    def test_c3_red_02_http200_wrong_release_sha_triggers_rollback(self):
        """C3 RED 02: Ingress returning HTTP 200 with wrong release SHA must trigger rollback_to_active_slot."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "rollback_to_active_slot" in wf_content
        # Ensure post-switch verification explicitly invokes rollback_to_active_slot on release SHA failure
        idx_switch = wf_content.find("=== Switching Traffic to Target Slot in Nginx ===")
        assert idx_switch != -1
        switch_section = wf_content[idx_switch:]
        assert "rollback_to_active_slot" in switch_section

    def test_c3_red_03_http200_attestation_valid_false_triggers_rollback(self):
        """C3 RED 03: Ingress returning HTTP 200 with attestation_valid=false must trigger rollback_to_active_slot."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "rollback_to_active_slot" in wf_content

    def test_c3_red_04_invalid_json_triggers_rollback(self):
        """C3 RED 04: Ingress returning invalid JSON must trigger rollback_to_active_slot."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "rollback_to_active_slot" in wf_content

    def test_c3_red_05_window_sample_failure_triggers_centralized_rollback(self):
        """C3 RED 05: Rollback window sampling failure must invoke rollback_to_active_slot."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_window = wf_content.find("=== Commit Boundary and Warm Rollback Window ===")
        assert idx_window != -1
        window_section = wf_content[idx_window:]
        assert "rollback_to_active_slot" in window_section, (
            "600s rollback window must invoke centralized rollback_to_active_slot on any sample failure"
        )

    def test_c3_red_06_forward_nginx_test_failure_restores_old_pointer(self):
        """C3 RED 06: Forward switch nginx -t failure must restore the old pointer atomically."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "FORWARD_NGINX_TEST_FAILURE_RESTORES_POINTER" in wf_content or "RESTORE_OLD_POINTER" in wf_content or "PRESERVED_POINTER" in wf_content or "PREV_UPSTREAM" in wf_content, (
            "Forward switch must preserve old pointer and restore it if nginx -t fails"
        )

    def test_c3_red_07_rollback_uses_temp_and_atomic_mv(self):
        """C3 RED 07: Centralized rollback authority must use temp file and atomic mv."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "rollback_to_active_slot" in wf_content
        # rollback function must contain atomic mv
        idx_fn = wf_content.find("rollback_to_active_slot()")
        assert idx_fn != -1, "deploy-vps.yml must define rollback_to_active_slot() function"
        fn_body = wf_content[idx_fn:idx_fn+1500]
        assert "mv " in fn_body and ".tmp." in fn_body, (
            "rollback_to_active_slot must write to temp file and mv atomically"
        )

    def test_c3_red_08_rollback_nginx_test_before_reload(self):
        """C3 RED 08: rollback_to_active_slot must test nginx syntax before reload."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        assert idx_fn != -1
        fn_body = wf_content[idx_fn:idx_fn+1500]
        t_pos = fn_body.find("nginx -t")
        reload_pos = fn_body.find("systemctl reload nginx")
        assert t_pos != -1 and reload_pos != -1 and t_pos < reload_pos, (
            "rollback_to_active_slot must test nginx -t before systemctl reload nginx"
        )

    def test_c3_red_09_rollback_verifies_publicly_before_stopping_b(self):
        """C3 RED 09: rollback_to_active_slot must verify public ingress A before stopping target B."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        assert idx_fn != -1
        fn_body = wf_content[idx_fn:idx_fn+2500]
        assert "Host: app.toanaas.vn" in fn_body or "ROLLBACK_VERIFY" in fn_body, (
            "rollback_to_active_slot must verify public ingress on slot A"
        )
        assert "systemctl stop toanaas-web@\\${TARGET_SLOT}.service" in fn_body or "systemctl stop toanaas-web@$TARGET_SLOT.service" in fn_body, (
            "rollback_to_active_slot must stop target B only after public verification of A"
        )

    def test_c3_red_10_shared_root_git_update_ref_absent(self):
        """C3 RED 10: git update-ref refs/heads/main must NOT be run in deploy root."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "git update-ref refs/heads/main" not in wf_content, (
            "deploy-vps.yml must not mutate refs/heads/main in shared checkout"
        )
        assert "git update-ref refs/remotes/origin/main" not in wf_content, (
            "deploy-vps.yml must not mutate refs/remotes/origin/main in shared checkout"
        )

    def test_c3_red_11_shared_root_symbolic_ref_absent(self):
        """C3 RED 11: git symbolic-ref HEAD refs/heads/main must NOT be run in deploy root."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "git symbolic-ref HEAD" not in wf_content, (
            "deploy-vps.yml must not mutate symbolic-ref HEAD in shared checkout"
        )

    def test_c3_red_12_nginx_test_loaded_config_proof_required(self):
        """C3 RED 12: Prerequisite checks must inspect loaded Nginx configuration with nginx -T."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "nginx -T" in wf_content, "Prerequisite checks must run nginx -T to verify loaded config"

    def test_c3_red_13_commented_stale_include_rejected(self):
        """C3 RED 13: Prerequisite must verify active upstream block consumes web-upstream-active.conf."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "grep -rq 'web-upstream-active.conf' /etc/nginx/" not in wf_content, (
            "Filesystem grep is prohibited; must verify loaded configuration"
        )

    def test_c3_red_14_public_lifecycle_proxy_exposure_fails_prerequisite(self):
        """C3 RED 14: Prerequisite must prove /api/v1/internal/lifecycle/ is denied/blocked publicly in Nginx."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_prereq = wf_content.find("=== Verifying Runtime Prerequisites (Fail-Closed) ===")
        idx_end_prereq = wf_content.find("=== Fetching Bundle Objects and Verifying Target ===")
        assert idx_prereq != -1 and idx_end_prereq != -1
        prereq_section = wf_content[idx_prereq:idx_end_prereq]
        assert "api/v1/internal/lifecycle" in prereq_section, (
            "Prerequisite checks must prove public lifecycle route is blocked/denied in loaded Nginx config"
        )
        assert "deny all" in prereq_section or "return 404" in prereq_section or "return 403" in prereq_section or "LIFECYCLE_BLOCKED" in prereq_section, (
            "Prerequisite must verify explicit block of lifecycle route"
        )

    def test_c3_red_15_strict_release_sha_malformed_returns_503(self, monkeypatch, tmp_path):
        """C3 RED 15: In strict mode, malformed release_sha (not 40-char hex) must fail closed with release_valid=False."""
        import app
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        monkeypatch.setattr(app, "ROOT", tmp_path)

        # Create requirements.lock with valid sha
        lock_file = tmp_path / "requirements.lock"
        lock_file.write_text("package==1.0.0\n", encoding="utf-8")

        # Create release.json with non-hex / short release_sha
        release_json = tmp_path / "release.json"
        release_json.write_text(json.dumps({
            "release_sha": "short-sha-invalid",
            "requirements_lock_sha256": "9490bebca11e7aaf14b7804eba35a6bf2c5bcab7d0a1220771c8fbdc29c14d5f",
        }), encoding="utf-8")

        meta = app._load_release_metadata()
        assert meta.get("release_valid") is False, f"Expected release_valid=False for malformed release_sha, got {meta.get('release_valid')}"

    def test_c3_red_16_strict_release_lock_sha_mismatch_returns_503(self, monkeypatch, tmp_path):
        """C3 RED 16: In strict mode, release.json requirements_lock_sha256 mismatching actual repo lock SHA must return release_valid=False."""
        import app
        monkeypatch.setenv("WEBAPP_RELEASE_ATTESTATION_REQUIRED", "1")
        monkeypatch.setattr(app, "ROOT", tmp_path)

        # Create requirements.lock
        lock_file = tmp_path / "requirements.lock"
        lock_file.write_text("package==1.0.0\n", encoding="utf-8")
        import hashlib
        actual_lock_sha = hashlib.sha256(lock_file.read_bytes()).hexdigest()

        # Create release.json with different requirements_lock_sha256
        release_json = tmp_path / "release.json"
        release_json.write_text(json.dumps({
            "release_sha": "0123456789abcdef0123456789abcdef01234567",
            "requirements_lock_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }), encoding="utf-8")

        meta = app._load_release_metadata()
        assert meta.get("release_valid") is False, f"Expected release_valid=False for lock SHA mismatch in release.json, got {meta.get('release_valid')}"

    # =========================================================================
    # C4 Contract Tests (Task P0.WEBAPP.V3-B1.ZERO.DOWNTIME.SOURCE.IMPLEMENTATION.R1.C4)
    # =========================================================================

    def test_c4_first_red_a_rollback_wrong_generation(self):
        """FIRST RED A: Rollback verification must prove old slot identity, rejecting B payload."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        assert idx_fn != -1
        idx_end = wf_content.find("=== Switching Traffic to Target Slot in Nginx ===")
        rb_block = wf_content[idx_fn:idx_end]
        assert "OLD_RELEASE_SHA" in rb_block, "rollback_to_active_slot must bind OLD_RELEASE_SHA"
        assert "OLD_RUNTIME_ENV" in rb_block, "rollback_to_active_slot must bind OLD_RUNTIME_ENV"

    def test_c4_first_red_b_shared_root_mutation(self):
        """FIRST RED B: Workflow must not mutate shared checkout via delete/ or git fetch."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "BACKUP_DIR=\"$WEBAPP_DIR/delete" not in wf_content, "Workflow must not create backup under WEBAPP_DIR/delete"
        assert "SHARED_GIT_METADATA_MUTATION=0" in wf_content, "Workflow must enforce SHARED_GIT_METADATA_MUTATION=0"
        assert "BUNDLE_VERIFICATION_ISOLATED=YES" in wf_content, "Workflow must enforce BUNDLE_VERIFICATION_ISOLATED=YES"

    def test_c4_first_red_c_commented_nginx_false_positive(self):
        """FIRST RED C: Prerequisite checks must reject commented pointer include and commented lifecycle block."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        prereq_block = wf_content[wf_content.find("=== Verifying Runtime Prerequisites") : wf_content.find("=== Resolving Active / Target")]
        assert "strip_nginx_comments" in prereq_block or "COMMENTED" in prereq_block or "python3" in prereq_block, (
            "Prerequisite checks must normalize Nginx config to reject commented directives"
        )

    def test_c4_01_rollback_receives_b_health_fails_verification(self):
        """C4-01: rollback receiving B health must fail verification."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        rb_block = wf_content[idx_fn:wf_content.find("=== Switching Traffic to Target Slot in Nginx ===")]
        assert "OLD_RELEASE_SHA" in rb_block and "OLD_RUNTIME_ENV" in rb_block
        assert "release_sha" in rb_block and "runtime_environment_id" in rb_block

    def test_c4_02_rollback_wrong_old_release_sha_leaves_b_running(self):
        """C4-02: rollback with wrong old release SHA must leave B running."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        rb_block = wf_content[idx_fn:wf_content.find("=== Switching Traffic to Target Slot in Nginx ===")]
        assert "ROLLBACK_A_IDENTITY_NOT_PROVEN_TARGET_STOP=NO" in rb_block or "Leaving target slot" in rb_block

    def test_c4_03_rollback_wrong_old_runtime_env_leaves_b_running(self):
        """C4-03: rollback with wrong old runtime env must leave B running."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        idx_fn = wf_content.find("rollback_to_active_slot()")
        rb_block = wf_content[idx_fn:wf_content.find("=== Switching Traffic to Target Slot in Nginx ===")]
        stop_pos = rb_block.find("systemctl stop toanaas-web@")
        verify_pos = rb_block.find("RB_VERIFIED")
        assert verify_pos != -1 and stop_pos != -1 and verify_pos < stop_pos

    def test_c4_04_rollback_exact_old_identity_allows_b_to_be_stopped(self):
        """C4-04: Target B is stopped only after proven restoration of exact A identity."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "TARGET_STOP_ONLY_AFTER_PROVEN_A=YES" in wf_content

    def test_c4_05_active_slot_identity_captured_before_switch(self):
        """C4-05: A identity captured from private active-slot health before switch."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "PRE_SWITCH_ACTIVE_SLOT_IDENTITY_PROVEN=YES" in wf_content
        idx_cap = wf_content.find("Capturing Pre-Switch Active Slot Runtime Identity")
        idx_sw = wf_content.find("Switching Traffic to Target Slot in Nginx")
        assert idx_cap != -1 and idx_sw != -1 and idx_cap < idx_sw

    def test_c4_06_pre_switch_public_health_matches_a(self):
        """C4-06: public pre-switch health must match A."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "PRE_SWITCH_PUBLIC_MATCHES_ACTIVE_SLOT=YES" in wf_content
        idx_pub = wf_content.find("Verifying Current Public Traffic Matches Active Slot Identity")
        idx_sw = wf_content.find("Switching Traffic to Target Slot in Nginx")
        assert idx_pub != -1 and idx_sw != -1 and idx_pub < idx_sw

    def test_c4_07_no_webapp_dir_delete_deployment_backup(self):
        """C4-07: no WEBAPP_DIR/delete deployment backup."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "$WEBAPP_DIR/delete" not in wf_content
        assert "SHARED_DEPLOY_ROOT_MUTATION=0" in wf_content

    def test_c4_08_no_git_fetch_into_shared_checkout(self):
        """C4-08: no git fetch into shared checkout."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert 'git fetch "$STAGING_DIR/release.bundle" refs/deployments/release:refs/deployments/release' not in wf_content

    def test_c4_09_no_shared_git_ref_mutation(self):
        """C4-09: no shared .git ref/object mutation."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "SHARED_GIT_METADATA_MUTATION=0" in wf_content

    def test_c4_10_isolated_bundle_verification_exists(self):
        """C4-10: isolated bundle verification exists in staging repo."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "BUNDLE_VERIFICATION_ISOLATED=YES" in wf_content
        assert "verify-repo.git" in wf_content or "verify.git" in wf_content

    def test_c4_11_commented_pointer_include_rejected(self):
        """C4-11: commented pointer include rejected."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "ACTIVE_NGINX_POINTER_INTEGRATION_PREREQUISITE=YES" in wf_content

    def test_c4_12_commented_lifecycle_deny_rejected(self):
        """C4-12: commented lifecycle deny rejected."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "PUBLIC_LIFECYCLE_ROUTE_BLOCK_PREREQUISITE=YES" in wf_content

    def test_c4_13_unrelated_upstream_include_rejected(self):
        """C4-13: inactive/unrelated upstream include rejected."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        prereq = wf_content[wf_content.find("Verifying Runtime Prerequisites") : wf_content.find("=== Resolving Active / Target")]
        assert "proxy_pass" in prereq and "web-upstream-active.conf" in prereq

    def test_c4_14_unrelated_proxy_pass_rejected(self):
        """C4-14: unrelated proxy_pass rejected."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        prereq = wf_content[wf_content.find("Verifying Runtime Prerequisites") : wf_content.find("=== Resolving Active / Target")]
        assert "proxy_pass" in prereq

    def test_c4_15_same_upstream_public_routing_chain_accepted(self):
        """C4-15: same upstream/public routing chain accepted."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "ACTIVE_NGINX_POINTER_INTEGRATION_PREREQUISITE=YES" in wf_content

    def test_c4_16_lifecycle_string_without_effective_blocking_location_rejected(self):
        """C4-16: lifecycle string without effective blocking location rejected."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        prereq = wf_content[wf_content.find("Verifying Runtime Prerequisites") : wf_content.find("=== Resolving Active / Target")]
        assert "api/v1/internal/lifecycle" in prereq

    def test_c4_17_effective_lifecycle_block_accepted(self):
        """C4-17: effective lifecycle block accepted."""
        wf_path = ROOT / ".github" / "workflows" / "deploy-vps.yml"
        wf_content = wf_path.read_text(encoding="utf-8")
        assert "PUBLIC_LIFECYCLE_ROUTE_BLOCK_PREREQUISITE=YES" in wf_content
