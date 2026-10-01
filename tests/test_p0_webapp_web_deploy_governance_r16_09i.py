"""Web Deploy Governance Tests — R16.09I

Prove that the deploy workflow enforces manual-only dispatch with exact
target SHA validation, a forward-only deploy guard, and that the quality
gate remains independent from production deployment.

These tests parse the committed YAML workflow files without executing them.
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-vps.yml"
QUALITY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "webapp-quality.yml"


def _load_workflow(path: Path) -> dict:
    """Load and parse a GitHub Actions workflow YAML file."""
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


# ---------------------------------------------------------------------------
# §1  WEB_DEPLOY_ON_PUSH_MAIN=NO
# ---------------------------------------------------------------------------

def test_deploy_workflow_has_no_push_trigger() -> None:
    """The deploy workflow must NOT trigger on push to any branch."""
    wf = _load_workflow(DEPLOY_WORKFLOW)
    triggers = wf.get(True) or wf.get("on") or {}
    assert "push" not in triggers, (
        "deploy-vps.yml must not contain a 'push' trigger"
    )


# ---------------------------------------------------------------------------
# §2  WEB_DEPLOY_MANUAL_ONLY=YES
# ---------------------------------------------------------------------------

def test_deploy_workflow_uses_only_workflow_dispatch() -> None:
    """The deploy workflow's only trigger must be workflow_dispatch."""
    wf = _load_workflow(DEPLOY_WORKFLOW)
    triggers = wf.get(True) or wf.get("on") or {}
    if isinstance(triggers, str):
        trigger_keys = {triggers}
    elif isinstance(triggers, list):
        trigger_keys = set(triggers)
    elif isinstance(triggers, dict):
        trigger_keys = set(triggers.keys())
    else:
        pytest.fail(f"Unexpected 'on' type: {type(triggers)}")

    assert trigger_keys == {"workflow_dispatch"}, (
        f"deploy-vps.yml triggers must be exactly {{workflow_dispatch}}, got {trigger_keys}"
    )


def test_deploy_workflow_has_no_automatic_triggers() -> None:
    """Reject pull_request, workflow_run, schedule, or other auto triggers."""
    wf = _load_workflow(DEPLOY_WORKFLOW)
    triggers = wf.get(True) or wf.get("on") or {}
    if isinstance(triggers, dict):
        forbidden = {"push", "pull_request", "workflow_run", "schedule"}
        found = forbidden & set(triggers.keys())
        assert not found, (
            f"deploy-vps.yml must not have automatic triggers: {found}"
        )


# ---------------------------------------------------------------------------
# §3  TARGET_SHA_REQUIRED=YES
# ---------------------------------------------------------------------------

def test_deploy_workflow_target_sha_input_required() -> None:
    """workflow_dispatch must require a 'target_sha' input."""
    wf = _load_workflow(DEPLOY_WORKFLOW)
    triggers = wf.get(True) or wf.get("on") or {}
    dispatch = triggers.get("workflow_dispatch") or {}
    inputs = dispatch.get("inputs") or {}
    assert "target_sha" in inputs, (
        "deploy-vps.yml workflow_dispatch must have a 'target_sha' input"
    )
    sha_input = inputs["target_sha"]
    assert sha_input.get("required") is True, (
        "target_sha input must be required=true"
    )


# ---------------------------------------------------------------------------
# §4  TARGET_SHA_40_HEX_VALIDATION=YES
# ---------------------------------------------------------------------------

def test_deploy_workflow_validates_40_hex_sha() -> None:
    """The workflow must validate target_sha matches ^[0-9a-fA-F]{40}$."""
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert "[0-9a-fA-F]{40}" in text, (
        "deploy-vps.yml must contain 40-hex SHA format validation regex"
    )


# ---------------------------------------------------------------------------
# §5  DOWNGRADE_GUARD_PRESENT=YES
# ---------------------------------------------------------------------------

def test_deploy_workflow_has_forward_only_guard() -> None:
    """The workflow must include a merge-base --is-ancestor guard."""
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert "merge-base" in text and "is-ancestor" in text, (
        "deploy-vps.yml must include 'merge-base --is-ancestor' forward-only deploy guard"
    )


