"""RED contracts for presentation-only customer dashboard decision motion.

The dashboard can animate how an already-rendered decision layer arrives, but
it cannot delay the summary or canonical read state, infer authority, or touch
account/provider/payment state. The lifecycle test runs the real browser asset
against a very small DOM harness rather than duplicating its selector logic.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
UX_CONTRACT = (ROOT / "docs" / "UX_APP_FIRST_REDESIGN.md").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_dashboard_motion_has_a_closed_decision_landmark_boundary() -> None:
    workspace = _section(MOTION, "function mountWorkspace(root)", "function mountLanding(root)")

    assert "const dashboardDecisionSelector = [" in workspace
    for selector in (
        '"[data-dashboard-start-guide]"',
        '".portal-dashboard-app .portal-command-center-lane--work"',
        '".portal-dashboard-app .portal-command-center-lane--account"',
        '".portal-dashboard-app .portal-studio-section"',
        '".portal-dashboard-app .portal-dashboard-assurance"',
    ):
        assert selector in workspace
    decision_source = workspace[
        workspace.index("const dashboardDecisionSelector = ["):
        workspace.index("const targetSelector = [", workspace.index("const dashboardDecisionSelector = ["))
    ]
    assert ".portal-dashboard-overview" not in decision_source
    assert ".portal-command-center-canonical" not in decision_source

    for forbidden in (
        "dashboardReadState",
        "wallet",
        "jobs",
        "assets",
        "tickets",
        "capabilities",
        "fetch(",
        "localStorage",
        "sessionStorage",
        "/api/",
        "csrf",
    ):
        assert forbidden not in decision_source


def test_dashboard_motion_has_shared_token_pointer_and_reduced_motion_rules() -> None:
    assert "@keyframes portal-dashboard-decision-reveal" in THEME
    for selector in (
        ".portal-dashboard-motion-target.is-pending",
        ".portal-dashboard-motion-target.is-visible",
        ".portal-dashboard-motion-item",
        ".portal-dashboard-app .portal-dashboard-draft",
        ".portal-dashboard-app .portal-studio-card",
    ):
        assert selector in THEME
    assert "animation: portal-dashboard-decision-reveal var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;" in THEME
    assert "animation-delay: calc(var(--portal-dashboard-motion-index, 0) * 34ms);" in THEME
    assert "transform: translateY(-1px);" in THEME
    assert "transform: scale(.985);" in THEME

    dashboard_motion = THEME[THEME.index("/* Customer dashboard decision motion"):]
    assert ".portal-dashboard-motion-target.is-visible:focus-within" in dashboard_motion
    focus_start = dashboard_motion.index(".portal-dashboard-motion-target.is-visible:focus-within")
    focus_end = dashboard_motion.index("}", focus_start)
    focus_rule = dashboard_motion[focus_start:focus_end]
    assert "opacity: 1;" in focus_rule
    assert "transform: none;" in focus_rule
    assert "animation: none;" in focus_rule

    child_focus_selector = ".portal-dashboard-motion-target.is-visible:focus-within .portal-dashboard-motion-item"
    assert child_focus_selector in dashboard_motion
    child_focus_start = dashboard_motion.index(child_focus_selector)
    child_focus_end = dashboard_motion.index("}", child_focus_start)
    child_focus_rule = dashboard_motion[child_focus_start:child_focus_end]
    assert "opacity: 1;" in child_focus_rule
    assert "transform: none;" in child_focus_rule
    assert "animation: none;" in child_focus_rule

    pointer_start = dashboard_motion.index("@media (hover: hover) and (pointer: fine)")
    pointer_end = dashboard_motion.index("@media (hover: none), (pointer: coarse)", pointer_start)
    pointer_rules = dashboard_motion[pointer_start:pointer_end]
    assert "transition: transform var(--portal-motion-fast) var(--portal-motion-ease-standard);" in pointer_rules
    for forbidden_transition in (
        "border-color var(--portal-motion-fast)",
        "background-color var(--portal-motion-fast)",
        "box-shadow var(--portal-motion-fast)",
    ):
        assert forbidden_transition not in pointer_rules

    reduced_start = THEME.rindex("@media (prefers-reduced-motion: reduce)")
    reduced = THEME[reduced_start:]
    for token in (
        ".portal-dashboard-motion-target",
        ".portal-dashboard-motion-item",
        "animation: none !important;",
        "transition: none !important;",
        "transform: none !important;",
    ):
        assert token in reduced

    assert "dashboard decision layers" in UX_CONTRACT
    assert "canonical read lane" in UX_CONTRACT


def test_dashboard_overview_is_never_delayed_by_the_legacy_surface_entrance() -> None:
    """The summary is operational context, not optional presentation content."""

    legacy_marker = "/* A regular tool/detail page gets one spatially continuous entrance."
    legacy_surface_start = THEME.index(legacy_marker)
    legacy_surface_end = THEME.index("}", legacy_surface_start)
    legacy_surface_rule = THEME[legacy_surface_start:legacy_surface_end]

    assert ".portal-dashboard-overview" not in legacy_surface_rule
    assert "portal-app-surface-enter" in legacy_surface_rule


def test_dashboard_skips_shared_main_and_document_route_entrances() -> None:
    """Operational dashboard state must not inherit generic route animation."""

    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")
    assert 'const dashboardMotionRoute = page.path === "/dashboard" && page.layout === "dashboard";' in mount
    assert 'main.dataset.portalMotionSkipEnter = landingMotionRoute || dashboardMotionRoute ? "true" : "false";' in mount

    assert 'data-portal-motion-route="__PORTAL_MOTION_ROUTE__"' in SHELL
    fallback_template = _section(PAGES, "def _fallback_template()", "\n\ndef render_portal")
    assert 'data-portal-motion-route=\\"__PORTAL_MOTION_ROUTE__\\"' in fallback_template
    assert 'motion_route = "dashboard" if normalized == "/dashboard" else "default"' in PAGES
    assert '.replace("__PORTAL_MOTION_ROUTE__", motion_route)' in PAGES

    dashboard_transition_start = THEME.index('html[data-portal-motion-route="dashboard"]::view-transition-old(root)')
    dashboard_transition_end = THEME.index("}", dashboard_transition_start)
    dashboard_transition_rule = THEME[dashboard_transition_start:dashboard_transition_end]
    assert 'html[data-portal-motion-route="dashboard"]::view-transition-new(root)' in dashboard_transition_rule
    assert "animation: none;" in dashboard_transition_rule

    dashboard_render = render_portal("/dashboard", interface_locale="en")
    default_render = render_portal("/features", interface_locale="en")
    assert re.search(r'<html[^>]*data-portal-motion-route="dashboard"', dashboard_render.body.decode("utf-8"))
    assert re.search(r'<html[^>]*data-portal-motion-route="default"', default_render.body.decode("utf-8"))


def test_dashboard_decision_motion_reveals_and_cleans_up_without_touching_canonical_content() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal dashboard motion lifecycle")
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classList() {
  const values = new Set();
  return {
    add(...names) { names.forEach((name) => values.add(name)); },
    remove(...names) { names.forEach((name) => values.delete(name)); },
    contains(name) { return values.has(name); }
  };
}

function element(items = []) {
  const listeners = new Map();
  const styles = new Map();
  return {
    classList: classList(),
    style: {
      setProperty(name, value) { styles.set(name, String(value)); },
      removeProperty(name) { styles.delete(name); },
      get(name) { return styles.get(name) || null; }
    },
    querySelectorAll(selector) {
      return selector.includes("portal-start-guide-step") || selector.includes("portal-dashboard-draft")
        || selector.includes("portal-dashboard-motion-item")
        ? items
        : [];
    },
    addEventListener(name, listener) { listeners.set(name, listener); },
    removeEventListener(name) { listeners.delete(name); },
    emit(name) {
      const listener = listeners.get(name);
      if (listener) listener({ currentTarget: this });
    },
    hasListener(name) { return listeners.has(name); }
  };
}

const guideItem = element();
const workItem = element();
const guide = element([guideItem]);
const work = element([workItem]);
const canonical = element();
const root = {
  querySelectorAll(selector) {
    if (selector.includes("data-dashboard-start-guide")) return [guide, work];
    if (selector.includes("portal-catalog-context")) return [];
    return [];
  }
};
let observer = null;
let motionListener = null;
const preference = {
  matches: false,
  addEventListener(name, listener) {
    if (name === "change") motionListener = listener;
  },
  removeEventListener(name, listener) {
    if (name === "change" && motionListener === listener) motionListener = null;
  },
  emit(matches) {
    this.matches = matches;
    if (motionListener) motionListener({ matches });
  }
};
const window = {
  matchMedia() { return preference; },
  IntersectionObserver: class {
    constructor(callback) { this.callback = callback; this.observed = []; this.disconnected = false; observer = this; }
    observe(target) { this.observed.push(target); }
    unobserve(target) { this.observed = this.observed.filter((entry) => entry !== target); }
    disconnect() { this.disconnected = true; }
  }
};
vm.runInNewContext(source, { window, console });
window.TOANAASPortalMotion.mountWorkspace(root);
observer.callback([{ target: guide, isIntersecting: true }]);
work.emit("focusin");
const beforePreferenceChange = {
  observedCount: observer.observed.length,
  guideVisible: guide.classList.contains("is-visible"),
  workVisible: work.classList.contains("is-visible"),
  guideDashboardClass: guide.classList.contains("portal-dashboard-motion-target"),
  guideItemIndex: guideItem.style.get("--portal-dashboard-motion-index"),
  canonicalDashboardClass: canonical.classList.contains("portal-dashboard-motion-target"),
  canonicalPending: canonical.classList.contains("is-pending"),
  preferenceBound: Boolean(motionListener)
};
preference.emit(true);
process.stdout.write(JSON.stringify({
  beforePreferenceChange,
  afterPreferenceChange: {
    observerDisconnected: observer.disconnected,
    guideDashboardClass: guide.classList.contains("portal-dashboard-motion-target"),
    guideWorkspaceClass: guide.classList.contains("portal-workspace-motion-target"),
    guideItemClass: guideItem.classList.contains("portal-dashboard-motion-item"),
    guideItemIndex: guideItem.style.get("--portal-dashboard-motion-index"),
    guideFocusBound: guide.hasListener("focusin"),
    preferenceBound: Boolean(motionListener),
    canonicalDashboardClass: canonical.classList.contains("portal-dashboard-motion-target"),
    canonicalPending: canonical.classList.contains("is-pending")
  }
}));
'''
    result = subprocess.run(
        [node, "-e", harness, str(ROOT / "static" / "portal" / "portal-motion.js")],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout) == {
        "beforePreferenceChange": {
            "observedCount": 0,
            "guideVisible": True,
            "workVisible": True,
            "guideDashboardClass": True,
            "guideItemIndex": "0",
            "canonicalDashboardClass": False,
            "canonicalPending": False,
            "preferenceBound": True,
        },
        "afterPreferenceChange": {
            "observerDisconnected": True,
            "guideDashboardClass": False,
            "guideWorkspaceClass": False,
            "guideItemClass": False,
            "guideItemIndex": None,
            "guideFocusBound": False,
            "preferenceBound": False,
            "canonicalDashboardClass": False,
            "canonicalPending": False,
        },
    }


def test_dashboard_decision_motion_falls_back_visible_and_cleans_first_mount_on_remount() -> None:
    """No observer and a subsequent Portal mount must leave no stale motion.

    The first root simulates a browser without IntersectionObserver. The next
    mount replaces it with a different dashboard root, proving the helper does
    not leave listener, class, inline-index or observer ownership behind.
    """

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal dashboard motion lifecycle")
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classList() {
  const values = new Set();
  return {
    add(...names) { names.forEach((name) => values.add(name)); },
    remove(...names) { names.forEach((name) => values.delete(name)); },
    contains(name) { return values.has(name); }
  };
}

function element(items = []) {
  const listeners = new Map();
  const styles = new Map();
  return {
    classList: classList(),
    style: {
      setProperty(name, value) { styles.set(name, String(value)); },
      removeProperty(name) { styles.delete(name); },
      get(name) { return styles.get(name) || null; }
    },
    querySelectorAll(selector) {
      return selector.includes("portal-start-guide-step") || selector.includes("portal-dashboard-draft")
        || selector.includes("portal-dashboard-motion-item")
        ? items
        : [];
    },
    addEventListener(name, listener) { listeners.set(name, listener); },
    removeEventListener(name) { listeners.delete(name); },
    hasListener(name) { return listeners.has(name); }
  };
}

function dashboardRoot(target) {
  return {
    querySelectorAll(selector) {
      if (selector.includes("data-dashboard-start-guide")) return [target];
      if (selector.includes("portal-catalog-context")) return [];
      return [];
    }
  };
}

const firstItem = element();
const firstTarget = element([firstItem]);
const secondItem = element();
const secondTarget = element([secondItem]);
let motionListener = null;
const preference = {
  matches: false,
  addEventListener(name, listener) { if (name === "change") motionListener = listener; },
  removeEventListener(name, listener) { if (name === "change" && motionListener === listener) motionListener = null; }
};
const window = { matchMedia() { return preference; } };
vm.runInNewContext(source, { window, console });
const motion = window.TOANAASPortalMotion;
motion.mountWorkspace(dashboardRoot(firstTarget));
const fallback = {
  targetVisible: firstTarget.classList.contains("is-visible"),
  targetPending: firstTarget.classList.contains("is-pending"),
  targetClass: firstTarget.classList.contains("portal-dashboard-motion-target"),
  itemIndex: firstItem.style.get("--portal-dashboard-motion-index"),
  focusBound: firstTarget.hasListener("focusin")
};
motion.mountWorkspace(dashboardRoot(secondTarget));
process.stdout.write(JSON.stringify({
  fallback,
  afterRemount: {
    firstTargetClass: firstTarget.classList.contains("portal-dashboard-motion-target"),
    firstPending: firstTarget.classList.contains("is-pending"),
    firstVisible: firstTarget.classList.contains("is-visible"),
    firstItemClass: firstItem.classList.contains("portal-dashboard-motion-item"),
    firstItemIndex: firstItem.style.get("--portal-dashboard-motion-index"),
    firstFocusBound: firstTarget.hasListener("focusin"),
    secondTargetClass: secondTarget.classList.contains("portal-dashboard-motion-target"),
    secondVisible: secondTarget.classList.contains("is-visible"),
    secondItemIndex: secondItem.style.get("--portal-dashboard-motion-index"),
    preferenceBound: Boolean(motionListener)
  }
}));
'''
    result = subprocess.run(
        [node, "-e", harness, str(ROOT / "static" / "portal" / "portal-motion.js")],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout) == {
        "fallback": {
            "targetVisible": True,
            "targetPending": False,
            "targetClass": True,
            "itemIndex": "0",
            "focusBound": True,
        },
        "afterRemount": {
            "firstTargetClass": False,
            "firstPending": False,
            "firstVisible": False,
            "firstItemClass": False,
            "firstItemIndex": None,
            "firstFocusBound": False,
            "secondTargetClass": True,
            "secondVisible": True,
            "secondItemIndex": "0",
            "preferenceBound": True,
        },
    }
