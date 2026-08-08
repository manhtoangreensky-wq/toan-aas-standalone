"""Regression contracts for a visibly replayable public Landing sequence."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _run_motion_harness() -> dict[str, object]:
    node = shutil.which("node")
    assert node is not None, "The project already uses Node for Portal syntax checks."
    harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");

function classes() {
  const values = new Set();
  return {
    add(...items) { items.forEach((item) => values.add(item)); },
    remove(...items) { items.forEach((item) => values.delete(item)); },
    has(item) { return values.has(item); }
  };
}
function rootFixture() {
  const attributes = new Map();
  const header = { classList: classes(), setAttribute() {}, removeAttribute() {} };
  const hero = { classList: classes() };
  const previewSteps = Array.from({ length: 4 }, () => ({ classList: classes() }));
  const preview = {
    classList: classes(),
    querySelectorAll(selector) {
      return selector === ".portal-landing-preview-steps > span" ? previewSteps : [];
    }
  };
  return {
    attributes,
    hero,
    previewSteps,
    root: {
      setAttribute(name, value) { attributes.set(name, String(value)); },
      removeAttribute(name) { attributes.delete(name); },
      querySelector(selector) {
        if (selector === ".portal-landing-header") return header;
        if (selector === ".portal-landing-hero") return hero;
        if (selector === ".portal-landing-preview") return preview;
        return null;
      },
      querySelectorAll() { return []; }
    }
  };
}
const frames = [];
const timers = [];
let frameRequests = 0;
const window = {
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { frameRequests += 1; frames.push(callback); return frameRequests; },
  cancelAnimationFrame() {},
  setTimeout(callback) { timers.push(callback); return timers.length; },
  clearTimeout() {},
  addEventListener() {},
  removeEventListener() {}
};
vm.runInNewContext(source, { window, console });
const motion = window.TOANAASPortalMotion;
const first = rootFixture();
motion.mountLanding(first.root);
const firstBeforeFrame = {
  phase: first.attributes.get("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready")
};
const firstPaintFrame = frames.shift();
if (typeof firstPaintFrame === "function") firstPaintFrame();
const firstAfterPaintFrame = {
  phase: first.attributes.get("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready")
};
const firstActivationFrame = frames.shift();
if (typeof firstActivationFrame === "function") firstActivationFrame();
const firstPlaybackState = {
  phase: first.attributes.get("data-landing-motion-phase"),
  playback: first.attributes.get("data-landing-motion-playback"),
  active: first.previewSteps.map((step) => step.classList.has("is-active"))
};
timers.splice(0).forEach((callback) => callback());
const firstState = {
  phase: first.attributes.get("data-landing-motion-phase"),
  ready: first.hero.classList.has("is-ready")
};
motion.unmountLanding();
const second = rootFixture();
motion.mountLanding(second.root);
const secondBeforeFrame = {
  phase: second.attributes.get("data-landing-motion-phase"),
  ready: second.hero.classList.has("is-ready")
};
const secondPaintFrame = frames.shift();
if (typeof secondPaintFrame === "function") secondPaintFrame();
const secondAfterPaintFrame = {
  phase: second.attributes.get("data-landing-motion-phase"),
  ready: second.hero.classList.has("is-ready")
};
const secondActivationFrame = frames.shift();
if (typeof secondActivationFrame === "function") secondActivationFrame();
const secondPlaybackState = {
  phase: second.attributes.get("data-landing-motion-phase"),
  playback: second.attributes.get("data-landing-motion-playback"),
  active: second.previewSteps.map((step) => step.classList.has("is-active"))
};
timers.splice(0).forEach((callback) => callback());
const secondState = {
  phase: second.attributes.get("data-landing-motion-phase"),
  ready: second.hero.classList.has("is-ready")
};
console.log(JSON.stringify({
  first: firstState,
  first_before_frame: firstBeforeFrame,
  first_after_paint_frame: firstAfterPaintFrame,
  first_playback: firstPlaybackState,
  second_before_frame: secondBeforeFrame,
  second_after_paint_frame: secondAfterPaintFrame,
  second_playback: secondPlaybackState,
  second: secondState,
  frame_requests: frameRequests
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


def test_landing_intro_replays_on_each_mount_and_has_a_real_lifecycle() -> None:
    state = _run_motion_harness()

    assert state["first_before_frame"] == {"phase": "intro", "ready": False}
    assert state["first_after_paint_frame"] == {"phase": "intro", "ready": False}
    assert state["first"] == {"phase": "settled", "ready": True}
    assert state["first_playback"] == {"phase": "intro", "playback": "active", "active": [True, False, False, False]}
    assert state["second_before_frame"] == {"phase": "intro", "ready": False}
    assert state["second_after_paint_frame"] == {"phase": "intro", "ready": False}
    assert state["second"] == {"phase": "settled", "ready": True}
    assert state["second_playback"] == {"phase": "intro", "playback": "active", "active": [True, False, False, False]}
    assert state["frame_requests"] == 4
    assert "landingHeroHasEntered" not in MOTION


def test_visible_sequence_stays_landing_scoped_and_reduced_motion_safe() -> None:
    assert "const LANDING_SEQUENCE_SETTLE_DELAY_MS = 7600;" in MOTION
    assert "const LANDING_HERO_KICKOFF_FALLBACK_MS = 160;" in MOTION
    assert "const LANDING_PREVIEW_CYCLE_COUNT = 2;" in MOTION
    assert 'root.setAttribute("data-landing-motion-playback", "active")' in MOTION
    assert 'root.removeAttribute("data-landing-motion-playback")' in MOTION
    assert 'landing-motion-step-active", "is-active"' in MOTION
    assert 'root.setAttribute("data-landing-motion-phase", "intro")' in MOTION
    assert 'root.setAttribute("data-landing-motion-phase", "settled")' in MOTION
    assert "--portal-landing-motion-sequence: 7600ms;" in THEME
    assert "@keyframes portal-landing-preview-scan" in THEME
    assert "portal-landing-preview-scan 1700ms" in THEME
    assert '[data-landing-motion="cinematic-mini"][data-landing-motion-phase="intro"]' in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    cinematic = THEME[THEME.index('[data-landing-motion="cinematic-mini"]'):]
    assert "animation-iteration-count: infinite" not in cinematic