def test_deploy_workflow_blocks_non_forward_deploy() -> None:
    """The workflow must emit BLOCKED_NON_FORWARD_WEB_DEPLOY on failure."""
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert "BLOCKED_NON_FORWARD_WEB_DEPLOY" in text, (
        "deploy-vps.yml must emit BLOCKED_NON_FORWARD_WEB_DEPLOY status"
    )


# ---------------------------------------------------------------------------
# §6  WEB_RESTART_ONLY_INSIDE_MANUAL_DEPLOY_JOB=YES
# ---------------------------------------------------------------------------

def test_systemctl_restart_only_in_deploy_workflow() -> None:
    """systemctl restart toanaas-web.service must appear only in deploy-vps.yml."""
    deploy_text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    quality_text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    assert "systemctl restart toanaas-web.service" in deploy_text, (
        "deploy-vps.yml must contain systemctl restart toanaas-web.service"
    )
    assert "systemctl restart" not in quality_text, (
        "webapp-quality.yml must NOT contain systemctl restart"
    )


# ---------------------------------------------------------------------------
# §7  QUALITY_GATE_INDEPENDENT_FROM_DEPLOY=YES
# ---------------------------------------------------------------------------

def test_quality_gate_has_no_deploy_actions() -> None:
    """The quality gate workflow must not perform any deploy actions."""
    text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    deploy_markers = [
        "systemctl restart",
        "systemctl is-active",
        "release.tar",
        "release.bundle",
        "VPS_SSH_KEY",
        "Deploy Web to VPS",
    ]
    for marker in deploy_markers:
        assert marker not in text, (
            f"webapp-quality.yml must not contain deploy action: '{marker}'"
        )


def test_quality_gate_does_not_trigger_deploy_workflow() -> None:
    """The quality gate workflow must not use workflow_run to chain deploy."""
    wf = _load_workflow(QUALITY_WORKFLOW)
    # Check that quality gate doesn't reference deploy workflow
    text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    assert "deploy-vps" not in text.lower().replace("deploy_vps", "deploy-vps"), (
        "webapp-quality.yml must not reference deploy-vps workflow"
    )


# ---------------------------------------------------------------------------
# §8  BOOTSTRAP SAFETY — POST_PATCH_PUSH_DEPLOY_TRIGGER_PRESENT=NO
# ---------------------------------------------------------------------------

def test_post_patch_no_push_deploy_trigger() -> None:
    """After this PR merges, the deploy workflow in main will have no push trigger.

    This test verifies the file on disk (which IS the proposed merge content)
    has no push trigger, ensuring bootstrap safety — the PR itself won't
    trigger an automatic deployment when merged.
    """
    wf = _load_workflow(DEPLOY_WORKFLOW)
    triggers = wf.get(True) or wf.get("on") or {}
    if isinstance(triggers, dict):
        assert "push" not in triggers
    elif isinstance(triggers, (list, str)):
        trigger_list = [triggers] if isinstance(triggers, str) else triggers
        assert "push" not in trigger_list


# ---------------------------------------------------------------------------
# Existing deploy safety preserved
# ---------------------------------------------------------------------------

def test_deploy_workflow_preserves_existing_safety() -> None:
    """Verify key safety mechanisms remain in the deploy workflow."""
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    safety_markers = [
        "checksums.sha256",
        "sha256sum",
        "git cat-file -e",
        "systemctl restart toanaas-web.service",
        "systemctl is-active toanaas-web.service",
        "systemctl is-active nginx.service",
        "/health",
        "release.tar",
        "release.bundle",
        "tracked-files.txt",
        "removed-files.txt",
    ]
    for marker in safety_markers:
        assert marker in text, (
            f"deploy-vps.yml must preserve safety mechanism: '{marker}'"
        )


# ---------------------------------------------------------------------------
# §R16.09I1  EXECUTION ORDER CORRECTNESS
# ---------------------------------------------------------------------------


