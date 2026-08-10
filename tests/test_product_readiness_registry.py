"""Behavior contracts for the public product-readiness taxonomy."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _readiness_module():
    module_path = ROOT / "copyfast_product_readiness.py"
    assert module_path.exists(), "the centralized product-readiness registry is missing"
    return importlib.import_module("copyfast_product_readiness")


def test_readiness_registry_exposes_the_closed_product_taxonomy() -> None:
    readiness = _readiness_module()

    assert readiness.READINESS_STATES == frozenset({
        "available",
        "planning_only",
        "local_execution",
        "canonical_read",
        "guarded",
        "disabled",
    })
    assert readiness.readiness_descriptor(
        "dashboard", {"copyfast_enabled": True}, bridge_ready=False
    ) == {"status": "available"}
    assert readiness.readiness_descriptor(
        "video_studio", {"video_studio_enabled": True}, bridge_ready=False
    ) == {"status": "planning_only"}
    assert readiness.readiness_descriptor(
        "documents_merge",
        {"asset_vault_enabled": True, "document_operations_enabled": True},
        bridge_ready=False,
    ) == {"status": "local_execution"}


def test_readiness_registry_fails_closed_for_paused_canonical_or_unknown_features() -> None:
    readiness = _readiness_module()

    assert readiness.readiness_descriptor(
        "documents_merge", {"asset_vault_enabled": True, "document_operations_enabled": False}, bridge_ready=False
    ) == {"status": "disabled"}
    assert readiness.readiness_descriptor("wallet", {"copyfast_enabled": True}, bridge_ready=False) == {"status": "guarded"}
    assert readiness.readiness_descriptor("wallet", {"copyfast_enabled": True}, bridge_ready=True) == {"status": "canonical_read"}
    assert readiness.readiness_descriptor("wallet_topup", {"copyfast_enabled": True}, bridge_ready=True) == {"status": "guarded"}
    assert readiness.readiness_descriptor("unreviewed_feature", {}, bridge_ready=True) == {"status": "guarded"}


def test_pricing_tracks_the_canonical_bridge_boundary() -> None:
    readiness = _readiness_module()

    assert readiness.readiness_descriptor(
        "pricing", {"copyfast_enabled": True}, bridge_ready=False
    ) == {"status": "guarded"}
    assert readiness.readiness_descriptor(
        "pricing", {"copyfast_enabled": True}, bridge_ready=True
    ) == {"status": "canonical_read"}


def test_partner_readiness_tracks_its_maintenance_flag() -> None:
    readiness = _readiness_module()

    assert readiness.readiness_descriptor(
        "partner_readiness", {"partner_readiness_enabled": False}, bridge_ready=False
    ) == {"status": "disabled"}
    assert readiness.readiness_descriptor(
        "partner_readiness", {"partner_readiness_enabled": True}, bridge_ready=False
    ) == {"status": "available"}


def test_readiness_registry_has_no_bridge_or_provider_imports() -> None:
    module_path = ROOT / "copyfast_product_readiness.py"
    assert module_path.exists(), "the centralized product-readiness registry is missing"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])

    assert {"bot", "copyfast_bridge", "requests", "httpx", "subprocess"}.isdisjoint(imported)
