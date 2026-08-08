"""Focused contracts for the public Landing Cinematic Mini.

These are intentionally static contracts: motion is presentation-only, and
the existing portal tests already own server/routing/auth behaviour.  The
contracts keep the enhancement narrowly scoped to ``/welcome`` with a
``?motion=0`` comparison opt-out, while making the DOM hooks and CSS/lifecycle
boundaries reviewable without a browser.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def _root_declarations() -> str:
    match = re.search(r":root\s*\{(?P<body>.*?)\n\}", THEME, flags=re.DOTALL)
    assert match is not None
    return match.group("body")


def test_motion_is_default_for_welcome_with_a_safe_opt_out_and_landing_only_cleanup() -> None:
    mount = _between(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    assert 'window.location.pathname === "/welcome"' in mount
    assert 'new URLSearchParams(window.location.search || "").get("motion") !== "0"' in mount
    assert "motion.unmountLanding" in mount
    assert re.search(r"if\s*\(landingMotionEnabled[\s\S]{0,500}?motion\.mountLanding", mount)
    assert mount.index("motion.unmountLanding") < mount.index("function renderShell()")
    assert mount.index("motion.mountLanding") > mount.index("main.innerHTML = renderPage(page, context);")

    assert "mountLanding" in MOTION
    assert "unmountLanding" in MOTION


def test_landing_motion_uses_existing_public_landing_structure_without_copy_changes() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")

    for existing_hook in (
        "portal-landing-hero-copy",
        "portal-landing-hero-actions",
        "portal-landing-preview",
        "portal-landing-section-heading",
        "portal-landing-studio",
        "portal-landing-workflow",
        "portal-landing-trust",
        "portal-landing-final",
    ):
        assert existing_hook in landing

    for selector in (
        ".portal-landing-hero-copy",
        ".portal-landing-hero-actions",
        ".portal-landing-proof",
        ".portal-landing-preview",
        ".portal-landing-section",
        ".portal-landing-studio",
        ".portal-landing-workflow",
        ".portal-landing-trust",
        ".portal-landing-final",
    ):
        assert selector in MOTION

    # The existing four-step workflow remains the source of the staged list.
    assert 'const workflowSteps = ["brief", "plan", "confirm", "delivery"];' in landing


def test_landing_motion_helper_is_browser_only_io_raf_passive_and_cleanup_safe() -> None:
    assert "typeof window" in MOTION
    assert "IntersectionObserver" in MOTION
    assert "requestAnimationFrame" in MOTION
    assert "cancelAnimationFrame" in MOTION
    assert re.search(r"addEventListener\(\s*[\"']scroll[\"'][\s\S]{0,180}?passive:\s*true", MOTION)
    assert re.search(r"removeEventListener\(\s*[\"']scroll[\"']", MOTION)
    assert "focusin" in MOTION
    assert re.search(r"removeEventListener\(\s*[\"']focusin[\"']", MOTION)
    assert "disconnect()" in MOTION
    assert "prefersReducedMotion" in MOTION

    for forbidden in (
        r"\bfetch\s*\(",
        r"\blocalStorage\b",
        r"\bsessionStorage\b",
        r"\bXMLHttpRequest\b",
        r"\bWebSocket\b",
        r"\bEventSource\b",
        r"\binnerHTML\b",
        r"\bstyle\.width\b",
        r"\bstyle\.height\b",
    ):
        assert re.search(forbidden, MOTION, flags=re.IGNORECASE) is None


def test_landing_motion_theme_has_local_timing_tokens_and_selector_gate() -> None:
    root = _root_declarations()
    for token in (
        "--portal-landing-motion-fast: 160ms;",
        "--portal-landing-motion-ui: 220ms;",
        "--portal-landing-motion-reveal: 480ms;",
        "--portal-landing-motion-hero: 600ms;",
        "--portal-landing-motion-stagger: 80ms;",
    ):
        assert token in root

    assert '[data-landing-motion="cinematic-mini"]' in THEME
    for selector in (
        "landing-motion-header",
        "landing-motion-hero",
        "landing-motion-reveal",
        "landing-motion-card",
        "landing-motion-workflow",
        "landing-motion-final",
        "landing-motion-cta",
    ):
        assert selector in THEME

    assert "backdrop-filter var(--portal-landing-motion-ui)" in THEME
    final_cta = re.search(
        r"\.landing-motion-final \.landing-motion-cta\s*\{(?P<body>[^}]*)\}",
        THEME,
    )
    assert final_cta is not None
    assert "animation" not in final_cta.group("body")

    card_reveal = re.search(
        r"\.landing-motion-reveal\.is-visible \.landing-motion-card\s*\{(?P<body>[^}]*)\}",
        THEME,
    )
    assert card_reveal is not None
    assert "backwards" in card_reveal.group("body")
    assert "both" not in card_reveal.group("body")
    assert ".landing-motion-workflow.is-visible .landing-motion-card" in THEME
    assert "animation-duration: 400ms;" in THEME


def test_landing_motion_theme_keeps_motion_transform_only_and_reduced_content_visible() -> None:
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    reduced = THEME[THEME.index("@media (prefers-reduced-motion: reduce)"):]
    assert "animation: none !important;" in reduced
    assert "transition: none !important;" in reduced
    assert "opacity: 1 !important;" in reduced
    assert "transform: none !important;" in reduced

    # The experiment must not introduce motion patterns outside the explicit
    # landing test gate.
    gated = THEME[THEME.index('[data-landing-motion="cinematic-mini"]'):]
    assert ".landing-motion-header" in gated
    assert "position: sticky;" in gated
    assert "scroll-behavior" not in gated
    assert "will-change:" not in gated
    assert "translateZ" not in gated
    assert "scale(1.02" not in gated
    assert "scale(1.03" not in gated
    assert ".landing-motion-reveal.is-pending:focus-within" in gated
    assert ".landing-motion-hero:focus-within" in gated
    assert ".landing-motion-reveal:focus-within" in gated
    assert "animation: none;" in gated
