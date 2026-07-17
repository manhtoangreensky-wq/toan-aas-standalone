"""Focused responsive contract for the signed Web authentication entry point."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def test_auth_intro_stays_at_the_top_when_the_provider_card_is_taller() -> None:
    """A long OAuth card must not vertically push the login title below fold."""

    rule = CSS.split(".portal-auth-page {", 1)[1].split("}", 1)[0]
    assert "align-items: start" in rule
    assert "align-content: start" in rule
    assert "padding-top: 68px" in rule
    assert 'class="portal-auth-intro"' in PORTAL
    assert 'class="portal-card portal-card-pad portal-auth-card"' in PORTAL
