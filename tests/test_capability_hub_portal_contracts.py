"""Static product boundary checks for the aggregate Capability Hub."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_exposes_only_aggregate_static_capability_hub() -> None:
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    hub = (ROOT / "copyfast_capability_hub.py").read_text(encoding="utf-8")
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")

    assert '"capability_hub": capability_hub()' in api
    assert "def build_capability_hub" in hub
    assert "never imports the Telegram bot" in hub
    assert "raw Bot command, callback" in hub
    assert "function renderCapabilityHub(context)" in portal
    assert "Không có lệnh thô" in portal
    assert "capabilityHub: normalizeCapabilityHub(source.capabilityHub)" in portal
    assert "const capabilityHub = catalogData.capability_hub" in integration
    assert "never grants a feature capability" in integration


def test_capability_hub_contract_documents_static_only_and_execution_boundary() -> None:
    contract = (ROOT / "docs" / "migration" / "CAPABILITY_HUB_CONTRACT.md").read_text(encoding="utf-8")

    assert "static-only" in contract
    assert "never imports `bot.py`" in contract
    assert "No static count may be represented as successful execution" in contract
