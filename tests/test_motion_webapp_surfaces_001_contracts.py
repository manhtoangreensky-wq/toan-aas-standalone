from hashlib import sha256
from pathlib import Path
import json, re, subprocess, sys


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "static" / "portal" / "portal.css"
THEME_PATH = ROOT / "static" / "portal" / "portal-theme.css"
MOTION_PATH = ROOT / "static" / "portal" / "portal-motion.js"
PORTAL_PATH = ROOT / "static" / "portal" / "portal.js"
INTEGRATION_PATH = ROOT / "static" / "portal" / "integration.js"
BASE_SHA = "896d3761aa1126cf4bd6a6f08e2f9a9d7c51e972"
PORTAL_PRE_AMENDMENT_HASH = "ba802f9f9c41fd003d78dde38b31391278303f2ade2ba0cbd75eedba64c388d5"
PORTAL_AMENDED_HASH = "5806db0131dd9fcafff3700d34f7b9f8ba1073c49d00e364d52dc809cf6a0eeb"

PROTECTED_HASHES = {
    "static/portal/portal-theme.css": "944b3dddeebe307f98b6d674191888b8d3c28424aa3ad84c8b7eba7255289f47",
    "static/portal/portal-motion.js": "9f03ff775c10a8a55781a655b48e4c6c68d2d53e63d50188fa351deac9d90d14",
    "static/portal/integration.js": "3d65506345bc36728284f8bd8bb0375aa43d2bbc5711cacbe6291386f91411a1",
    "static/portal/portal-auth.js": "1452263d258ff9f56ebf8b0a7f17192091a4635db2a80b7ca32120407a9b59d3",
}

EXPECTED_TRANSITIONS = {
    ".portal-session-chip": [
        "background-color .16s ease, border-color .16s ease, color .16s ease",
    ],
    ".portal-install-tab-btn": [
        "color .15s ease, background-color .15s ease",
        "color 0.16s ease, background-color 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease",
    ],
    ".portal-auth-submit-btn": [
        "transform 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important",
    ],
    ".portal-auth-app-link": [
        "background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.16s ease",
    ],
    ".portal-free-tab-btn": [
        "background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease",
    ],
    ".portal-btn-install": [
        "transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.18s cubic-bezier(0.16, 1, 0.3, 1), filter 0.18s cubic-bezier(0.16, 1, 0.3, 1)",
    ],
    ".portal-btn-dismiss,\n.portal-btn-collapse": [
        "background-color 0.15s ease, color 0.15s ease",
    ],
}

