"""Runtime contracts for safe landing motion remounts and cleanup."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")


def _run_lifecycle_harness() -> dict[str, object]:
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

function element(kind = "generic") {
  const attributes = new Map();
  const listeners = new Map();
  const children = [];
  return {
    kind,
    classList: classList(),
    children,
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
    querySelector(selector) {
      if (selector === ".portal-landing-section-heading" && this.heading) return this.heading;
      if (selector === ".portal-landing-header") return this.header || null;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === ".portal-landing-preview-steps > span") return this.steps || [];
      if (selector === ".portal-landing-hero-copy, .portal-landing-hero-actions, .portal-landing-proof, .portal-landing-preview") return this.stages || [];
      if (selector === ".portal-landing-studio, .portal-landing-workflow li, .portal-landing-trust-grid > article") return this.cards || [];
      if (selector === ".portal-button") return this.ctas || [];
      return [];
    },
    matches(selector) {
      return (selector === ".portal-landing-workflow" && kind === "workflow")
        || (selector === ".portal-landing-final" && kind === "final");
    }
  };
}

const scheduledFrames = [];
const scheduledTimers = [];
const canceledFrames = new Set();
const clearedTimers = new Set();
const observers = [];
let reduced = false;
const window = {
  scrollY: 0,
  matchMedia() { return { matches: reduced }; },
  requestAnimationFrame(callback) { const id = scheduledFrames.length + 1; scheduledFrames.push({ id, callback }); return id; },
  cancelAnimationFrame(id) { canceledFrames.add(id); },
  setTimeout(callback) { const id = scheduledTimers.length + 1; scheduledTimers.push({ id, callback }); return id; },
  clearTimeout(id) { clearedTimers.add(id); },
  addEventListener(name, callback) { window._listeners = window._listeners || new Map(); if (!window._listeners.has(name)) window._listeners.set(name, new Set()); window._listeners.get(name).add(callback); },
  removeEventListener(name, callback) { if (window._listeners && window._listeners.has(name)) window._listeners.get(name).delete(callback); }
};
window.IntersectionObserver = class {
  constructor(callback) { this.callback = callback; this.disconnected = false; observers.push(this); }
  observe(target) { this.target = target; }
  unobserve() {}
  disconnect() { this.disconnected = true; }
};

vm.runInNewContext(source, { window, console });
const motion = window.TOANAASPortalMotion;

function fixture() {
  const root = element("root");
  const header = element("header");
  const hero = element("hero");
  const preview = element("preview");
  const section = element("section");
  const final = element("final");
  const stage = element("stage");
  const card = element("card");
  const cta = element("cta");
  preview.steps = [element("step")];
  root.header = header;
  root.hero = hero;
  root.preview = preview;
  root.section = section;
  root.final = final;
  root.stages = [stage];
  root.ctas = [cta];
  section.heading = element("heading");
  section.cards = [card];
  root.querySelector = function(selector) {
    if (selector === ".portal-landing-header") return header;
    if (selector === ".portal-landing-hero") return hero;
    if (selector === ".portal-landing-preview") return preview;
    return null;
  };
  root.querySelectorAll = function(selector) {
    if (selector === ".portal-landing-section, .portal-landing-workflow, .portal-landing-trust, .portal-landing-final") return [section, final];
    if (selector === ".portal-button") return root.ctas;
    return [];
  };
  return { root, header, hero, preview, section, final, stage, card, cta };
}

function deliverStaleCallbacks() {
  scheduledFrames.splice(0).forEach((item) => item.callback());
  scheduledTimers.splice(0).forEach((item) => item.callback());
  observers.forEach((observer) => observer.callback([{ isIntersecting: true, target: observer.target }]));
}

const first = fixture();
motion.mountLanding(first.root);
const firstObserver = observers[observers.length - 1];
motion.unmountLanding();
deliverStaleCallbacks();
const stale = {
  phase: first.root.getAttribute("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready"),
  revealed: first.section.classList.has("is-visible"),
  headerListenerCount: window._listeners && window._listeners.has("scroll") ? window._listeners.get("scroll").size : 0,
  focusListenerCount: first.section.listenerCount("focusin"),
  observerDisconnected: firstObserver.disconnected,
  motionClassCleared: !first.hero.classList.has("landing-motion-hero") && !first.section.classList.has("landing-motion-reveal")
};

const second = fixture();
motion.mountLanding(second.root);
const secondFrame = scheduledFrames[scheduledFrames.length - 1];
if (secondFrame) secondFrame.callback();
const live = {
  phase: second.root.getAttribute("data-landing-motion-phase"),
  ready: second.hero.classList.has("is-ready")
};
motion.unmountLanding();

reduced = true;
const framesBeforeReduced = scheduledFrames.length;
const timersBeforeReduced = scheduledTimers.length;
const observersBeforeReduced = observers.length;
const reducedFixture = fixture();
motion.mountLanding(reducedFixture.root);
const reducedState = {
  phase: reducedFixture.root.getAttribute("data-landing-motion-phase"),
  ready: reducedFixture.hero.classList.has("is-ready"),
  scheduledFrames: scheduledFrames.length - framesBeforeReduced,
  scheduledTimers: scheduledTimers.length - timersBeforeReduced,
  observerCount: observers.length - observersBeforeReduced
};
motion.unmountLanding();
console.log(JSON.stringify({ stale, live, reduced: reducedState }));
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


def test_stale_callbacks_cannot_resurrect_or_mutate_unmounted_landing() -> None:
    state = _run_lifecycle_harness()
    assert state["stale"] == {
        "phase": None,
        "ready": False,
        "revealed": False,
        "headerListenerCount": 0,
        "focusListenerCount": 0,
        "observerDisconnected": True,
        "motionClassCleared": True,
    }


def test_live_remount_and_reduced_motion_are_bounded() -> None:
    state = _run_lifecycle_harness()
    assert state["live"] == {"phase": "intro", "ready": True}
    assert state["reduced"]["phase"] == "settled"
    assert state["reduced"]["ready"] is False
    assert state["reduced"]["scheduledFrames"] == 0
    assert state["reduced"]["scheduledTimers"] == 0
    assert state["reduced"]["observerCount"] == 0
