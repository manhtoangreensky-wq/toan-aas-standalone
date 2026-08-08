"""Contracts for the user-visible, bounded landing motion replay."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MOTION = ROOT / "static" / "portal" / "portal-motion.js"


def _run_replay_harness() -> dict[str, object]:
    node = shutil.which("node")
    assert node is not None, "Node is required for the Portal motion runtime contract."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classes() {
  const values = new Set();
  return {
    add(...items) { items.forEach((item) => values.add(String(item))); },
    remove(...items) { items.forEach((item) => values.delete(String(item))); },
    has(item) { return values.has(String(item)); }
  };
}

function element(kind) {
  const attributes = new Map();
  const listeners = new Map();
  return {
    kind,
    offsetWidth: 0,
    classList: classes(),
    setAttribute(name, value) { attributes.set(name, String(value)); },
    removeAttribute(name) { attributes.delete(name); },
    getAttribute(name) { return attributes.get(name) || null; },
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener(name, callback) {
      if (listeners.has(name)) listeners.get(name).delete(callback);
    },
    dispatch(name) {
      (listeners.get(name) || new Set()).forEach((callback) => callback({ currentTarget: this }));
    },
    listenerCount(name) { return listeners.has(name) ? listeners.get(name).size : 0; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    matches() { return false; }
  };
}

const frames = [];
const timers = [];
const canceledFrames = new Set();
const clearedTimers = new Set();
let reduced = false;
const window = {
  scrollY: 0,
  matchMedia() { return { matches: reduced }; },
  requestAnimationFrame(callback) {
    const id = frames.length + 1;
    frames.push({ id, callback });
    return id;
  },
  cancelAnimationFrame(id) { canceledFrames.add(id); },
  setTimeout(callback) {
    const id = timers.length + 1;
    timers.push({ id, callback });
    return id;
  },
  clearTimeout(id) { clearedTimers.add(id); },
  addEventListener() {},
  removeEventListener() {}
};
vm.runInNewContext(source, { window, console });
const motion = window.TOANAASPortalMotion;

function fixture() {
  const root = element("root");
  const header = element("header");
  const hero = element("hero");
  const preview = element("preview");
  const replay = element("replay");
  const steps = [element("step-1"), element("step-2"), element("step-3"), element("step-4")];
  preview.querySelectorAll = (selector) => selector === ".portal-landing-preview-steps > span" ? steps : [];
  root.querySelector = (selector) => {
    if (selector === ".portal-landing-header") return header;
    if (selector === ".portal-landing-hero") return hero;
    if (selector === ".portal-landing-preview") return preview;
    if (selector === "[data-landing-motion-replay]") return replay;
    return null;
  };
  root.querySelectorAll = (selector) => {
    if (selector === ".portal-landing-hero-copy, .portal-landing-hero-actions, .portal-landing-proof, .portal-landing-preview") return [element("stage")];
    if (selector === ".portal-button") return [replay];
    return [];
  };
  return { root, hero, replay, steps };
}

const first = fixture();
motion.mountLanding(first.root);
const firstCallbacks = { frames: frames.slice(), timers: timers.slice() };
first.frames = frames;
first.timers = timers;
// The first frame starts the real hero sequence.
frames[0].callback();
const afterInitialFrame = {
  phase: first.root.getAttribute("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready"),
  active: first.steps.map((step) => step.classList.has("landing-motion-step-active"))
};

// A user-triggered replay resets the phase and the active step.
first.replay.dispatch("click");
const afterReplayClick = {
  phase: first.root.getAttribute("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready"),
  active: first.steps.map((step) => step.classList.has("landing-motion-step-active")),
  run: first.root.getAttribute("data-landing-motion-run")
};

// Deliver callbacks from the old run after replay; generation/run guards must
// prevent them from settling or selecting a stale step.
firstCallbacks.frames.forEach((item) => item.callback());
firstCallbacks.timers.forEach((item) => item.callback());
const afterStaleDelivery = {
  phase: first.root.getAttribute("data-landing-motion-phase"),
  active: first.steps.map((step) => step.classList.has("landing-motion-step-active"))
};

motion.unmountLanding();
frames.forEach((item) => item.callback());
timers.forEach((item) => item.callback());
const afterUnmount = {
  phase: first.root.getAttribute("data-landing-motion-phase"),
  run: first.root.getAttribute("data-landing-motion-run"),
  ready: first.hero.classList.has("is-ready"),
  active: first.steps.map((step) => step.classList.has("landing-motion-step-active")),
  replayListeners: first.replay.listenerCount("click"),
  canceledFrames: canceledFrames.size > 0,
  clearedTimers: clearedTimers.size > 0
};

reduced = true;
const reducedFixture = fixture();
const frameCount = frames.length;
const timerCount = timers.length;
motion.mountLanding(reducedFixture.root);
const reducedState = {
  phase: reducedFixture.root.getAttribute("data-landing-motion-phase"),
  scheduledFrames: frames.length - frameCount,
  scheduledTimers: timers.length - timerCount,
  replayListeners: reducedFixture.replay.listenerCount("click")
};
console.log(JSON.stringify({ afterInitialFrame, afterReplayClick, afterStaleDelivery, afterUnmount, reduced: reducedState }));
'''
    result = subprocess.run(
        [node, "-e", harness, str(MOTION)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_replay_is_visible_bounded_and_stale_callbacks_are_ignored() -> None:
    state = _run_replay_harness()
    assert state["afterInitialFrame"] == {
        "phase": "intro",
        "ready": True,
        "active": [True, False, False, False],
    }
    assert state["afterReplayClick"]["phase"] == "intro"
    assert state["afterReplayClick"]["ready"] is False
    assert state["afterReplayClick"]["active"] == [True, False, False, False]
    assert state["afterReplayClick"]["run"] == "2"
    assert state["afterStaleDelivery"] == {
        "phase": "intro",
        "active": [True, False, False, False],
    }
    assert state["afterUnmount"] == {
        "phase": None,
        "run": None,
        "ready": False,
        "active": [False, False, False, False],
        "replayListeners": 0,
        "canceledFrames": True,
        "clearedTimers": True,
    }
    assert state["reduced"] == {
        "phase": "settled",
        "scheduledFrames": 0,
        "scheduledTimers": 0,
        "replayListeners": 0,
    }


def test_replay_control_and_bounded_timing_are_checked_in() -> None:
    source = MOTION.read_text(encoding="utf-8")
    assert 'root.querySelector("[data-landing-motion-replay]")' in source
    assert "LANDING_PREVIEW_STEP_START_DELAY_MS" in source
    assert "LANDING_PREVIEW_STEP_INTERVAL_MS" in source
    assert "landing-motion-step-active" in source