def _ssh_block(text: str) -> str:
    """Extract the remote SSH execution block from deploy-vps.yml."""
    # The SSH heredoc block starts after the last ssh command line that opens
    # a quoted heredoc string and ends at the closing quote.
    # We locate it by finding the 'Deploy Web to VPS via SSH' step.
    marker = "Deploy Web to VPS via SSH"
    idx = text.index(marker)
    return text[idx:]


def _line_index(block: str, needle: str) -> int:
    """Return the line number (0-based) of the first line containing needle."""
    for i, line in enumerate(block.splitlines()):
        if needle in line:
            return i
    raise ValueError(f"Needle '{needle}' not found in block")


def test_fetch_bundle_before_forward_guard() -> None:
    """git fetch release.bundle must precede Forward-Only Deploy Guard."""
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    fetch_idx = _line_index(block, "release.bundle")
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    assert fetch_idx < guard_idx, (
        f"release.bundle fetch (line {fetch_idx}) must precede "
        f"Forward-Only Deploy Guard (line {guard_idx})"
    )


def test_target_object_verify_before_forward_guard() -> None:
    """git cat-file -e TARGET_SHA must precede Forward-Only Deploy Guard."""
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    catfile_idx = _line_index(block, "git cat-file -e")
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    assert catfile_idx < guard_idx, (
        f"git cat-file -e (line {catfile_idx}) must precede "
        f"Forward-Only Deploy Guard (line {guard_idx})"
    )


def test_forward_guard_before_source_apply() -> None:
    """Forward-Only Deploy Guard must precede Applying Release Source."""
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    apply_idx = _line_index(block, "Applying Release Source")
    assert guard_idx < apply_idx, (
        f"Forward-Only Deploy Guard (line {guard_idx}) must precede "
        f"Applying Release Source (line {apply_idx})"
    )


def test_forward_guard_before_web_restart() -> None:
    """Forward-Only Deploy Guard must precede systemctl restart."""
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    restart_idx = _line_index(block, "systemctl restart toanaas-web.service")
    assert guard_idx < restart_idx, (
        f"Forward-Only Deploy Guard (line {guard_idx}) must precede "
        f"systemctl restart (line {restart_idx})"
    )


def test_forward_guard_before_backup() -> None:
    """Forward-Only Deploy Guard must precede backup creation."""
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    backup_idx = _line_index(block, "Creating Tracked Source Backup")
    assert guard_idx < backup_idx, (
        f"Forward-Only Deploy Guard (line {guard_idx}) must precede "
        f"Creating Tracked Source Backup (line {backup_idx})"
    )


def test_no_source_mutation_before_guard() -> None:
    """No source-mutating operations may appear before the forward guard.

    Source mutations: tar extraction, git update-ref (heads/main),
    systemctl restart, file quarantine moves.
    """
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    guard_idx = _line_index(block, "Forward-Only Deploy Guard")
    mutation_markers = [
        "Applying Release Source",
        "Restarting Web Service",
        "Quarantining Removed",
        "Creating Tracked Source Backup",
    ]
    for marker in mutation_markers:
        marker_idx = _line_index(block, marker)
        assert marker_idx > guard_idx, (
            f"Mutation '{marker}' (line {marker_idx}) must not appear "
            f"before Forward-Only Deploy Guard (line {guard_idx})"
        )


def test_full_safe_execution_order() -> None:
    """Verify the complete safe execution order:
    fetch_bundle < target_verify < forward_guard < backup < quarantine < apply < restart.
    """
    block = _ssh_block(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    ordered_markers = [
        ("release.bundle", "fetch bundle"),
        ("git cat-file -e", "target verify"),
        ("Forward-Only Deploy Guard", "forward guard"),
        ("Creating Tracked Source Backup", "backup"),
        ("Quarantining Removed", "quarantine"),
        ("Applying Release Source", "apply"),
        ("systemctl restart toanaas-web.service", "restart"),
    ]
    indices = []
    for marker, label in ordered_markers:
        idx = _line_index(block, marker)
        indices.append((idx, label))
    for i in range(len(indices) - 1):
        curr_idx, curr_label = indices[i]
        next_idx, next_label = indices[i + 1]
        assert curr_idx < next_idx, (
            f"Order violation: '{curr_label}' (line {curr_idx}) must precede "
            f"'{next_label}' (line {next_idx})"
        )
