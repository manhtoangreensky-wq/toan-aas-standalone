"""Contracts for the continuous, scroll-aware public landing motion layer.

The motion is presentation-only: it may read viewport/pointer state and write
CSS variables/classes, but it must not call APIs, persist browser data, or
change the route's authority/data boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess


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


def test_landing_anchor_navigation_is_smooth_only_when_motion_is_safe() -> None:
    """Public landing anchors need a header-safe, reduced-motion-safe path."""
    landing = PORTAL[
        PORTAL.index("function renderLanding(page, context)") : PORTAL.index(
            "function renderVideoFinalization", PORTAL.index("function renderLanding(page, context)")
        )
    ]
    for target in (
        "features",
        "content-workspace",
        "audio-workspace",
        "studios",
        "workflow",
    ):
        assert f'href="#{target}"' in landing

    for marker in (
        'root.setAttribute("data-landing-anchor-motion", "active")',
        'root.setAttribute("data-landing-anchor-motion", "static")',
        'root.removeAttribute("data-landing-anchor-motion")',
        '"portal-landing-anchor-motion"',
    ):
        assert marker in MOTION

    anchor_start = THEME.index("/* Landing anchor continuity")
    anchor_end = THEME.index("/*", anchor_start + len("/* Landing anchor continuity"))
    anchor_css = THEME[anchor_start:anchor_end]
    for marker in (
        "@media (prefers-reduced-motion: no-preference)",
        "html.portal-landing-anchor-motion",
        "scroll-behavior: smooth;",
        "scroll-padding-block-start: calc(var(--portal-landing-anchor-offset) + var(--portal-safe-top));",
        "[data-landing-anchor-target]",
        "scroll-margin-block-start: var(--portal-landing-anchor-gap);",
    ):
        assert marker in anchor_css
    for token in (
        "--portal-landing-anchor-offset: 80px;",
        "--portal-landing-anchor-gap: 16px;",
    ):
        assert token in THEME
    for forbidden in ("scrollIntoView", "scrollTo", "history.pushState"):
        assert forbidden not in MOTION


def _run_landing_scroll_harness() -> dict[str, object]:
    node = shutil.which("node")
    assert node is not None, "Node is required for the Portal motion runtime contract."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classList() {
  const values = new Set();
  return {
    add(...items) { items.forEach((item) => values.add(String(item))); },
    remove(...items) { items.forEach((item) => values.delete(String(item))); },
    has(item) { return values.has(String(item)); }
  };
}

function element(kind = "generic", options = {}) {
  const attributes = new Map();
  const listeners = new Map();
  const styles = new Map();
  const children = [];
  return {
    kind,
    classList: classList(),
    children,
    style: {
      setProperty(name, value) { styles.set(name, String(value)); },
      removeProperty(name) { styles.delete(name); },
      getPropertyValue(name) { return styles.get(name) || ""; }
    },
    styles,
    setAttribute(name, value) { attributes.set(name, String(value)); },
    removeAttribute(name) { attributes.delete(name); },
    getAttribute(name) { return attributes.get(name) || null; },
    hasAttribute(name) { return attributes.has(name); },
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener(name, callback) {
      if (listeners.has(name)) listeners.get(name).delete(callback);
    },
    listenerCount(name) { return listeners.has(name) ? listeners.get(name).size : 0; },
    dispatchEvent(name) {
      if (listeners.has(name)) {
        listeners.get(name).forEach((cb) => cb({ currentTarget: this }));
      }
    },
    scrollTop: options.scrollTop || 0,
    scrollHeight: options.scrollHeight || 800,
    clientHeight: options.clientHeight || 800,
    getBoundingClientRect() {
      if (typeof options.getRect === "function") return options.getRect();
      return { top: 0, bottom: 800, height: 800, width: 1200, left: 0, right: 1200 };
    },
    closest(selector) {
      if (options.closest) return options.closest(selector);
      return null;
    },
    querySelector(selector) {
      if (options.querySelector) return options.querySelector(selector);
      return null;
    },
    querySelectorAll(selector) {
      if (options.querySelectorAll) return options.querySelectorAll(selector);
      return [];
    },
    matches(selector) {
      return (selector === ".portal-landing-workflow" && kind === "workflow")
        || (selector === ".portal-landing-final" && kind === "final")
        || (selector === ".portal-landing-section" && kind === "section")
        || (selector === ".portal-landing-feature-strip" && kind === "feature-strip")
        || (selector === ".portal-landing-spotlights" && kind === "spotlights");
    }
  };
}

const scheduledFrames = [];
const window = {
  scrollY: 0,
  innerHeight: 800,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) {
    const id = scheduledFrames.length + 1;
    scheduledFrames.push({ id, callback });
    return id;
  },
  cancelAnimationFrame(id) {},
  setTimeout(callback) { return 0; },
  clearTimeout(id) {},
  addEventListener(name, callback) {
    window._listeners = window._listeners || new Map();
    if (!window._listeners.has(name)) window._listeners.set(name, new Set());
    window._listeners.get(name).add(callback);
  },
  removeEventListener(name, callback) {
    if (window._listeners && window._listeners.has(name)) window._listeners.get(name).delete(callback);
  }
};
const document = {
  documentElement: {
    scrollHeight: 3000,
    clientHeight: 800,
    classList: classList()
  }
};

vm.runInNewContext(source, { window, document, console });
const motion = window.TOANAASPortalMotion;

const workspace = element("workspace", {
  scrollHeight: 3200,
  clientHeight: 800,
  getRect: () => ({ top: 0, bottom: 800, height: 800, width: 1200, left: 0, right: 1200 })
});
workspace.scrollTop = 0;

let currentScrollTop = 0;
const header = element("header");
const hero = element("hero", {
  getRect: () => ({ top: 0 - currentScrollTop, bottom: 600 - currentScrollTop, height: 600, width: 1200 })
});
const preview = element("preview");
preview.steps = [element("step"), element("step")];

const layerHero = element("layer-hero", {
  getRect: () => ({ top: 0 - currentScrollTop, height: 600, width: 1200 })
});
layerHero.setAttribute("data-landing-layer", "hero");

const layerStudios = element("layer-studios", {
  getRect: () => ({ top: 600 - currentScrollTop, height: 800, width: 1200 })
});
layerStudios.setAttribute("data-landing-layer", "studios");

const layerWorkflow = element("layer-workflow", {
  getRect: () => ({ top: 1400 - currentScrollTop, height: 800, width: 1200 })
});
layerWorkflow.setAttribute("data-landing-layer", "workflow");

const scrollLayers = [layerHero, layerStudios, layerWorkflow];

const root = element("root", {
  closest: (selector) => (selector === ".portal-workspace" ? workspace : null),
  querySelector: (selector) => {
    if (selector === ".portal-landing-header") return header;
    if (selector === ".portal-landing-hero") return hero;
    if (selector === ".portal-landing-preview") return preview;
    return null;
  },
  querySelectorAll: (selector) => {
    if (selector === "[data-landing-layer]") return scrollLayers;
    return [];
  }
});

motion.mountLanding(root);

const windowScrollYBefore = window.scrollY;
const workspaceScrollTopBefore = workspace.scrollTop;
const scrollOwnerResolved = workspace.listenerCount("scroll") === 1 ? "PORTAL_WORKSPACE" : "WINDOW";
const progressBefore = root.getAttribute("data-landing-scroll-progress");
const sectionBefore = root.getAttribute("data-landing-motion-section");
const headerMotionStateBefore = header.getAttribute("data-landing-motion-header");

workspace.scrollTop = 1200;
currentScrollTop = 1200;
workspace.dispatchEvent("scroll");
scheduledFrames.splice(0).forEach((frame) => frame.callback());

const windowScrollYAfter = window.scrollY;
const workspaceScrollTopAfter = workspace.scrollTop;
const progressAfter = root.getAttribute("data-landing-scroll-progress");
const cssProgressAfter = root.styles.get("--landing-scroll-progress");
const sectionAfter = root.getAttribute("data-landing-motion-section");
const headerMotionStateAfter = header.getAttribute("data-landing-motion-header");

motion.unmountLanding();
const workspaceListenerCountAfterUnmount = workspace.listenerCount("scroll");

const fallbackHeader = element("fallback-header");
const fallbackRoot = element("fallback-root", {
  closest: () => null,
  querySelector: (s) => (s === ".portal-landing-header" ? fallbackHeader : null),
  querySelectorAll: () => []
});
motion.mountLanding(fallbackRoot);
const fallbackWindowListenersBefore = window._listeners && window._listeners.has("scroll") ? window._listeners.get("scroll").size : 0;
window.scrollY = 150;
if (window._listeners && window._listeners.has("scroll")) {
  window._listeners.get("scroll").forEach((cb) => cb());
}
scheduledFrames.splice(0).forEach((frame) => frame.callback());
const fallbackHeaderStateAfter = fallbackHeader.getAttribute("data-landing-motion-header");
motion.unmountLanding();
const fallbackWindowListenersAfter = window._listeners && window._listeners.has("scroll") ? window._listeners.get("scroll").size : 0;

console.log(JSON.stringify({
  windowScrollYBefore,
  windowScrollYAfter,
  workspaceScrollTopBefore,
  workspaceScrollTopAfter,
  scrollOwnerResolved,
  progressBefore,
  progressAfter: Number(progressAfter),
  cssProgressAfter: Number(cssProgressAfter),
  sectionBefore,
  sectionAfter,
  headerMotionStateBefore,
  headerMotionStateAfter,
  workspaceListenerCountAfterUnmount,
  fallbackWindowListenersBefore,
  fallbackHeaderStateAfter,
  fallbackWindowListenersAfter
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
    return json.loads(result.stdout)


def test_landing_scroll_owner_syncs_with_workspace_container_and_falls_back_safely() -> None:
    data = _run_landing_scroll_harness()
    assert data["windowScrollYBefore"] == 0
    assert data["windowScrollYAfter"] == 0
    assert data["workspaceScrollTopBefore"] == 0
    assert data["workspaceScrollTopAfter"] > 20
    assert data["scrollOwnerResolved"] == "PORTAL_WORKSPACE"
    assert data["progressBefore"] == "0"
    assert data["progressAfter"] > 0
    assert data["cssProgressAfter"] > 0
    assert data["sectionBefore"] == "hero"
    assert data["sectionAfter"] != "hero"
    assert data["headerMotionStateBefore"] == "default"
    assert data["headerMotionStateAfter"] == "compact"
    assert data["workspaceListenerCountAfterUnmount"] == 0
    assert data["fallbackWindowListenersBefore"] == 1
    assert data["fallbackHeaderStateAfter"] == "compact"
    assert data["fallbackWindowListenersAfter"] == 0
