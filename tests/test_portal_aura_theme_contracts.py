"""Presentation-only contracts for the Aura light/dark theme layer."""

import json
from pathlib import Path
import re
import shutil
import subprocess

import copyfast_pages


ROOT = Path(__file__).resolve().parents[1]
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
THEME_JS_PATH = ROOT / "static" / "portal" / "portal-theme.js"
THEME_JS = THEME_JS_PATH.read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "webapp-quality.yml").read_text(encoding="utf-8")
MASTER_DESIGN_SYSTEM = (ROOT / "design-system" / "toan-aas-web-app" / "MASTER.md").read_text(
    encoding="utf-8"
)


def test_theme_asset_is_versioned_in_the_server_shell_and_pwa_allowlist() -> None:
    page = copyfast_pages.render_portal("/welcome", interface_locale="en")
    html = page.body.decode("utf-8")

    assert 'src="/static/portal/portal-theme.js?v=' in html
    assert "portal-theme.js" in copyfast_pages._PORTAL_BUILD_SOURCE_FILES
    assert '"/static/portal/portal-theme.js",' in WORKER
    assert 'src="/static/portal/portal-theme.js?v=__PORTAL_ASSET_VERSION__"' in SHELL
    assert "portal-theme.js" in PAGES


def test_theme_controller_is_local_presentation_state_only() -> None:
    assert 'const STORAGE_KEY = "toan-aas-portal-theme";' in THEME_JS
    assert 'const THEMES = Object.freeze(["system", "light", "dark"]);' in THEME_JS
    assert 'documentElement.setAttribute("data-portal-theme", resolved);' in THEME_JS
    assert 'global.document.body.setAttribute("data-portal-theme", resolved);' in THEME_JS
    assert 'new global.CustomEvent("toanaas:theme-change"' in THEME_JS
    assert "fetch(" not in THEME_JS
    assert "XMLHttpRequest" not in THEME_JS
    assert "/api/" not in THEME_JS
    assert "telegram" not in THEME_JS.lower()
    assert "payos" not in THEME_JS.lower()
    assert "provider" not in THEME_JS.lower()


def test_theme_controller_does_not_observe_its_own_icon_rendering() -> None:
    """Portal mount explicitly syncs controls, avoiding a mutation feedback loop."""
    assert "new global.MutationObserver" not in THEME_JS
    assert "observer.observe(" not in THEME_JS


def test_theme_toggle_is_shared_by_workspace_access_and_public_companion() -> None:
    assert "function renderThemeToggle()" in PORTAL
    assert PORTAL.count("${renderThemeToggle()}") == 3
    assert "data-portal-theme-toggle" in PORTAL
    assert "theme.syncControls()" in PORTAL
    assert 'class="portal-auth-header-actions"' in PORTAL
    assert 'class="portal-landing-nav-actions"' in PORTAL


def test_all_reviewed_interface_locales_have_theme_copy() -> None:
    for key in (
        "chrome.theme_switch",
        "chrome.theme_label",
        "chrome.theme_light",
        "chrome.theme_dark",
        "chrome.theme_system",
        "chrome.theme_switch_to_light",
        "chrome.theme_switch_to_dark",
        "chrome.theme_switch_to_system",
    ):
        assert I18N.count(f'"{key}"') == 3


def test_aura_tokens_use_requested_slate_dark_pair_and_accessible_controls() -> None:
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    dark_theme = re.search(
        r':root\[data-portal-theme="dark"\]\s*\{(?P<declarations>.*?)\n\}',
        THEME,
        flags=re.DOTALL,
    )

    assert root is not None
    assert dark_theme is not None
    assert "--portal-dark-app-canvas: #0b132b;" in root.group("declarations")
    assert "--portal-dark-surface-light: #1c2541;" in root.group("declarations")
    assert "--portal-dark-action: #14b8a6;" in root.group("declarations")
    assert "--portal-dark-context: #38bdf8;" in root.group("declarations")
    assert "--portal-app-canvas: var(--portal-dark-app-canvas);" in dark_theme.group("declarations")
    assert "--portal-surface-light: var(--portal-dark-surface-light);" in dark_theme.group("declarations")
    assert "--portal-action: var(--portal-dark-action);" in dark_theme.group("declarations")
    assert "--portal-context: var(--portal-dark-context);" in dark_theme.group("declarations")
    assert ".portal-theme-toggle" in THEME
    assert "min-width: 44px;" in THEME
    assert "min-height: var(--portal-control-height);" in THEME
    assert ".portal-theme-toggle:focus-visible" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    assert "transition-duration: 0ms !important;" in THEME


def test_compact_landing_header_preserves_locale_and_theme_without_clipping_cta() -> None:
    assert "@media (max-width: 420px)" in THEME
    assert ".portal-landing-nav-primary { display: none; }" in THEME


def test_theme_cycle_uses_its_explicit_mode_label_instead_of_binary_pressed_state() -> None:
    assert 'data-portal-theme-toggle aria-pressed' not in PORTAL
    assert 'setAttribute("aria-pressed"' not in THEME_JS
    assert "control.dataset.portalThemePreference = preference;" in THEME_JS
    assert "control.dataset.portalThemeResolved = resolved;" in THEME_JS


def test_design_system_documents_the_real_three_state_theme_control() -> None:
    assert "system → light → dark → system" in MASTER_DESIGN_SYSTEM
    assert "current and next mode" in MASTER_DESIGN_SYSTEM
    assert "does not use binary `aria-pressed`" in MASTER_DESIGN_SYSTEM