EXPECTED_STATES = {
    ".portal-session-chip:hover": ("border-color:", "background:", "color:"),
    ".portal-install-tab-btn:hover": ("color:", "background:"),
    ".portal-install-tab-btn.is-active": ("background:", "color:"),
    ".portal-auth-submit-btn:hover": ("transform: translateY(-1px)",),
    ".portal-auth-submit-btn:active": ("transform: scale(0.99)",),
    ".portal-auth-app-link:hover": ("background:", "border-color:", "color:", "transform:"),
    ".portal-free-tab-btn:hover": ("border-color:", "background:", "color:", "transform:"),
    ".portal-free-tab-btn.is-active": ("border-color:", "background:", "color:", "box-shadow:"),
    ".portal-btn-install:hover": ("transform:", "box-shadow:", "filter:"),
    ".portal-btn-install:active": ("transform:",),
    ".portal-btn-dismiss:hover,\n.portal-btn-collapse:hover": ("background:", "color:"),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _portable_hash(path: Path) -> str:
    return sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _rule_bodies(source: str, selector: str) -> list[str]:
    pattern = rf"(?m)^[ \t]*{re.escape(selector)}\s*\{{([^{{}}]*)\}}"
    return re.findall(pattern, source)


def _slice(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index:source.index(end, start_index)]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def test_exact_eight_transition_rules_own_explicit_state_properties() -> None:
    css = _read(CSS_PATH)
    assert len(re.findall(r"(?i)transition\s*:\s*all\b", css)) == 0

    actual = {}
    for selector, expected in EXPECTED_TRANSITIONS.items():
        values = []
        for body in _rule_bodies(css, selector):
            values.extend(re.findall(r"transition\s*:\s*([^;]+);", body))
        actual[selector] = values
        assert all(value in values for value in expected), selector
        if selector == ".portal-btn-install":
            assert values == ["transform .14s ease, filter .14s ease", *expected]
        else:
            assert values == expected, selector
    assert sum(map(len, EXPECTED_TRANSITIONS.values())) == 8

    for selector, declarations in EXPECTED_STATES.items():
        bodies = _rule_bodies(css, selector)
        assert bodies, selector
        assert any(all(item in body for item in declarations) for body in bodies), selector

    layout_transition = re.compile(
        r"(?i)transition(?:-property)?\s*:[^;]*(?:\bwidth\b|\bheight\b|\btop\b|\bleft\b)"
    )
    assert layout_transition.search(css) is None


def test_shared_tokens_pending_visibility_stagger_and_six_item_cap() -> None:
    theme = _read(THEME_PATH)
    motion = _read(MOTION_PATH)
    for declaration in (
        "--portal-motion-fast: 140ms;",
        "--portal-motion-base: 220ms;",
        "--portal-motion-slow: 420ms;",
        "--portal-motion-ease-emphasis: cubic-bezier(.16,1,.3,1);",
    ):
        assert declaration in theme

    for family in ("workspace", "dashboard"):
        pending = _rule_bodies(
            theme,
            f'.portal-shell[data-portal-app-kind="customer"] .portal-{family}-motion-target.is-pending',
        )
        assert pending and "opacity: 1;" in pending[0]
        assert f"calc(var(--portal-{family}-motion-index, 0) * 34ms)" in theme

    mount_workspace = _slice(motion, "  function mountWorkspace(root)", "\n\n  window.TOANAASPortalMotion")
    slice_limits = [int(value) for value in re.findall(r"\.slice\(0,\s*(\d+)\)", mount_workspace)]
    assert slice_limits == [6]
    assert max(slice_limits) <= 6


def test_same_route_data_hydration_skips_workspace_mount_in_portal_source() -> None:
    integration = _read(INTEGRATION_PATH)
    portal = _read(PORTAL_PATH)
    mount = _slice(portal, "  function mountPortal(override)", "\n\n  window.TOANAASPortal")
    assert 'mount(window.__TOAN_AAS_PORTAL__, { reason: "data-hydration" })' in integration
    assert "const options = arguments[1] || {};" in mount
    assert 'const isHydration = options.reason === "data-hydration" && lastNormalizedRoute === actualPath;' in mount
    assert "const phase = isHydration ? \"settled\" : \"entry\";" in mount
    guard = "if (isHydration || minimalShell || isAdminPortalSurface(page) || typeof motion.mountWorkspace !== \"function\") return;"
    assert guard in mount
    assert mount.index(guard) < mount.index("motion.mountWorkspace(main);")


def test_spec_one_lifecycle_comparator_runs_independently() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_motion_webapp_lifecycle_001_contracts.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "5 passed" in output


def test_fine_and_coarse_pointer_feedback_is_bounded() -> None:
    theme = _read(THEME_PATH)
    workspace = _slice(theme, "/* Customer workspace reveal", "/* Delivery receipt keyframes")
    dashboard = _slice(theme, "/* Customer dashboard decision motion", "/* Auth Motion Contract")
    for surface in (workspace, dashboard):
        assert "@media (hover: hover) and (pointer: fine)" in surface
        assert "transform: translateY(-1px);" in surface
        assert "@media (hover: none), (pointer: coarse)" in surface
        assert "transform: scale(.985);" in surface
        assert "translateY(-2px)" not in surface


def test_reduced_motion_disables_presentation_and_keeps_content_visible() -> None:
    theme = _read(THEME_PATH)
    workspace = _slice(theme, "/* Customer workspace reveal", "/* Delivery receipt keyframes")
    dashboard = _slice(theme, "/* Customer dashboard decision motion", "/* Auth Motion Contract")
    for surface in (workspace, dashboard):
        reduced = surface.split("@media (prefers-reduced-motion: reduce)", 1)[1]
        assert "animation: none !important;" in reduced
        assert "transition: none !important;" in reduced
        assert "transform: none !important;" in reduced
        hidden_content = re.search(
            r"portal-(?:workspace|dashboard)-motion-(?:target|item)[^{]*\{[^}]*opacity\s*:\s*0(?:[;}]|\s)",
            surface,
        )
        assert hidden_content is None


def test_admin_is_stationary_and_semantically_visible() -> None:
    theme = _read(THEME_PATH)
    selector = (
        '.portal-shell[data-portal-app-kind="admin"] .portal-main,\n'
        '.portal-shell[data-portal-app-kind="admin"] .portal-page,\n'
        '.portal-shell[data-portal-app-kind="admin"] .portal-page.portal-admin-home > *'
    )
    bodies = _rule_bodies(theme, selector)
    assert bodies
    assert any(
        all(value in body for value in ("opacity: 1;", "transform: none;", "animation: none;"))
        for body in bodies
    )


def test_command_palette_keeps_concrete_dialog_focus_and_close_paths() -> None:
    portal = _read(PORTAL_PATH)
    theme = _read(THEME_PATH)
    command_markup = _slice(portal, "  function renderCommandPalette", "\n\n  function renderSidebar")
    interactions = _slice(portal, "  function bindInteractions", "\n\n  function bindVideoPreviewPlayer")

    assert 'class="portal-command-dialog" role="dialog" aria-modal="true"' in command_markup
    assert 'class="portal-command-palette-backdrop" data-portal-command-close' in command_markup
    assert 'class="portal-command-close"' in command_markup and "data-portal-command-close" in command_markup
    assert 'if (event.target.closest("[data-portal-command-close]")) { closeCommandPalette(); return; }' in interactions
    assert 'if (event.key === "Escape" && paletteOpen)' in interactions
    assert 'if (event.key === "Tab" && paletteOpen)' in interactions
    assert "const focusables = commandPaletteFocusables(palette);" in interactions
    assert "document.activeElement === first" in interactions and "last.focus();" in interactions
    assert "document.activeElement === last" in interactions and "first.focus();" in interactions
    assert "animation: portal-customer-command-enter var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;" in theme


def test_install_modal_keeps_dialog_pop_and_explicit_close_paths() -> None:
    portal = _read(PORTAL_PATH)
    theme = _read(THEME_PATH)
    motion = _read(MOTION_PATH)
    install = _slice(portal, "  function openUniversalInstallGuideModal", "\n\n  function openIosInstallGuideModal")
    interactions = _slice(portal, "  function bindInteractions", "\n\n  function bindVideoPreviewPlayer")

    assert 'class="portal-modal-card portal-install-guide-modal" role="dialog" aria-modal="true"' in install
    assert install.count('data-portal-action="modal-close"') >= 2
    assert 'event.target.closest(\'[data-portal-action="modal-close"]\')' in interactions
    assert "closeInstallGuideModal();" in interactions
    assert 'motion.enter(card, "pop")' in install
    assert "@keyframes portal-motion-pop" in theme
    assert 'animation: portal-motion-pop var(--portal-motion-fast)' in theme
    enter = _slice(motion, "  function enter(element, kind)", "\n\n  function replace")
    assert "if (!element || prefersReducedMotion())" in enter
    assert 'element.setAttribute("data-portal-motion", kind === "pop" ? "pop" : "enter")' in enter


def test_install_modal_backdrop_maps_to_its_close_handler() -> None:
    portal = _read(PORTAL_PATH)
    install = _slice(portal, "  function openUniversalInstallGuideModal", "\n\n  function openIosInstallGuideModal")
    interactions = _slice(portal, "  function bindInteractions", "\n\n  function bindVideoPreviewPlayer")
    assert 'modal.setAttribute("data-portal-modal-backdrop", "true")' in install
    assert 'event.target.matches("[data-portal-modal-backdrop]")' in interactions


def test_install_modal_maps_tab_focus_trap_and_escape_handlers() -> None:
    portal = _read(PORTAL_PATH)
    install = _slice(portal, "  function openUniversalInstallGuideModal", "\n\n  function openIosInstallGuideModal")
    close = _slice(portal, "  function closeInstallGuideModal", "\n\n  function openUniversalInstallGuideModal")
    interactions = _slice(portal, "  function bindInteractions", "\n\n  function bindVideoPreviewPlayer")
    assert "let installModalReturnFocus = null;" in portal
    assert "installModalReturnFocus = document.activeElement;" in install
    assert "const firstControl = installModalFocusables(modal)[0];" in install
    assert "firstControl.focus({ preventScroll: true });" in install
    assert "function closeInstallGuideModal(options)" in portal
    assert "returnFocus.focus({ preventScroll: true });" in close
    assert "function installModalFocusables(modal)" in portal
    assert "element.offsetParent !== null" in portal
    assert "const focusables = installModalFocusables(installModal);" in interactions
    assert 'event.key === "Escape" && installModalOpen' in interactions
    assert 'event.key === "Tab" && installModalOpen' in interactions


def test_install_modal_resolves_live_equivalent_when_saved_trigger_is_detached() -> None:
    portal = _read(PORTAL_PATH)
    close = _slice(portal, "  function closeInstallGuideModal", "\n\n  function openUniversalInstallGuideModal")
    harness = '''let focused=[],selectors=[],installModalReturnFocus={isConnected:false,focus(){focused.push("stale")}};const live={isConnected:true,focus(){focused.push("live")}},modal={remove(){}},document={querySelector(s){if(s.includes("data-portal-ios-modal"))return modal;selectors.push(s);return s==="[data-portal-pwa-fab]"?live:null;}};eval(process.argv[1]+"\\ncloseInstallGuideModal();");process.stdout.write(JSON.stringify({focused,selectors,staleConnected:false}));'''
    result = subprocess.run(["node", "-e", harness, close], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"focused": ["live"], "selectors": ["[data-portal-install-app]:not([hidden])", '[data-portal-action="pwa-install-prompt"]', '[data-portal-action="pwa-install-ios-guide"]', "[data-portal-pwa-fab]"], "staleConnected": False}


def test_scope_hash_line_and_debug_contracts() -> None:
    assert _git("merge-base", "--is-ancestor", BASE_SHA, "HEAD") == ""
    for relative_path, expected_hash in PROTECTED_HASHES.items():
        digest = _portable_hash(ROOT / relative_path)
        assert digest == expected_hash, relative_path
    portal_digest = _portable_hash(PORTAL_PATH)
    assert portal_digest == PORTAL_AMENDED_HASH
    assert portal_digest != PORTAL_PRE_AMENDMENT_HASH

    assert ".portal-body--features .portal-header { min-height: 67px; }" in _read(CSS_PATH)
    assert len(_read(CSS_PATH).splitlines()) == 9148
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
    css_numstat = _git("diff", "--numstat", BASE_SHA, "--", "static/portal/portal.css")
    assert css_numstat in ("", "9\t9\tstatic/portal/portal.css")

    debug_names = re.compile(r"^(?:test_debug|test_runner|.*motion.*debug|.*\.tmp)", re.IGNORECASE)
    unexpected = []
    for directory in (ROOT, ROOT / "tests"):
        unexpected.extend(path.name for path in directory.iterdir() if path.is_file() and debug_names.match(path.name))
    assert unexpected == []
