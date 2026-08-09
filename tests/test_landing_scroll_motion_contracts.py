"""Contracts for the continuous, scroll-aware public landing motion layer.

The motion is presentation-only: it may read viewport/pointer state and write
CSS variables/classes, but it must not call APIs, persist browser data, or
change the route's authority/data boundary.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def test_landing_markup_exposes_semantic_motion_layers_without_new_runtime_state() -> None:
    landing = PORTAL[PORTAL.index("function renderLanding(page, context)") : PORTAL.index("function renderVideoFinalization", PORTAL.index("function renderLanding(page, context)"))]
    for marker in (
        'data-landing-layer="hero"',
        'data-landing-layer="studios"',
        'data-landing-layer="workflow"',
        'data-landing-layer="trust"',
        'data-landing-layer="final"',
        'data-landing-pointer="preview"',
        'data-landing-pointer="studio"',
    ):
        assert marker in landing


def test_scroll_runtime_uses_raf_css_variables_and_cleans_all_listeners() -> None:
    for phrase in (
        "data-landing-scroll-progress",
        "--landing-scroll-progress",
        "--landing-hero-progress",
        "requestAnimationFrame",
        "addEventListener(\"scroll\"",
        "addEventListener(\"pointermove\"",
        "removeEventListener(\"pointermove\"",
        "removeEventListener(\"scroll\"",
        "landing-motion-scroll",
    ):
        assert phrase in MOTION
    for forbidden in (r"\bfetch\s*\(", r"\blocalStorage\b", r"\bsessionStorage\b", r"\bWebSocket\b"):
        assert re.search(forbidden, MOTION, flags=re.IGNORECASE) is None


def test_motion_css_has_distinct_scroll_reveal_parallax_and_pointer_variants() -> None:
    motion = THEME[THEME.index('.landing-motion-scroll[data-landing-scroll-motion="active"]') :]
    for marker in (
        "landing-scroll-scene",
        "landing-motion-parallax",
        "landing-motion-pointer",
        "landing-motion-studio",
        "landing-motion-workflow",
        "landing-motion-trust",
        "--landing-pointer-x",
        "--landing-pointer-y",
        "clip-path",
        "prefers-reduced-motion: reduce",
    ):
        assert marker in motion
    assert "animation-iteration-count: infinite" not in motion


def test_motion_fails_open_for_content_and_respects_reduced_motion() -> None:
    motion = THEME[THEME.index('[data-landing-motion="cinematic-mini"]') :]
    assert "content-visibility" not in motion
    for declaration in ("opacity: 1 !important;", "transform: none !important;", "clip-path: none !important;"):
        assert declaration in motion


def test_motion_opt_out_does_not_leave_an_inert_replay_control() -> None:
    """The visible replay affordance must reflect the selected motion mode."""
    assert "setReplayAvailability" in MOTION
    assert "replayControl.hidden = !enabled" in MOTION
    assert "replayControl.disabled = !enabled" in MOTION
    assert 'data-landing-motion-replay-disabled' in MOTION
    assert "if (!landingMotionEnabled)" in PORTAL
    assert 'data-landing-motion-replay-disabled' in PORTAL


def test_replay_focus_does_not_cancel_the_hero_replay_animation() -> None:
    """Keyboard focus on replay is an action, not a reason to clear the hero."""
    assert '.landing-motion-hero:focus-within:not(:has([data-landing-motion-replay]:focus))' in THEME


def test_preview_scan_uses_compositor_friendly_keyframes() -> None:
    """The finite preview scan must not repaint a box shadow every frame."""
    start = THEME.index("@keyframes portal-landing-preview-scan")
    end = THEME.index("@media (prefers-reduced-motion: no-preference)", start)
    keyframes = THEME[start:end]
    assert "opacity:" in keyframes
    assert "transform:" in keyframes
    assert "box-shadow:" not in keyframes


def test_each_scroll_section_has_a_distinct_pointer_response() -> None:
    motion = THEME[THEME.index('.landing-motion-scroll[data-landing-scroll-motion="active"]') :]
    for marker in (
        ".landing-motion-parallax.landing-motion-pointer",
        ".landing-motion-workflow li.landing-motion-pointer.is-pointer-active",
        ".portal-landing-trust-grid > article.landing-motion-pointer.is-pointer-active",
    ):
        assert marker in motion
    assert ".landing-motion-trust-grid" not in motion