def test_auth_and_public_surfaces_inherit_the_resolved_color_scheme() -> None:
    auth = re.search(
        r"\.portal-body--auth,\s*\.portal-shell--auth\s*\{(?P<declarations>.*?)\n\}",
        THEME,
        flags=re.DOTALL,
    )
    landing = re.search(
        r"\.portal-body--landing,\s*\.portal-shell--landing,\s*\.portal-landing\s*\{"
        r"(?P<declarations>.*?)\n\}",
        THEME,
        flags=re.DOTALL,
    )

    assert auth is not None
    assert landing is not None
    assert "color-scheme: inherit;" in auth.group("declarations")
    assert "color-scheme: inherit;" in landing.group("declarations")


def test_compact_headers_keep_the_brand_visible_while_secondary_controls_compact() -> None:
    assert "@media (max-width: 1180px) and (min-width: 701px)" in THEME
    assert ".portal-header-actions .portal-theme-toggle-label { display: none; }" in THEME
    assert "@media (max-width: 390px)" in THEME
    assert "grid-template-columns: minmax(0, 1fr) auto;" in THEME
    assert "grid-column: 1 / -1;" in THEME
    assert "clip-path: inset(50%);" not in THEME


def test_theme_cycle_visits_every_explicit_preference_for_both_system_modes() -> None:
    node = shutil.which("node")
    assert node is not None, "The CI workflow already requires Node for portal syntax checks."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function run(systemDark) {
  const rootAttributes = new Map();
  const bodyAttributes = new Map();
  const icon = { innerHTML: "" };
  const label = { textContent: "" };
  const controlAttributes = new Map();
  const control = {
    dataset: {},
    querySelector(selector) {
      if (selector === "[data-portal-theme-icon]") return icon;
      if (selector === "[data-portal-theme-label]") return label;
      return null;
    },
    setAttribute(name, value) { controlAttributes.set(name, String(value)); },
    getAttribute(name) { return controlAttributes.get(name) || null; }
  };
  const document = {
    readyState: "complete",
    documentElement: {
      style: {},
      setAttribute(name, value) { rootAttributes.set(name, String(value)); },
      getAttribute(name) { return rootAttributes.get(name) || null; }
    },
    body: { setAttribute(name, value) { bodyAttributes.set(name, String(value)); } },
    querySelector() { return null; },
    querySelectorAll(selector) { return selector === "[data-portal-theme-toggle]" ? [control] : []; },
    addEventListener() {}
  };
  const storage = new Map();
  const window = {
    document,
    localStorage: {
      getItem(key) { return storage.has(key) ? storage.get(key) : null; },
      setItem(key, value) { storage.set(key, String(value)); },
      removeItem(key) { storage.delete(key); }
    },
    matchMedia() { return { matches: systemDark, addEventListener() {} }; },
    addEventListener() {},
    dispatchEvent() {},
    CustomEvent: class { constructor(name, options) { this.name = name; this.detail = options.detail; } }
  };
  vm.runInNewContext(source, { window, console });
  const theme = window.TOANAASPortalTheme;
  const sequence = [theme.getPreference()];
  theme.toggle(); sequence.push(theme.getPreference());
  theme.toggle(); sequence.push(theme.getPreference());
  theme.toggle(); sequence.push(theme.getPreference());
  return { sequence, label: control.getAttribute("aria-label"), ariaPressed: control.getAttribute("aria-pressed") };
}

console.log(JSON.stringify([run(false), run(true)]));
'''
    result = subprocess.run(
        [node, "-e", harness, str(THEME_JS_PATH)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    for scenario in json.loads(result.stdout):
        assert scenario["sequence"] == ["system", "light", "dark", "system"]
        assert scenario["ariaPressed"] is None
        assert "Giao diện" in scenario["label"]


def test_landing_primary_action_uses_an_aa_contrast_pair() -> None:
    root = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    landing_primary = re.search(
        r"\.portal-landing \.portal-button--primary\s*\{(?P<declarations>.*?)\n\}",
        THEME,
        flags=re.DOTALL,
    )

    assert root is not None
    assert landing_primary is not None
    assert "background: var(--portal-action);" in landing_primary.group("declarations")
    assert "color: var(--portal-on-action);" in landing_primary.group("declarations")
    assert "--portal-action: #0f766e;" in root.group("declarations")
    assert "--portal-on-action: #ffffff;" in root.group("declarations")


def test_skip_link_uses_the_aa_action_pair_instead_of_the_mint_brand_pair() -> None:
    legacy_skip_link = re.search(
        r"\.skip-link\s*\{(?P<declarations>.*?)\n\}", PORTAL_CSS, flags=re.DOTALL
    )
    theme_skip_link = re.search(
        r"\.skip-link\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL
    )

    assert legacy_skip_link is not None
    assert theme_skip_link is not None
    assert "background: var(--portal-accent);" in legacy_skip_link.group("declarations")
    assert "color: var(--portal-accent-ink);" in legacy_skip_link.group("declarations")
    assert "background: var(--portal-action);" in theme_skip_link.group("declarations")
    assert "color: var(--portal-on-action);" in theme_skip_link.group("declarations")


def test_ci_gate_checks_aura_javascript_and_contracts() -> None:
    assert "node --check static/portal/portal-theme.js" in WORKFLOW
    assert "tests/test_portal_aura_theme_contracts.py" in WORKFLOW
