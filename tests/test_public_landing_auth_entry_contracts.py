"""Static contracts for public landing account-entry actions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_public_landing_hero_secondary_action_uses_truthful_auth_entry_routes() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    primary_action = _between(
        landing,
        "const primaryAction = signedIn",
        "const heroSecondaryAction",
    )
    hero_secondary_action = _between(
        landing,
        "const heroSecondaryAction = signedIn",
        "const navigationAction",
    )
    hero_actions = _between(
        landing,
        '<div class="portal-landing-hero-actions">',
        '<ul class="portal-landing-proof"',
    )

    signed_primary = '? `<a class="portal-button portal-button--primary" href="/dashboard"><span>${text("cta.workspace")}'
    anonymous_primary = ': `<a class="portal-button portal-button--primary" href="/register"><span>${text("cta.start")}'
    assert signed_primary in primary_action
    assert anonymous_primary in primary_action
    assert primary_action.index(signed_primary) < primary_action.index(anonymous_primary)
    assert primary_action.count("<a ") == 2

    signed_secondary = '? `<a class="portal-button" href="/features"><span>${text("hero.explore")}'
    anonymous_secondary = ': `<a class="portal-button" href="/login"><span>${text("cta.signIn")}'
    assert signed_secondary in hero_secondary_action
    assert anonymous_secondary in hero_secondary_action
    assert hero_secondary_action.index(signed_secondary) < hero_secondary_action.index(anonymous_secondary)
    assert hero_secondary_action.count("<a ") == 2
    assert hero_actions == '<div class="portal-landing-hero-actions">${primaryAction}${heroSecondaryAction}</div>'


def test_public_landing_hero_secondary_action_stays_static_and_reuses_reviewed_copy() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    hero_secondary_action = _between(landing, "const heroSecondaryAction = signedIn", "const navigationAction")

    assert I18N.count('"landing.cta.signIn"') == 3
    assert I18N.count('"landing.hero.explore"') == 3
    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        "sessionStorage",
        "data-portal-action",
        "<form",
        "payment",
        "wallet",
        "provider",
        "telegram",
    ):
        assert forbidden not in hero_secondary_action
