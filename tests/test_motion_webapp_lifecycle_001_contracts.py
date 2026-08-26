import json
import subprocess
from pathlib import Path

import pytest


BASE_SHA = "896d3761aa1126cf4bd6a6f08e2f9a9d7c51e972"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "static/portal/integration.js",
    "static/portal/portal.js",
    "static/portal/portal-motion.js",
)

NODE_HARNESS = r"""
(async () => {
  const fs = require("fs");
  const integrationCode = fs.readFileSync(process.argv[2], "utf8");
  const portalCode = fs.readFileSync(process.argv[3], "utf8");
  const motionCode = fs.readFileSync(process.argv[4], "utf8");

  let genericEnterCount = 0;
  let workspaceMountCount = 0;
  let viewTransitionCount = 0;
  let reducedMotionMatches = false;
  const hydrationReasons = [];
  const renderPhases = [];

  const makeElement = (tag) => {
    let markup = "";
    const classes = new Set();
    const el = {
      tagName: tag.toUpperCase(),
      dataset: {},
      attributes: {},
      hidden: false,
      disabled: false,
      parentElement: null,
      classList: {
        add: (...items) => items.forEach((item) => classes.add(item)),
        remove: (...items) => items.forEach((item) => classes.delete(item)),
        contains: (item) => classes.has(item),
        toggle(item, force) {
          const shouldAdd = force === undefined ? !classes.has(item) : Boolean(force);
          if (shouldAdd) classes.add(item);
          else classes.delete(item);
          return shouldAdd;
        },
      },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
        if (name === "data-portal-motion" && value === "enter") genericEnterCount += 1;
      },
      removeAttribute(name) {
        delete this.attributes[name];
      },
      getAttribute(name) {
        return Object.prototype.hasOwnProperty.call(this.attributes, name)
          ? this.attributes[name]
          : null;
      },
      addEventListener() {},
      removeEventListener() {},
      querySelectorAll() { return []; },
      querySelector() { return null; },
      appendChild(child) { child.parentElement = this; return child; },
      insertBefore(child) { child.parentElement = this; return child; },
      contains() { return false; },
      focus() {},
      style: {
        setProperty(name, value) { this[name] = String(value); },
        removeProperty(name) { delete this[name]; },
      },
    };
    Object.defineProperty(el, "innerHTML", {
      get() { return markup; },
      set(value) {
        markup = String(value);
        if (el.tagName === "MAIN") {
          renderPhases.push(el.dataset.portalPresentationPhase || null);
        }
      },
    });
    return el;
  };

  const dom = {
    main: makeElement("main"),
    shell: makeElement("div"),
    sidebar: makeElement("aside"),
    header: makeElement("header"),
    documentElement: makeElement("html"),
    body: makeElement("body"),
  };
  dom.main.parentElement = dom.shell;

  const firstPath = "/projects/11111111-1111-4111-8111-111111111111/";
  const secondPath = "/projects/22222222-2222-4222-8222-222222222222";
  global.window = {
    location: { pathname: firstPath, search: "" },
    matchMedia(query) {
      return {
        matches: query === "(prefers-reduced-motion: reduce)" && reducedMotionMatches,
        addEventListener() {},
        removeEventListener() {},
      };
    },
    setTimeout(callback) { callback(); return 1; },
    clearTimeout() {},
    setInterval() { return 1; },
    clearInterval() {},
    requestAnimationFrame(callback) { callback(); return 1; },
    cancelAnimationFrame() {},
    addEventListener() {},
    removeEventListener() {},
    __TOAN_AAS_PORTAL__: {
      path: firstPath,
      layout: "workspace",
      session: { authenticated: true },
    },
    TOANAASI18n: { t(_key, fallback) { return fallback; } },
  };

  global.document = {
    readyState: "complete",
    title: "",
    activeElement: null,
    createElement: (tag) => makeElement(tag),
    getElementById() { return null; },
    querySelectorAll() { return []; },
    querySelector(selector) {
      if (selector === "[data-portal-main]") return dom.main;
      if (selector === "[data-portal-shell]") return dom.shell;
      if (selector === "[data-portal-sidebar]") return dom.sidebar;
      if (selector === "[data-portal-header]") return dom.header;
      return null;
    },
    addEventListener() {},
    removeEventListener() {},
    documentElement: dom.documentElement,
    body: dom.body,
    startViewTransition(render) {
      viewTransitionCount += 1;
      render();
      return {
        ready: Promise.resolve(),
        finished: Promise.resolve(),
        updateCallbackDone: Promise.resolve(),
      };
    },
  };

  const flush = () => new Promise((resolve) => setImmediate(resolve));
  const visibleState = () => {
    const pending = dom.main.classList.contains("is-pending")
      || dom.shell.classList.contains("is-pending");
    const motionMarker = dom.main.getAttribute("data-portal-motion");
    return {
      pending,
      motionMarker,
      contentVisible: dom.main.innerHTML.length > 0 && !pending && motionMarker === null,
      phase: dom.main.dataset.portalPresentationPhase || null,
    };
  };
  const counters = () => ({
    viewTransitions: viewTransitionCount,
    genericEnters: genericEnterCount,
    workspaceMounts: workspaceMountCount,
  });

  eval(motionCode);
  const realMotion = window.TOANAASPortalMotion;
  window.TOANAASPortalMotion = {
    ...realMotion,
    mountWorkspace(root) {
      workspaceMountCount += 1;
      return realMotion.mountWorkspace(root);
    },
  };
  eval(portalCode);
  await flush();

  const realPortal = window.TOANAASPortal;
  window.TOANAASPortal = {
    ...realPortal,
    mount(override, options) {
      hydrationReasons.push(options && options.reason ? options.reason : null);
      return realPortal.mount(override, options);
    },
  };

  const mergeStart = integrationCode.indexOf("function merge(next) {");
  const mergeEnd = integrationCode.indexOf(
    "// Keep the Web-native Support Desk helpers",
    mergeStart,
  );
  if (mergeStart < 0 || mergeEnd < 0) throw new Error("merge() source boundary missing");
  const base = () => window.__TOAN_AAS_PORTAL__;
  let promptStudioComposeLockRoute = "";
  function setPromptStudioComposeFormLocked() {}
  eval(integrationCode.slice(mergeStart, mergeEnd));

  merge({ hydration: 1 });
  merge({ hydration: 2 });
  await flush();
  const sameRoute = { ...counters(), ...visibleState(), renderPhases: [...renderPhases] };

  window.location.pathname = secondPath;
  merge({ path: secondPath, hydration: 3 });
  await flush();
  const differentDynamicPath = {
    ...counters(),
    ...visibleState(),
    renderPhases: [...renderPhases],
  };

  reducedMotionMatches = true;
  const beforeReduced = counters();
  window.location.pathname = "/voice";
  realPortal.mount({
    ...window.__TOAN_AAS_PORTAL__,
    path: "/voice",
  });
  await flush();
  const afterReduced = counters();
  const reducedMotion = {
    viewTransitions: afterReduced.viewTransitions - beforeReduced.viewTransitions,
    genericEnters: afterReduced.genericEnters - beforeReduced.genericEnters,
    ...visibleState(),
  };

  console.log(JSON.stringify({
    hydrationReasons,
    sameRoute,
    differentDynamicPath,
    reducedMotion,
  }));
})();
"""


