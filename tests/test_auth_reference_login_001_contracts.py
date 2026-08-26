import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AUTH_SOURCE = ROOT / "static/portal/portal-auth.js"
THEME_SOURCE = ROOT / "static/portal/portal-theme.css"

NODE_HARNESS = r"""
(async () => {
  const fs = require("node:fs"), vm = require("node:vm");
  const source = fs.readFileSync(process.argv[2], "utf8");
  const listeners = {}, phaseWrites = [];
  let mainWrites = 0, primaryWrites = 0, motionMountedWrites = 0;
  let card = null, intro = null, primary = null, social = null, inputs = {};

  const classList = () => ({ add() {}, remove() {}, contains() { return false; } });
  const makeInput = (id, type) => ({ id, type, value: "" });
  const rebuildInputs = () => { inputs = {
    "portal-field-email": makeInput("portal-field-email", "email"),
    "portal-field-password": makeInput("portal-field-password", "password"),
  }; };
  const makeSocial = (markup) => ({
    markup, remove() { if (social === this) social = null; },
  });
  const makePrimary = (markup) => {
    const element = { markup };
    Object.defineProperty(element, "innerHTML", {
      get() { return element.markup; },
      set(value) {
        primaryWrites += 1;
        element.markup = String(value);
        rebuildInputs();
        document.activeElement = null;
      },
    });
    return element;
  };
  const makeCard = (markup) => {
    primary = makePrimary(markup);
    social = markup.includes("portal-direct-social-auth") ? makeSocial(markup) : null;
    return {
      querySelector(selector) {
        if (selector === ".portal-auth-primary") return primary;
        if (selector === ".portal-direct-social-auth") return social;
        return null;
      },
      replaceChild(next, previous) { if (social === previous) social = next; },
      appendChild(next) { social = next; },
    };
  };

  const attributes = {};
  const main = {
    dataset: {}, classList: classList(),
    hasAttribute(name) { return Object.hasOwn(attributes, name); },
    getAttribute(name) { return attributes[name] || null; },
    setAttribute(name, value) {
      attributes[name] = String(value);
      if (name === "data-auth-motion-phase") phaseWrites.push(String(value));
      if (name === "data-auth-motion-mounted") motionMountedWrites += 1;
    },
    querySelector(selector) {
      if (selector === ".portal-auth-card") return card;
      if (selector === ".portal-auth-intro") return intro;
      return null;
    },
  };
  Object.defineProperty(main, "innerHTML", {
    get() { return main.markup || ""; },
    set(value) {
      mainWrites += 1;
      main.markup = String(value);
      rebuildInputs();
      intro = {};
      card = makeCard(main.markup);
    },
  });

  const shell = { classList: classList() };
  const sidebar = { hidden: false }, header = { hidden: false }, mobile = { hidden: false };
  const pwaControl = { hidden: true, disabled: true, removeAttribute() {} };
  const toastRegion = { appendChild() {} };
  const bootstrap = { textContent: JSON.stringify({ path: "/login", interfaceLocale: "vi" }) };
  const document = {
    activeElement: null, visibilityState: "visible", body: { classList: classList() },
    getElementById(id) {
      if (id === "portal-bootstrap") return bootstrap;
      if (id === "portal-main") return main;
      return inputs[id] || null;
    },
    querySelector(selector) {
      const elements = {
        "[data-portal-shell]": shell,
        "[data-portal-sidebar]": sidebar,
        "[data-portal-header]": header,
        "[data-portal-mobile-nav]": mobile,
        '[data-portal-action="pwa-install-prompt"]': pwaControl,
        "[data-portal-toast]": toastRegion,
      };
      return elements[selector] || null;
    },
    createElement() {
      const element = { className: "", textContent: "", firstElementChild: null, remove() {} };
      Object.defineProperty(element, "innerHTML", { set(value) {
        const markup = String(value);
        element.firstElementChild = markup.includes("portal-direct-social-auth")
          ? makeSocial(markup) : null;
      } });
      return element;
    },
    addEventListener(type, handler) { listeners[type] = handler; },
  };

  let resolveProviders, resolveConnection;
  const providersGate = new Promise((resolve) => { resolveProviders = resolve; });
  const connectionGate = new Promise((resolve) => { resolveConnection = resolve; });
  const response = (payload, ok = true) => ({ ok, json: async () => payload });
  const fetch = (url) => {
    if (url.endsWith("/auth/providers")) return providersGate.then(() => response({
      data: { providers: { google: { enabled: true }, apple: { enabled: false } } },
    }));
    if (url.endsWith("/auth/telegram/connection/status")) {
      return connectionGate.then(() => response({ data: { ready: true } }));
    }
    if (url.endsWith("/auth/login")) return Promise.resolve(response({
      ok: true, message: "MFA", data: {
        mfa_required: true,
        challenge_id: "11111111-1111-4111-8111-111111111111",
        challenge_token: "A".repeat(32), expires_in_minutes: 5,
      },
    }));
    return Promise.resolve(response({
      ok: false, message: "No challenge",
      error_code: "TELEGRAM_LOGIN_CHALLENGE_REQUIRED",
    }, false));
  };

  class FakeFormData { entries() {
    return [["email", "owner@example.com"], ["password", "sentinel-password"]];
  } }
  const window = {
    location: { search: "", assign() {} },
    crypto: { getRandomValues(array) { return array; } },
    setTimeout() { return 1; }, clearTimeout() {}, addEventListener() {}, open() {},
    TOANAASPortalTheme: { syncControls() {} },
  };
  const context = {
    window, document, fetch, Headers, URL, URLSearchParams, FormData: FakeFormData,
    crypto: window.crypto, Uint8Array, Date, Promise, Error, JSON, Object, Array, console,
  };
  vm.createContext(context);
  vm.runInContext(source, context, { filename: "portal-auth.js" });

  const initialCard = card, initialIntro = intro, initialPrimary = primary;
  const initialEmail = inputs["portal-field-email"];
  const initialPassword = inputs["portal-field-password"];
  initialEmail.value = "email-sentinel";
  initialPassword.value = "password-sentinel";
  document.activeElement = initialEmail;

  resolveProviders();
  resolveConnection();
  const flush = () => new Promise((resolve) => setImmediate(resolve));
  for (let index = 0; index < 4; index += 1) await flush();

  const provider = {
    mainWrites, primaryWrites, motionMountedWrites,
    phase: main.getAttribute("data-auth-motion-phase"), phaseWrites: [...phaseWrites],
    motionMounted: main.getAttribute("data-auth-motion-mounted") === "true",
    cardIdentity: card === initialCard, introIdentity: intro === initialIntro,
    primaryIdentity: primary === initialPrimary,
    emailIdentity: inputs["portal-field-email"] === initialEmail,
    emailValue: initialEmail.value, passwordValue: initialPassword.value,
    focusPreserved: document.activeElement === initialEmail,
    googleReady: Boolean(social && social.markup.includes("google")),
    appleHidden: Boolean(social && !social.markup.includes("apple")),
  };

  const button = { disabled: false, setAttribute() {} };
  const passwordInput = inputs["portal-field-password"];
  const form = {
    dataset: { portalAction: "auth-login" }, reportValidity() { return true; },
    closest(selector) { return selector === "[data-portal-form]" ? form : null; },
    querySelector() { return button; }, querySelectorAll() { return [passwordInput]; },
  };
  listeners.submit({ target: form, preventDefault() {} });
  for (let index = 0; index < 4; index += 1) await flush();

  const mfa = {
    mainWrites, primaryWrites, motionMountedWrites,
    phase: main.getAttribute("data-auth-motion-phase"), phaseWrites: [...phaseWrites],
    motionMounted: main.getAttribute("data-auth-motion-mounted") === "true",
    cardIdentity: card === initialCard, introIdentity: intro === initialIntro,
    mfaVisible: primary.markup.includes('data-portal-action="auth-mfa-login"'),
    socialHidden: social === null,
  };
  console.log(JSON.stringify({ provider, mfa }));
})();
"""


