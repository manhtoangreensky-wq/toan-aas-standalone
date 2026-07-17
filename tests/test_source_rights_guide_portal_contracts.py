"""Static contracts for the Bot-derived read-only source/dubbing guide."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_source_rights_guide_is_private_read_only_and_derives_the_bot_guardrails() -> None:
    assert 'customerPage("/guides/source-rights", "Nguồn tư liệu & Dubbing hợp lệ"' in PORTAL
    assert 'layout: "source-rights-guide", type: "source-rights-guide", fields: [], action: "none"' in PORTAL
    assert "const SOURCE_RIGHTS_ALLOWED" in PORTAL
    assert "const SOURCE_RIGHTS_NOT_SUPPORTED" in PORTAL
    assert "const DUBBING_RIGHTS_RULES" in PORTAL
    assert "function renderSourceRightsGuide(page, context)" in PORTAL
    assert 'case "source-rights-guide": return renderSourceRightsGuide(page, context);' in PORTAL
    guide = PORTAL[PORTAL.index("const SOURCE_RIGHTS_ALLOWED"):PORTAL.index("const IMAGE_PROMPT_COMPOSER_GOAL_OPTIONS")]
    for forbidden in ("api(", "fetch(", "data-portal-action", "localStorage"):
        assert forbidden not in guide


def test_source_rights_guide_requires_signed_context_and_never_enters_pwa_cache() -> None:
    assert '"/guides/source-rights": account && contentStudioEnabled ? "ready" : "guarded"' in INTEGRATION
    assert '"/guides/source-rights"' in WORKER
    assert "toan-aas-portal-shell-v36" in WORKER
