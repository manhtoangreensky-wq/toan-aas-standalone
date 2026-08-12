"""Red contracts for truthful customer PWA navigation and workspace motion.

The dock and animation layer are presentation-only. They must not infer
authority, invoke an action, request data, or make a guarded workflow look
available. The Node harness executes the real route helper instead of a
duplicated Python route map.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
MOTION = (ROOT / "static" / "portal" / "portal-motion.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def _run_mobile_dock_harness(source_path: Path) -> dict[str, list[str]]:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal customer dock helper")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error("missing " + start);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error("missing end " + end);
  return source.slice(offset, finish);
}
const runtime = [
  'const window = { location: { pathname: "/dashboard" } };',
  extract("function normalizePath(path)", "const CAPABILITY_HUB_FAMILY_KEYS"),
  extract("function matchesRouteFamily(path, root)", "function isNavCurrent(linkPath, page)"),
  extract("function isNavCurrent(linkPath, page)", "// The compact dock intentionally links"),
  extract("const CUSTOMER_MOBILE_NAV_GROUPS", "function isMobileNavCurrent(key, page)"),
  extract("function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")
].join("\n");
eval(runtime);
const keys = ["dashboard", "studio", "jobs", "assets", "account"];
const cases = {
  setup: "/workspace/setup",
  video: "/video-studio/story-video-plan",
  document: "/documents/ocr",
  contentCaption: "/content/caption",
  contentPackAlias: "/content-pack",
  contentStudio: "/content-studio",
  contentStudioDetail: "/content-studio/brief-42",
  promptAlias: "/prompts",
  imageRoot: "/image",
  videoRoot: "/video",
  pdfAlias: "/pdf",
  muxAlias: "/mux",
  imageStudio: "/image-studio/artboard-42",
  voiceStudio: "/voice-studio/vault-42",
  mediaWorkspace: "/media-workspace/collection-42",
  imageHistory: "/image/history",
  videoProgress: "/video/progress",
  videoExport: "/video/export",
  voiceVault: "/voice",
  savedVoice: "/voice/saved",
  savedVoiceVaultAlias: "/voice/vault",
  voicePreview: "/voice/preview",
  musicLibrary: "/music/library",
  musicLibraryAlias: "/music-library",
  project: "/projects/project-42",
  workboard: "/workboard/board-42",
  job: "/jobs/job-42",
  campaignReport: "/campaign/report",
  promptLibrary: "/prompt-library/library-42",
  vault: "/asset-vault",
  accountSecurity: "/account/security",
  ticket: "/tickets/ticket-42",
  consultation: "/crm/consultations/new",
  referral: "/referrals",
  sourceRights: "/guides/source-rights",
  unknownGuide: "/guides/not-a-real-page",
  admin: "/admin/jobs"
};
const result = {};
for (const entry of Object.entries(cases)) {
  const name = entry[0];
  const routePath = entry[1];
  result[name] = keys.filter((key) => isMobileNavCurrent(key, { routePath, path: routePath }));
}
process.stdout.write(JSON.stringify(result));
'''
    result = subprocess.run(
        [node, "-e", script, str(source_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def test_customer_dock_maps_one_truthful_group_per_known_route() -> None:
    assert _run_mobile_dock_harness(ROOT / "static" / "portal" / "portal.js") == {
        "setup": ["dashboard"],
        "video": ["studio"],
        "document": ["studio"],
        "contentCaption": ["studio"],
        "contentPackAlias": ["studio"],
        "contentStudio": ["studio"],
        "contentStudioDetail": ["studio"],
        "promptAlias": ["studio"],
        "imageRoot": ["studio"],
        "videoRoot": ["studio"],
        "pdfAlias": ["studio"],
        "muxAlias": ["studio"],
        "imageStudio": ["studio"],
        "voiceStudio": ["studio"],
        "mediaWorkspace": ["studio"],
        "imageHistory": ["assets"],
        "videoProgress": ["jobs"],
        "videoExport": ["assets"],
        "voiceVault": ["assets"],
        "savedVoice": ["studio"],
        "savedVoiceVaultAlias": ["studio"],
        "voicePreview": ["assets"],
        "musicLibrary": ["assets"],
        "musicLibraryAlias": ["assets"],
        "project": ["jobs"],
        "workboard": ["jobs"],
        "job": ["jobs"],
        "campaignReport": ["jobs"],
        "promptLibrary": ["assets"],
        "vault": ["assets"],
        "accountSecurity": ["account"],
        "ticket": ["account"],
        "consultation": ["account"],
        "referral": ["account"],
        "sourceRights": ["dashboard"],
        "unknownGuide": [],
        "admin": [],
    }


def test_customer_dock_uses_fixed_presentation_groups_without_authority_inputs() -> None:
    dock = _section(PORTAL, "function isMobileNavCurrent(key, page)", "function renderMobileNav(page)")

    assert "const CUSTOMER_MOBILE_NAV_GROUPS = Object.freeze({" in PORTAL
    assert "function customerMobileNavGroupForPath(path)" in PORTAL
    assert 'if (path === "/admin" || path.startsWith("/admin/")) return false;' in dock
    assert "customerMobileNavGroupForPath(path) === key" in dock
    for forbidden in ("context", "session", "role", "adminErpNavigation", "fetch(", "dispatchAction", "wallet", "provider"):
        assert forbidden not in dock


def test_workspace_motion_is_browser_only_and_cleans_up_before_remount() -> None:
    assert "function mountWorkspace(root)" in MOTION
    assert "function unmountWorkspace()" in MOTION
    assert "mountWorkspace," in MOTION
    assert "unmountWorkspace" in MOTION
    for forbidden in (
        "fetch(",
        "localStorage",
        "sessionStorage",
        "innerHTML",
        "/api/",
        "csrf",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "indexedDB",
        "caches",
        "document.cookie",
    ):
        assert forbidden not in MOTION

    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")
    assert 'if (typeof motion.unmountWorkspace === "function") motion.unmountWorkspace();' in mount
    assert "function mountWorkspaceMotion()" in mount
    assert "motion.mountWorkspace(main)" in mount
    assert mount.index("motion.unmountWorkspace") < mount.index("function renderShell()")
    assert mount.index("mountWorkspaceMotion();") > mount.index("mountLandingMotion();")


def test_workspace_motion_has_bounded_reveal_interaction_and_reduced_motion_rules() -> None:
    assert "@keyframes portal-workspace-reveal" in THEME
    assert ".portal-workspace-motion-target.is-pending" in THEME
    assert ".portal-workspace-motion-target.is-visible" in THEME
    assert ".portal-workspace-motion-item" in THEME
    assert "animation-delay: calc(var(--portal-workspace-motion-index, 0) * 34ms);" in THEME
    assert "@media (hover: hover) and (pointer: fine)" in THEME
    assert "transform: translateY(-1px);" in THEME
    assert "@media (hover: none), (pointer: coarse)" in THEME
    assert "transform: scale(.985);" in THEME
    assert "animation: none !important;" in THEME
    assert "transition: none !important;" in THEME
    assert "transform: none !important;" in THEME


def test_workspace_reveal_observer_does_not_hide_a_partially_visible_primary_group() -> None:
    workspace = _section(MOTION, "function mountWorkspace(root)", "function mountLanding(root)")

    assert "rootMargin: \"0px 0px -8%\", threshold: 0" in workspace
    assert "threshold: 0.12" not in workspace


def test_workspace_motion_cleans_up_when_reduced_motion_is_enabled_mid_session() -> None:
    """A preference change must never leave signed workspace content hidden.

    This runs the real Portal lifecycle with a deliberately tiny DOM harness:
    an observer reveal, keyboard focus reveal, then an OS-level reduced-motion
    change.  It proves the presentation layer removes its own classes,
    listeners and inline stagger index without touching network or account
    state.
    """

    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the Portal motion lifecycle")
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
    querySelectorAll() { return items; },
    addEventListener(name, listener) { listeners.set(name, listener); },
    removeEventListener(name) { listeners.delete(name); },
    emit(name) {
      const listener = listeners.get(name);
      if (listener) listener({ currentTarget: this });
    },
    hasListener(name) { return listeners.has(name); }
  };
}

const firstItem = element();
const secondItem = element();
const first = element([firstItem]);
const second = element([secondItem]);
const root = {
  querySelectorAll(selector) {
    return selector.includes("portal-catalog-context") ? [first, second] : [];
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
observer.callback([{ target: first, isIntersecting: true }]);
second.emit("focusin");
const beforePreferenceChange = {
  firstVisible: first.classList.contains("is-visible"),
  secondVisible: second.classList.contains("is-visible"),
  itemIndex: firstItem.style.get("--portal-workspace-motion-index"),
  firstFocusBound: first.hasListener("focusin"),
  preferenceBound: Boolean(motionListener)
};
preference.emit(true);
process.stdout.write(JSON.stringify({
  beforePreferenceChange,
  afterPreferenceChange: {
    observerDisconnected: observer.disconnected,
    firstHasMotionClass: first.classList.contains("portal-workspace-motion-target"),
    firstPending: first.classList.contains("is-pending"),
    secondVisible: second.classList.contains("is-visible"),
    firstItemHasMotionClass: firstItem.classList.contains("portal-workspace-motion-item"),
    firstItemIndex: firstItem.style.get("--portal-workspace-motion-index"),
    firstFocusBound: first.hasListener("focusin"),
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
        "beforePreferenceChange": {
            "firstVisible": True,
            "secondVisible": True,
            "itemIndex": "0",
            "firstFocusBound": True,
            "preferenceBound": True,
        },
        "afterPreferenceChange": {
            "observerDisconnected": True,
            "firstHasMotionClass": False,
            "firstPending": False,
            "secondVisible": False,
            "firstItemHasMotionClass": False,
            "firstItemIndex": None,
            "firstFocusBound": False,
            "preferenceBound": False,
        },
    }


def test_cross_document_route_motion_is_opt_in_and_reduced_motion_safe() -> None:
    """Real Portal navigations keep a calm visual hand-off when supported.

    Portal deliberately uses regular server navigations for signed route
    guards, so this contract protects the CSS-level progressive enhancement
    instead of introducing a browser-side router or intercepting links.
    """

    assert "@view-transition {\n  navigation: auto;\n}" in THEME
    assert "::view-transition-old(root)" in THEME
    assert "::view-transition-new(root)" in THEME
    assert "portal-route-exit" in THEME
    assert "portal-route-enter" in THEME

    assert "@media (prefers-reduced-motion: reduce) {\n  @view-transition {\n    navigation: none;\n  }" in THEME