@pytest.fixture(scope="module")
def auth_behavior(tmp_path_factory: pytest.TempPathFactory) -> dict:
    runner = tmp_path_factory.mktemp("auth-reference-login-001") / "auth-reference-login.js"
    runner.write_text(NODE_HARNESS, encoding="utf-8")
    completed = subprocess.run(
        ["node", str(runner), str(AUTH_SOURCE)], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    output = [line for line in completed.stdout.splitlines() if line.strip()]
    assert output, "Auth harness returned no result"
    result = json.loads(output[-1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def test_provider_hydration_preserves_primary_inputs_focus_and_identity(
    auth_behavior: dict,
) -> None:
    provider = auth_behavior["provider"]
    assert provider["mainWrites"] == 1
    assert provider["primaryWrites"] == 0
    assert provider["phaseWrites"] == ["entry", "settled"]
    assert provider["motionMountedWrites"] == 1
    assert provider["motionMounted"] is True
    assert provider["cardIdentity"] is True
    assert provider["introIdentity"] is True
    assert provider["primaryIdentity"] is True
    assert provider["emailIdentity"] is True
    assert provider["emailValue"] == "email-sentinel"
    assert provider["passwordValue"] == "password-sentinel"
    assert provider["focusPreserved"] is True


def test_provider_hydration_updates_only_social_readiness(auth_behavior: dict) -> None:
    provider = auth_behavior["provider"]
    assert provider["googleReady"] is True
    assert provider["appleHidden"] is True


def test_mfa_renders_primary_settled_without_entry_replay(auth_behavior: dict) -> None:
    mfa = auth_behavior["mfa"]
    assert mfa["mainWrites"] == 1
    assert mfa["primaryWrites"] == 1
    assert mfa["phase"] == "settled"
    assert mfa["phaseWrites"] == ["entry", "settled", "settled"]
    assert mfa["motionMountedWrites"] == 1
    assert mfa["motionMounted"] is True
    assert mfa["cardIdentity"] is True
    assert mfa["introIdentity"] is True
    assert mfa["mfaVisible"] is True
    assert mfa["socialHidden"] is True


def test_auth_entry_keeps_semantic_content_stationary_mobile_first_and_reduced_visible() -> None:
    css = THEME_SOURCE.read_text(encoding="utf-8")
    motion_start = css.index("/* Auth Motion Contract: AUTH-REFERENCE-LOGIN-001 */")
    motion_end = css.index("/* Admin Visual Hierarchy 001", motion_start)
    motion = css[motion_start:motion_end]
    assert '[data-auth-motion-mounted="true"]' in motion
    assert 'data-auth-motion-phase="entry"' not in motion
    assert all(value in motion for value in ("animation: none;", "opacity: 1;", "transform: none;"))
    assert all(value not in motion for value in ("@keyframes auth-motion", "translateY(20px)", "translateX(-20px)", "animation-delay:"))
    mobile = motion[motion.index("@media (max-width: 768px)") :]
    def rule(selector: str) -> str:
        return mobile[mobile.index(selector) : mobile.index("}", mobile.index(selector))]
    assert 'grid-template-areas: "card";' in rule(".portal-auth-page--access .portal-auth-shell")
    assert "column-reverse" not in mobile
    assert "display: none;" in rule(".portal-auth-page--access .portal-auth-intro")
    assert "flex: 0 0 36px;" in rule(".portal-auth-page--access .portal-auth-brand .portal-brand-mark")
    assert "display: none;" in rule(".portal-auth-header-actions .portal-theme-toggle-label")
    assert all(value in rule(".portal-auth-page--access .portal-auth-back") for value in ("flex-shrink: 0;", "min-width: 44px;"))
    assert "animation: none;" in mobile
    reduced = motion[motion.index("@media (prefers-reduced-motion: reduce)") :]
    for declaration in (
        "animation: none !important;", "transition: none !important;",
        "opacity: 1 !important;", "transform: none !important;",
    ):
        assert declaration in reduced
    assert "transition: all" not in motion


def test_source_and_runner_stay_bounded_and_portable() -> None:
    source = AUTH_SOURCE.read_text(encoding="utf-8")
    marker = 'main.setAttribute("data-auth-motion-mounted", "true")'
    render_source = source[source.index("  function render") : source.index("  function setBusy")]
    assert len(source.splitlines()) <= 500
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
    assert render_source.count(marker) == 1
    assert render_source.index(marker) < render_source.index("main.innerHTML =")
    assert "setTimeout" not in render_source
    assert "animationend" not in render_source
    assert "initialRender" not in source
    assert "NODE_PATH" not in NODE_HARNESS
    assert "jsdom" not in NODE_HARNESS
