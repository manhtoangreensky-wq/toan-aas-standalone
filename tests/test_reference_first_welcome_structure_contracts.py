"""Static contracts for the public reference-first Welcome structure.

The supplied reference may inform information hierarchy and product-surface
rhythm.  These checks keep the TOAN AAS implementation original, truthful and
limited to the existing public route boundaries.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _rule(source: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>.*?)\n\}", source, flags=re.DOTALL)
    assert match, f"Missing CSS rule for {selector}"
    return match.group("body")


def test_reference_first_welcome_keeps_a_truthful_product_surface_and_real_entry_actions() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")

    assert 'class="portal-landing-hero-stage"' in landing
    assert 'portal-landing-product-surface"' in landing
    assert 'portal-landing-product-surface-head"' in landing
    assert 'portal-landing-product-surface-flow"' in landing
    assert 'data-landing-pointer="preview"' in landing
    assert 'href="/register"' in landing
    assert 'href="/login"' in landing
    assert 'href="/dashboard"' in landing
    assert 'href="/features"' in landing

    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        "sessionStorage",
        "data-portal-action",
        "payment",
        "wallet",
        "provider",
        "telegram",
        "testimonial",
        "rating",
        "trusted by",
        "120+",
        "50K+",
        "99.9%",
    ):
        assert forbidden not in landing.lower()


def test_reference_first_welcome_turns_existing_studios_into_a_scannable_discovery_rail() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")

    assert 'portal-landing-discovery-rail"' in landing
    assert 'portal-landing-discovery-intro"' in landing
    assert 'portal-landing-discovery-list"' in landing
    assert "const studios = [" in landing
    assert 'const studioCards = studios.map(' in landing
    assert "studioCards" in landing
    assert landing.index("portal-landing-discovery-rail") < landing.index('id="workflow"')
    for route in ("/chat", "/image/create", "/video/create", "/voice/tts", "/subtitle", "/documents"):
        assert route in landing


def test_reference_first_welcome_has_complete_trilingual_structural_copy() -> None:
    for key in (
        "landing.hero.productLabel",
        "landing.hero.productBody",
        "landing.discovery.label",
        "landing.discovery.cta",
    ):
        assert I18N.count(f'"{key}"') == 3


def test_public_welcome_keeps_the_server_reviewed_query_locale_over_signed_profile_locale() -> None:
    locale_selection = _between(PORTAL, "function interfaceLocaleFor(context)", "function applyInterfaceLocale(context)")

    assert 'const isPublicWelcome = normalizePath(context && context.path || window.location.pathname || "/") === "/welcome";' in locale_selection
    assert 'const candidate = isPublicWelcome' in locale_selection
    assert 'bootstrapLocale || profileLocale || "vi"' in locale_selection
    assert 'profileLocale || bootstrapLocale || "vi"' in locale_selection


def test_reference_first_welcome_uses_token_only_responsive_motion_safe_presentation() -> None:
    for selector in (
        ".portal-landing-hero-stage",
        ".portal-landing-product-surface",
        ".portal-landing-product-surface-head",
        ".portal-landing-product-surface-flow",
        ".portal-landing-discovery-rail",
        ".portal-landing-discovery-list",
        ".portal-landing-discovery-intro",
    ):
        assert selector in THEME

    product_surface = _rule(THEME, ".portal-landing-product-surface")
    discovery_list = _rule(THEME, ".portal-landing-discovery-list")
    discovery_card = _rule(THEME, ".portal-landing-discovery-list .portal-landing-studio")

    assert "z-index: 1;" in product_surface
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in discovery_list
    assert "min-height: 44px;" in discovery_card
    assert ".portal-landing-discovery-list .portal-landing-studio:focus-visible" in THEME
    assert "@media (max-width: 920px)" in THEME
    assert "@media (max-width: 600px)" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    assert "#" not in THEME[THEME.index(".portal-landing-hero-stage"):]


def test_reference_first_product_surface_copy_keeps_its_compact_preview_type_scale() -> None:
    preview_copy = _rule(THEME, ".portal-landing-hero .portal-landing-product-surface-copy")

    assert "font-size: 12px;" in preview_copy
    assert "line-height: 1.55;" in preview_copy


def test_reference_first_welcome_has_route_only_product_spotlights_between_hero_and_tool_directory() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")

    assert 'portal-landing-feature-strip"' in landing
    assert 'portal-landing-spotlights"' in landing
    assert 'portal-landing-spotlight--${safeText(item.key)}' in landing
    assert 'key: "content"' in landing
    assert 'key: "audio"' in landing
    assert 'data-landing-layer="spotlights"' in landing
    assert landing.index("portal-landing-feature-strip") < landing.index("portal-landing-spotlights") < landing.index("portal-landing-discovery-rail")
    for route in ("/content-studio", "/media-workspace"):
        assert route in landing
    for forbidden in (
        "fetch(",
        "data-portal-action",
        "provider",
        "payment",
        "wallet",
        "job",
        "output",
        "testimonial",
        "rating",
    ):
        assert forbidden not in _between(landing, "const spotlight", "const studioCards").lower()


def test_reference_first_welcome_has_trilingual_spotlight_copy_and_token_only_responsive_layout() -> None:
    for key in (
        "landing.featureStrip.content.title",
        "landing.featureStrip.content.body",
        "landing.featureStrip.security.title",
        "landing.featureStrip.security.body",
        "landing.featureStrip.delivery.title",
        "landing.featureStrip.delivery.body",
        "landing.spotlight.content.kicker",
        "landing.spotlight.content.title",
        "landing.spotlight.content.body",
        "landing.spotlight.content.cta",
        "landing.spotlight.audio.kicker",
        "landing.spotlight.audio.title",
        "landing.spotlight.audio.body",
        "landing.spotlight.audio.cta",
    ):
        assert I18N.count(f'"{key}"') == 3

    for selector in (
        ".portal-landing-feature-strip",
        ".portal-landing-spotlights",
        ".portal-landing-spotlight",
        ".portal-landing-spotlight--audio",
        ".portal-landing-spotlight-preview",
    ):
        assert selector in THEME
    assert "#" not in THEME[THEME.index(".portal-landing-feature-strip"):]


def test_reference_first_welcome_reveals_its_feature_strip_and_spotlights_as_real_motion_scenes() -> None:
    """New reference-first sections must join the mounted motion lifecycle.

    The page must not only carry decorative motion CSS: the mounted landing
    runtime has to observe the sections, release them for keyboard focus, and
    clean their generated classes on a route replacement.
    """
    motion = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
    landing_motion = _between(motion, "function mountLanding(root)", "window.TOANAASPortalMotion")

    assert '".portal-landing-feature-strip, .portal-landing-spotlights"' in landing_motion
    assert ".portal-landing-feature-strip article" in landing_motion
    assert ".portal-landing-spotlight" in landing_motion
    assert '"landing-motion-features"' in landing_motion
    assert '"landing-motion-spotlights"' in landing_motion
    assert ".portal-landing-spotlight-preview" in landing_motion
    assert ".landing-motion-features" in THEME
    assert ".landing-motion-spotlights" in THEME
