"""Static integration contracts for display-only engine catalog labels."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_enriches_entries_with_a_safe_engine_descriptor_only() -> None:
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    engine = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")

    assert 'item["engine"] = engine_descriptor' in api
    assert "from copyfast_web_engine import engine_descriptor" in api
    assert "from copyfast_bridge import" not in engine
    assert "import bot" not in engine
    assert "import requests" not in engine
    public_section = engine[engine.index("def engine_descriptor"):]
    assert 'return {"mode": mode, "execution_state": state}' in public_section
    assert "handler_name" not in public_section
    assert "required_flags" not in public_section


def test_portal_uses_a_finite_display_only_engine_label_on_catalog_cards() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

    assert 'const CATALOG_ENGINE_MODES = new Set(["web_native", "bot_companion", "guarded"])' in portal
    assert "function normalizeCatalogEngine(raw)" in portal
    assert "function renderEngineLabel(module)" in portal
    assert "Phân loại execution; không xác nhận job, payment hoặc output." in portal
    assert 'moduleCard(entry, context, "Mở workflow", { showEngineLabel: true })' in portal
    assert "portal-module-card-signals" in portal
    assert '.portal-engine-label[data-engine-mode="web_native"]' in css
    assert '.portal-engine-label[data-engine-mode="bot_companion"]' in css
    assert '.portal-engine-label[data-engine-mode="guarded"]' in css


def test_engine_label_does_not_control_actions_or_call_external_capabilities() -> None:
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    label = portal[portal.index("function renderEngineLabel(module)"):portal.index("function catalogEntryState(module, page, context)")]
    state = portal[portal.index("function catalogEntryState(module, page, context)"):portal.index("function moduleCard(module, context, label, options)")]

    assert "canAct" not in label
    assert "fetch(" not in label
    assert "api(" not in label
    assert "provider" not in label.lower()
    assert "wallet" not in label.lower()
    assert 'api("/payments' not in label
    assert 'api("/wallet' not in label
    assert "engine" not in state


def test_engine_contract_documents_the_no_capability_boundary() -> None:
    contract = (ROOT / "docs" / "migration" / "WEB_ENGINE_REGISTRY_CONTRACT.md").read_text(encoding="utf-8")

    assert "never a permission, quote, job, payment, output or" in contract
    assert "The registry imports no Bot, Core Bridge, provider, wallet, PayOS" in contract.replace("\n", " ")
    assert "global provider flag alone is insufficient" in contract
