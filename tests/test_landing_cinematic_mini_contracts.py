"""Static safety contracts for the public Landing Cinematic Mini.

The cinematic layer is intentionally presentation-only.  These checks protect
the public route, semantic light/dark control, reduced-motion fallback and
customer/ERP isolation without starting providers or a live application.
"""

from pathlib import Path
import json
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME_JS = (ROOT / "static" / "portal" / "portal-theme.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_cinematic_motion_is_default_only_for_welcome_with_a_safe_opt_out() -> None:
    mount = _between(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    assert 'window.location.pathname === "/welcome"' in mount
    assert 'new URLSearchParams(window.location.search || "").get("motion") !== "0"' in mount
    assert "const landingMotionRoute = isLanding" in mount
    assert "const landingMotionEnabled = landingMotionRoute" in mount
    assert "main.dataset.portalMotionSkipEnter = landingMotionRoute ? \"true\" : \"false\";" in mount
    assert 'root.setAttribute("data-landing-motion", "cinematic-mini")' in MOTION
    assert "motion.unmountLanding" in mount
    assert mount.index("motion.unmountLanding") < mount.index("function renderShell()")
    assert mount.index("motion.mountLanding") > mount.index("main.innerHTML = renderPage(page, context);")
    assert SHELL.index('src="/static/portal/portal-motion.js') < SHELL.index('src="/static/portal/portal.js')

    static_state = MOTION.index('root.setAttribute("data-landing-motion", "cinematic-mini")')
    reduced_exit = MOTION.index("if (prefersReducedMotion()) {")
    assert static_state < reduced_exit
    assert 'root.setAttribute("data-landing-motion-phase", "settled")' in MOTION


def test_landing_has_only_an_explicit_light_dark_control() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")

    assert "function renderLandingThemeSwitch()" in PORTAL
    assert 'data-portal-theme-set="light"' in PORTAL
    assert 'data-portal-theme-set="dark"' in PORTAL
    assert 'data-portal-theme-set="system"' not in PORTAL
    assert "renderLandingThemeSwitch()" in landing
    assert "${renderThemeToggle()}" not in landing

    assert 'closest("[data-portal-theme-set]")' in THEME_JS
    assert "setPreference(explicit.dataset.portalThemeSet);" in THEME_JS
    assert "classList.toggle(\"is-active\", active);" in THEME_JS
    assert 'window.location.pathname === "/welcome"' in THEME_JS


def test_cinematic_css_is_scoped_tokenized_and_reduced_motion_safe() -> None:
    assert '[data-landing-motion="cinematic-mini"]' in THEME
    assert "--portal-landing-cinematic" in THEME
    assert "landing-cinematic-hero" in THEME
    assert "landing-cinematic-preview" in THEME
    assert "landing-cinematic-step" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME

    cinematic = THEME[THEME.index('[data-landing-motion="cinematic-mini"]'):]
    for forbidden in ("will-change:", "animation-iteration-count: infinite", "scroll-timeline", "@property"):
        assert forbidden not in cinematic

    assert "clip-path: none !important;" in cinematic
    assert "opacity: 1 !important;" in cinematic
    assert "transform: none !important;" in cinematic


def test_cinematic_runtime_stays_presentation_only_and_landing_scoped() -> None:
    for forbidden in (
        r"\bfetch\s*\(",
        r"\blocalStorage\b",
        r"\bsessionStorage\b",
        r"\bXMLHttpRequest\b",
        r"\bWebSocket\b",
        r"\bEventSource\b",
        r"\btelegram\b",
        r"\bpayos\b",
        r"\bprovider\b",
    ):
        assert re.search(forbidden, MOTION, flags=re.IGNORECASE) is None

    assert ".portal-shell--workspace" not in MOTION
    assert ".portal-shell--admin" not in MOTION
    assert ".portal-shell--workspace" not in THEME[THEME.index('[data-landing-motion="cinematic-mini"]'):]
    assert ".portal-shell--admin" not in THEME[THEME.index('[data-landing-motion="cinematic-mini"]'):]


def test_landing_uses_light_only_when_no_theme_preference_is_saved() -> None:
    node = shutil.which("node")
    assert node is not None, "The project already uses Node for Portal syntax checks."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function run(pathname, stored, systemDark, storageThrows) {
  const attributes = new Map();
  const window = {
    location: { pathname },
    document: {
      readyState: "complete",
      documentElement: { style: {}, setAttribute(name, value) { attributes.set(name, String(value)); } },
      body: { setAttribute() {} },
      querySelector() { return null; },
      querySelectorAll() { return []; },
      addEventListener() {}
    },
    localStorage: {
      getItem() { if (storageThrows) throw new Error("blocked"); return stored; },
      setItem() {},
      removeItem() {}
    },
    matchMedia() { return { matches: systemDark, addEventListener() {} }; },
    addEventListener() {},
    dispatchEvent() {},
    CustomEvent: class { constructor(name, options) { this.name = name; this.detail = options.detail; } }
  };
  vm.runInNewContext(source, { window, console });
  const theme = window.TOANAASPortalTheme;
  return { preference: theme.getPreference(), resolved: theme.getResolvedTheme() };
}

console.log(JSON.stringify({
  landingMissing: run("/welcome", null, true, false),
  landingBlocked: run("/welcome", null, true, true),
  landingSavedDark: run("/welcome", "dark", false, false),
  appMissing: run("/login", null, true, false)
}));
'''
    result = subprocess.run(
        [node, "-e", harness, str(ROOT / "static" / "portal" / "portal-theme.js")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)
    assert state["landingMissing"] == {"preference": "light", "resolved": "light"}
    assert state["landingBlocked"] == {"preference": "light", "resolved": "light"}
    assert state["landingSavedDark"] == {"preference": "dark", "resolved": "dark"}
    assert state["appMissing"] == {"preference": "system", "resolved": "dark"}


def test_reduced_motion_keeps_the_static_cinematic_frame_without_scheduling_motion() -> None:
    node = shutil.which("node")
    assert node is not None, "The project already uses Node for Portal syntax checks."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classes() {
  const values = new Set();
  return { add(...items) { items.forEach((item) => values.add(item)); }, has(item) { return values.has(item); } };
}
const header = { classList: classes() };
const hero = { classList: classes() };
const steps = [{ classList: classes() }, { classList: classes() }, { classList: classes() }, { classList: classes() }];
const preview = { classList: classes(), querySelectorAll(selector) { return selector === ".portal-landing-preview-steps > span" ? steps : []; } };
const attributes = new Map();
const root = {
  setAttribute(name, value) { attributes.set(name, String(value)); },
  removeAttribute(name) { attributes.delete(name); },
  querySelector(selector) {
    if (selector === ".portal-landing-header") return header;
    if (selector === ".portal-landing-hero") return hero;
    if (selector === ".portal-landing-preview") return preview;
    return null;
  },
  querySelectorAll() { return []; }
};
const window = { matchMedia() { return { matches: true }; } };
vm.runInNewContext(source, { window, console });
window.TOANAASPortalMotion.mountLanding(root);
console.log(JSON.stringify({
  lifecycle: attributes.get("data-landing-motion"),
  header: header.classList.has("landing-motion-header"),
  hero: hero.classList.has("landing-cinematic-hero"),
  preview: preview.classList.has("landing-cinematic-preview"),
  staged: steps.every((step) => step.classList.has("landing-cinematic-step"))
}));
'''
    result = subprocess.run(
        [node, "-e", harness, str(ROOT / "static" / "portal" / "portal-motion.js")],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "lifecycle": "cinematic-mini",
        "header": True,
        "hero": True,
        "preview": True,
        "staged": True,
    }