def _sources_at_revision(tmp_path: Path, revision: str | None) -> tuple[Path, ...]:
    if revision is None:
        return tuple(ROOT / relative for relative in SOURCE_PATHS)
    source_dir = tmp_path / revision
    source_dir.mkdir()
    paths = []
    for relative in SOURCE_PATHS:
        completed = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        target = source_dir / Path(relative).name
        target.write_text(completed.stdout, encoding="utf-8")
        paths.append(target)
    return tuple(paths)


def _run_lifecycle_harness(tmp_path: Path, revision: str | None) -> dict:
    runner = tmp_path / f"lifecycle-{revision or 'current'}.js"
    runner.write_text(NODE_HARNESS, encoding="utf-8")
    sources = _sources_at_revision(tmp_path, revision)
    completed = subprocess.run(
        ["node", str(runner), *(str(path) for path in sources)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert output_lines, "Lifecycle harness returned no counters"
    return json.loads(output_lines[-1])


@pytest.fixture(scope="module")
def lifecycle_results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    temp_dir = tmp_path_factory.mktemp("motion-webapp-lifecycle-001")
    results = {
        "baseline": _run_lifecycle_harness(temp_dir, BASE_SHA),
        "current": _run_lifecycle_harness(temp_dir, None),
    }
    print(json.dumps(results, indent=2, sort_keys=True))
    return results


def test_baseline_reproduces_hydration_replay_red(lifecycle_results: dict) -> None:
    baseline = lifecycle_results["baseline"]
    assert baseline["hydrationReasons"][:2] == [None, None]
    assert baseline["sameRoute"]["viewTransitions"] > 1
    assert baseline["sameRoute"]["workspaceMounts"] > 1


def test_same_route_hydration_settles_without_replay(lifecycle_results: dict) -> None:
    current = lifecycle_results["current"]
    same_route = current["sameRoute"]
    assert current["hydrationReasons"][:2] == ["data-hydration", "data-hydration"]
    assert same_route["viewTransitions"] == 1
    assert same_route["genericEnters"] <= 1
    assert same_route["workspaceMounts"] <= 1
    assert same_route["renderPhases"] == ["entry", "settled", "settled"]
    assert same_route["pending"] is False
    assert same_route["motionMarker"] is None
    assert same_route["contentVisible"] is True


def test_different_actual_dynamic_path_is_a_new_entry(lifecycle_results: dict) -> None:
    current = lifecycle_results["current"]
    same_route = current["sameRoute"]
    dynamic_path = current["differentDynamicPath"]
    assert current["hydrationReasons"] == ["data-hydration"] * 3
    assert dynamic_path["viewTransitions"] == same_route["viewTransitions"] + 1
    assert dynamic_path["genericEnters"] == same_route["genericEnters"] + 1
    assert dynamic_path["workspaceMounts"] == same_route["workspaceMounts"] + 1
    assert dynamic_path["renderPhases"][-1] == "entry"
    assert dynamic_path["contentVisible"] is True


def test_reduced_motion_has_no_presentation_and_keeps_content_visible(
    lifecycle_results: dict,
) -> None:
    reduced = lifecycle_results["current"]["reducedMotion"]
    assert reduced["viewTransitions"] == 0
    assert reduced["genericEnters"] == 0
    assert reduced["pending"] is False
    assert reduced["motionMarker"] is None
    assert reduced["contentVisible"] is True


def test_source_contract_preserves_mount_focus_binding_and_phase_css() -> None:
    integration = (ROOT / SOURCE_PATHS[0]).read_text(encoding="utf-8")
    portal = (ROOT / SOURCE_PATHS[1]).read_text(encoding="utf-8")
    motion = (ROOT / SOURCE_PATHS[2]).read_text(encoding="utf-8")
    css = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
    mount = portal[
        portal.index("function mountPortal(override)") :
        portal.index("\n\n  window.TOANAASPortal")
    ]
    app_motion = css[
        css.index("/* App-wide surface motion") :
        css.index("/* Always-on Feature Family Explorer")
    ]

    assert 'mount(window.__TOAN_AAS_PORTAL__, { reason: "data-hydration" })' in integration
    assert "function mountPortal(override)" in mount
    assert "const options = arguments[1] || {};" in mount
    assert "const focus = focusSnapshot();" in mount
    assert "bindInteractions();" in mount
    assert "restoreFocus(focus)" in mount
    assert "lastNormalizedRoute === actualPath" in mount
    assert "lastNormalizedRoute === page.path" not in mount
    assert mount.index("portalPresentationPhase = phase") < mount.index("main.innerHTML =")
    assert "if (isHydration || minimalShell" in mount
    assert "opts.animate === false || isHydration" in motion
    assert '[data-portal-presentation-phase="entry"]' in app_motion
    assert "@media (prefers-reduced-motion: no-preference)" in app_motion
    assert "@media (prefers-reduced-motion: reduce)" in app_motion
    assert "animation: none !important;" in app_motion
    assert "transition: none !important;" in app_motion
