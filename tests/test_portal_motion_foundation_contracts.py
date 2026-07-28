"""Red presentation contracts for the shared portal motion foundation.

The checks stay deliberately static and presentation-only.  They describe the
public shell asset, its safe browser-only utility, and the mount lifecycle
without changing authentication, payment, provider, or data ownership.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SHELL_TEMPLATE = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
MOTION_ASSET = ROOT / "static" / "portal" / "portal-motion.js"

PORTAL_SCRIPT = '<script src="/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
MOTION_SCRIPT = '<script src="/static/portal/portal-motion.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
INTEGRATION_SCRIPT = '<script src="/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__" defer></script>'


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def _motion_source() -> str:
    assert MOTION_ASSET.is_file(), "portal motion must be a checked-in public shell asset"
    return MOTION_ASSET.read_text(encoding="utf-8")


def _theme_root() -> str:
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    assert root is not None
    return root.group("declarations")


def _theme_rule(selector: str) -> str:
    rule = re.search(re.escape(selector) + r"\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    assert rule is not None
    return rule.group("declarations")


def test_motion_asset_is_versioned_between_portal_and_integration_and_pre_cached() -> None:
    assert MOTION_ASSET.is_file(), "portal motion must be a checked-in public shell asset"
    assert MOTION_SCRIPT in SHELL_TEMPLATE
    assert SHELL_TEMPLATE.index(PORTAL_SCRIPT) < SHELL_TEMPLATE.index(MOTION_SCRIPT) < SHELL_TEMPLATE.index(INTEGRATION_SCRIPT)

    build_sources = _section(PAGES, "_PORTAL_BUILD_SOURCE_FILES = (", ")\n\n# The portal shell")
    local_build_fallback = _section(PAGES, "def _local_portal_build_id()", "\n\ndef _portal_build_id()")
    fallback_template = _section(PAGES, "def _fallback_template()", "\n\ndef render_portal")
    assert '"portal-motion.js",' in build_sources
    assert "for filename in _PORTAL_BUILD_SOURCE_FILES:" in local_build_fallback
    assert 'digest.update(b"missing")' in local_build_fallback
    assert MOTION_SCRIPT in fallback_template.replace('\\"', '"')

    shell_allow_list = _section(WORKER, "const SHELL = Object.freeze([", "]);\nconst SHELL_PATHS")
    assert '"/static/portal/portal-motion.js",' in shell_allow_list


def test_motion_utility_is_browser_only_progressive_enhancement() -> None:
    motion = _motion_source()

    assert "window.TOANAASPortalMotion = Object.freeze(" in motion
    assert re.search(r"TOANAASPortalMotion\s*=\s*Object\.freeze\(\s*\{[\s\S]*?\breplace\b", motion)
    assert "document.startViewTransition" in motion
    assert "prefers-reduced-motion: reduce" in motion
    forbidden_patterns = (
        r"\bfetch\s*\(",
        r"\blocalStorage\b",
        r"\bsessionStorage\b",
        r"\binnerHTML\b",
        r"/api/",
        r"\bcsrf\b",
        r"\bXMLHttpRequest\b",
        r"\bsendBeacon\b",
        r"\bWebSocket\b",
        r"\bEventSource\b",
        r"\bindexedDB\b",
        r"\bcaches\b",
        r"\bdocument\s*\.\s*cookie\b",
        r"\binsertAdjacentHTML\b",
        r"\bouterHTML\b",
    )
    for forbidden in forbidden_patterns:
        assert re.search(forbidden, motion, flags=re.IGNORECASE) is None


def test_motion_utility_waits_for_view_transition_dom_update_before_entering() -> None:
    motion = _motion_source()

    # `startViewTransition()` may defer its update callback until the previous
    # snapshot is captured.  Enter animation must therefore wait for the DOM
    # update rather than running against the outgoing workspace.
    assert "transition.updateCallbackDone" in motion
    assert re.search(
        r"transition\.updateCallbackDone\.then\(\(\)\s*=>\s*\{?\s*"
        r"enter\(main,\s*[\"']enter[\"']\)",
        motion,
    )


def test_theme_declares_shared_portal_motion_tokens_and_lifecycle_selectors() -> None:
    root = _theme_root()
    expected_tokens = (
        "--portal-motion-fast: 140ms;",
        "--portal-motion-base: 220ms;",
        "--portal-motion-slow: 420ms;",
        "--portal-motion-distance: 10px;",
        "--portal-motion-ease-standard: cubic-bezier(.2,.8,.2,1);",
        "--portal-motion-ease-emphasis: cubic-bezier(.16,1,.3,1);",
    )

    for token in expected_tokens:
        assert token in root

    enter = _theme_rule('[data-portal-motion="enter"]')
    pop = _theme_rule('[data-portal-motion="pop"]')
    assert "animation: portal-motion-enter var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;" in enter
    assert "animation: portal-motion-pop var(--portal-motion-fast) var(--portal-motion-ease-standard) both;" in pop
    assert re.search(r"@keyframes portal-motion-enter\s*\{[\s\S]*?to\s*\{", THEME)
    assert re.search(r"@keyframes portal-motion-pop\s*\{[\s\S]*?to\s*\{", THEME)
    assert re.search(
        r"@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]{0,1200}?"
        r"\[data-portal-motion\][\s\S]{0,500}?animation:\s*none\s*!important;[\s\S]{0,500}?"
        r"transition:\s*none\s*!important;",
        THEME,
    )


def test_mount_portal_assigns_surface_and_delegates_render_lifecycle_to_motion() -> None:
    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    assert 'const surface = isLanding ? "landing" : (isAuth ? "auth" : "workspace");' in mount
    assert "shell.dataset.portalSurface = surface;" in mount
    assert "document.body.dataset.portalSurface = surface;" in mount
    assert "const motion = window.TOANAASPortalMotion || Object.freeze({" in mount
    assert re.search(r"replace\([^)]*render[^)]*\)\s*\{\s*render\(\);\s*\}", mount)
    render_shell = _section(
        mount,
        "function renderShell() {",
        "\n    const replaceResult = motion.replace(shell, main, renderShell);",
    )
    for rendering_step in (
        "sidebar.innerHTML = renderSidebar(page, context);",
        "header.innerHTML = renderHeader(page, context);",
        "main.innerHTML = renderPage(page, context);",
        "placeSfxCueSheetReceipt(main);",
        "bindInteractions();",
        "syncPwaInstallControl();",
    ):
        assert rendering_step in render_shell
    assert "const replaceResult = motion.replace(shell, main, renderShell);" in mount
    assert "restoreFocus(focus);" in mount
    assert mount.index("const replaceResult = motion.replace(shell, main, renderShell);") < mount.index("restoreFocus(focus);")


def test_mount_restores_focus_after_the_deferred_render_completes() -> None:
    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    # The first deferred script can mount before the optional presentation
    # utility loads, while a supported View Transition may defer the DOM swap.
    # Both paths must restore focus only after the renderer has run.
    assert "const replaceResult = motion.replace(shell, main, renderShell);" in mount
    assert re.search(
        r"replaceResult\.then\(\(\)\s*=>\s*restoreFocus\(focus\),\s*"
        r"\(\)\s*=>\s*restoreFocus\(focus\)\)",
        mount,
    )
