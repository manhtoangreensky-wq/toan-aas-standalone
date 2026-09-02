"""Behavior contracts for the isolated /features Customer navigation shell."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "static" / "portal" / "portal-features.js"
CSS = ROOT / "static" / "portal" / "portal.css"


def _rule(source: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>.*?)\}", source, re.DOTALL)
    assert match, f"missing exact rule: {selector}"
    return match.group("body")


def _declarations(source: str, selector: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for item in _rule(source, selector).split(";"):
        if ":" not in item:
            continue
        name, value = item.split(":", 1)
        declarations[name.strip()] = value.strip()
    return declarations


def _run_node(script: str) -> dict:
    node = shutil.which("node")
    assert node, "Node.js is required for the real navigation behavior harness"
    result = subprocess.run(
        [node, "-e", script, str(FEATURES)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


SHELL_HARNESS = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error("missing " + start);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error("missing " + end);
  return source.slice(offset, finish);
}

class Events {
  constructor() { this.listeners = new Map(); }
  addEventListener(name, handler) {
    if (!this.listeners.has(name)) this.listeners.set(name, new Set());
    this.listeners.get(name).add(handler);
  }
  removeEventListener(name, handler) {
    if (this.listeners.has(name)) this.listeners.get(name).delete(handler);
  }
  emit(name, init = {}) {
    const event = {
      type: name, key: "", shiftKey: false, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
      ...init
    };
    for (const handler of [...(this.listeners.get(name) || [])]) handler(event);
    return event;
  }
}

class Classes {
  constructor() { this.values = new Set(); }
  add(...names) { names.forEach((name) => this.values.add(name)); }
  remove(...names) { names.forEach((name) => this.values.delete(name)); }
  contains(name) { return this.values.has(name); }
  set(value) { this.values = new Set(String(value || "").split(/\s+/).filter(Boolean)); }
}

let documentRef = null;
class Element extends Events {
  constructor(tag) {
    super();
    this.tagName = String(tag).toUpperCase();
    this.attributes = new Map();
    this.children = [];
    this.hidden = false;
    this.classList = new Classes();
    this.textContent = "";
  }
  set className(value) { this.classList.set(value); }
  get className() { return [...this.classList.values].join(" "); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  hasAttribute(name) { return this.attributes.has(name); }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) { if (child) this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children.filter(Boolean); }
  descendants() { return this.children.flatMap((child) => [child, ...child.descendants()]); }
  querySelectorAll(selector) {
    if (selector.includes("a[href]") || selector.includes("button:not")) {
      return this.descendants().filter((item) => (
        (item.tagName === "A" && item.hasAttribute("href"))
        || (item.tagName === "BUTTON" && !item.hasAttribute("disabled"))
        || ["INPUT", "SELECT", "TEXTAREA", "SUMMARY"].includes(item.tagName)
      ));
    }
    return [];
  }
  querySelector(selector) {
    if (selector === "[data-portal-close-menu]") {
      return this.descendants().find((item) => item.hasAttribute("data-portal-close-menu")) || null;
    }
    return null;
  }
  contains(target) { return target === this || this.descendants().includes(target); }
  focus() { documentRef.activeElement = this; }
}

const documentEvents = new Events();
const sidebar = new Element("aside");
const backdrop = new Element("div");
const header = new Element("header");
const mobile = new Element("nav");
const main = new Element("main");
const media = new Events();
media.matches = true;
media.set = function set(matches) { this.matches = matches; this.emit("change", { matches }); };

const document = {
  activeElement: null,
  createElement(tag) { return new Element(tag); },
  getElementById(id) {
    if (id === "portal-sidebar") return sidebar;
    if (id === "portal-main" || id === "portal-root") return main;
    return null;
  },
  querySelector(selector) {
    if (selector === "[data-portal-sidebar]") return sidebar;
    if (selector === "[data-portal-backdrop]") return backdrop;
    if (selector === "[data-portal-header]") return header;
    if (selector === "[data-portal-mobile-nav]") return mobile;
    if (selector === "[data-portal-menu]") {
      return header.descendants().find((item) => item.hasAttribute("data-portal-menu")) || null;
    }
    return null;
  },
  addEventListener(name, handler) { documentEvents.addEventListener(name, handler); },
  removeEventListener(name, handler) { documentEvents.removeEventListener(name, handler); },
  emit(name, init) { return documentEvents.emit(name, init); }
};
documentRef = document;
const window = {
  matchMedia() { return media; },
  requestAnimationFrame(callback) { callback(); }
};
global.document = document;
global.window = window;
function renderCatalogue() {}
function renderGuarded() {}
function mountFeatureMotion() {}

const runtime = [
  extract("const COPY = Object.freeze({", "function safeRoute(value)"),
  extract("function make(tag, className, text)", "function signal(className"),
  extract("function renderShell(features, account, locale, ready)", "async function hydrateFeatures()")
].join("\n") + "\n;global.__nav = { COPY, renderSidebar, renderHeader, renderMobile, bindFeatureNavigation, renderShell };";
eval(runtime);
const api = global.__nav;
'''


def test_customer_sidebar_logo_fits_its_scoped_frame_without_changing_the_global_asset_contract() -> None:
    css = CSS.read_text(encoding="utf-8")
    global_rule = _declarations(css, ".portal-brand-mark-image")
    scoped_rule = _declarations(
        css,
        '.portal-shell[data-portal-app-kind="customer"] .portal-sidebar .portal-brand-mark-image',
    )

    assert global_rule["width"] == "56px"
    assert global_rule["height"] == "56px"
    assert global_rule["max-width"] == "none"
    assert global_rule["transform"] == "translate(-8px, -4px)"
    assert scoped_rule["width"] == "100%"
    assert scoped_rule["height"] == "100%"
    assert scoped_rule["max-width"] == "100%"
    assert scoped_rule["object-fit"] == "contain"
    assert scoped_rule["transform"] == "none"


def test_customer_tablet_menu_keeps_a_full_touch_target() -> None:
    css = CSS.read_text(encoding="utf-8")
    rule = _declarations(
        css,
        '.portal-shell[data-portal-app-kind="customer"] .portal-menu-button',
    )
    assert rule["width"] == "44px"
    assert rule["min-width"] == "44px"
    assert rule["min-height"] == "44px"


def test_features_shell_renders_the_official_brand_and_five_locale_pure_dock_destinations() -> None:
    result = _run_node(
        SHELL_HARNESS
        + r'''
const expected = {
  vi: ["Trang chủ", "Tạo", "Công việc", "Thư viện", "Tài khoản"],
  en: ["Home", "Create", "Work", "Library", "Account"],
  zh: ["首页", "创建", "工作", "资源库", "账户"]
};
const expectedSidebar = {
  vi: ["Tổng quan", "Danh mục", "Không gian", "Tài khoản"],
  en: ["Overview", "Catalogue", "Workspaces", "Account"],
  zh: ["总览", "功能目录", "工作空间", "账户"]
};
const cases = {};
for (const locale of ["vi", "en", "zh"]) {
  api.renderSidebar(sidebar, api.COPY[locale]);
  api.renderMobile(mobile, api.COPY[locale]);
  api.renderMobile(mobile, api.COPY[locale]);
  const image = sidebar.descendants().find((item) => item.tagName === "IMG");
  const links = mobile.children;
  cases[locale] = {
    image: image && Object.fromEntries(image.attributes),
    brandHref: sidebar.children[0].children[0] && sidebar.children[0].children[0].getAttribute("href"),
    brandChildren: sidebar.children[0].children.map((item) => item.tagName),
    closeInsideBrandLink: Boolean(sidebar.children[0].children[0] && sidebar.children[0].children[0].querySelector("[data-portal-close-menu]")),
    hrefs: links.map((item) => item.getAttribute("href")),
    current: links.filter((item) => item.getAttribute("aria-current") === "page").map((item) => item.getAttribute("href")),
    labels: links.map((item) => item.children[1] && item.children[1].textContent),
    sidebarLabels: sidebar.children[1].children[1].children.map((item) => item.children[1] && item.children[1].textContent),
    count: links.length,
    expected: expected[locale],
    expectedSidebar: expectedSidebar[locale],
    closeLabel: sidebar.querySelector("[data-portal-close-menu]")?.getAttribute("aria-label")
  };
}
process.stdout.write(JSON.stringify(cases));
'''
    )

    close_labels = {"vi": "Đóng điều hướng", "en": "Close navigation", "zh": "关闭导航"}
    for locale, case in result.items():
        assert case["count"] == 5
        assert case["brandHref"] == "/dashboard"
        assert case["brandChildren"] == ["A", "BUTTON"]
        assert case["closeInsideBrandLink"] is False
        assert case["hrefs"] == ["/dashboard", "/features", "/jobs", "/assets", "/account"]
        assert case["current"] == ["/features"]
        assert case["labels"] == case["expected"]
        assert case["sidebarLabels"] == case["expectedSidebar"]
        assert case["closeLabel"] == close_labels[locale]
        assert case["image"] == {
            "src": "/static/logo_ch%C3%ADnh_th%E1%BB%A9c.png",
            "alt": "",
            "width": "56",
            "height": "56",
            "decoding": "async",
        }


def test_features_render_shell_binds_the_real_navigation_after_rendering_controls() -> None:
    result = _run_node(
        SHELL_HARNESS
        + r'''
api.renderShell([], { displayName: "QA", email: "qa@example.invalid" }, "vi", true);
const menu = document.querySelector("[data-portal-menu]");
const close = sidebar.querySelector("[data-portal-close-menu]");
const controls = sidebar.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary");
const initial = {
  hidden: sidebar.getAttribute("aria-hidden"),
  fallback: controls.filter((item) => item.getAttribute("tabindex") === "-1").length,
  total: controls.length,
  expanded: menu && menu.getAttribute("aria-expanded")
};
menu.emit("click");
process.stdout.write(JSON.stringify({
  initial,
  open: sidebar.classList.contains("is-open"),
  role: sidebar.getAttribute("role"),
  modal: sidebar.getAttribute("aria-modal"),
  focusClose: document.activeElement === close
}));
'''
    )

    assert result["initial"]["hidden"] == "true"
    assert result["initial"]["fallback"] == result["initial"]["total"]
    assert result["initial"]["expanded"] == "false"
    assert result["open"] is True
    assert result["role"] == "dialog"
    assert result["modal"] == "true"
    assert result["focusClose"] is True


def test_features_mobile_drawer_runs_real_open_close_focus_trap_and_breakpoint_transitions() -> None:
    source = FEATURES.read_text(encoding="utf-8")
    assert "function bindFeatureNavigation(copy)" in source

    result = _run_node(
        SHELL_HARNESS
        + r'''
const copy = api.COPY.vi;
api.renderSidebar(sidebar, copy);
api.renderHeader(header, { displayName: "QA", email: "qa@example.invalid" }, copy);
api.renderMobile(mobile, copy);
api.bindFeatureNavigation(copy);
api.bindFeatureNavigation(copy);
const menu = document.querySelector("[data-portal-menu]");
const close = sidebar.querySelector("[data-portal-close-menu]");
const controls = sidebar.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary");
const receipt = {
  initial: {
    hidden: sidebar.getAttribute("aria-hidden"),
    fallback: controls.filter((item) => item.getAttribute("tabindex") === "-1").length,
    total: controls.length,
    expanded: menu.getAttribute("aria-expanded"),
    backdrop: backdrop.hidden
  }
};
menu.emit("click");
receipt.open = {
  open: sidebar.classList.contains("is-open"),
  role: sidebar.getAttribute("role"),
  modal: sidebar.getAttribute("aria-modal"),
  hidden: sidebar.getAttribute("aria-hidden"),
  expanded: menu.getAttribute("aria-expanded"),
  backdrop: backdrop.hidden,
  focusClose: document.activeElement === close
};
menu.emit("click");
receipt.menuToggleClose = {
  open: sidebar.classList.contains("is-open"),
  hidden: sidebar.getAttribute("aria-hidden"),
  expanded: menu.getAttribute("aria-expanded"),
  backdrop: backdrop.hidden,
  focusMenu: document.activeElement === menu
};
menu.emit("click");
const first = controls[0], last = controls[controls.length - 1];
last.focus();
const tab = document.emit("keydown", { key: "Tab" });
receipt.tab = { prevented: tab.defaultPrevented, wrapped: document.activeElement === first };
first.focus();
const shiftTab = document.emit("keydown", { key: "Tab", shiftKey: true });
receipt.shiftTab = { prevented: shiftTab.defaultPrevented, wrapped: document.activeElement === last };
document.emit("keydown", { key: "Escape" });
receipt.escape = {
  open: sidebar.classList.contains("is-open"),
  hidden: sidebar.getAttribute("aria-hidden"),
  expanded: menu.getAttribute("aria-expanded"),
  focusMenu: document.activeElement === menu
};
menu.emit("click");
backdrop.emit("click");
receipt.backdrop = { open: sidebar.classList.contains("is-open"), focusMenu: document.activeElement === menu };
menu.emit("click");
close.emit("click");
receipt.close = { open: sidebar.classList.contains("is-open"), focusMenu: document.activeElement === menu };
media.set(false);
receipt.desktop = {
  hidden: sidebar.getAttribute("aria-hidden"),
  fallback: controls.filter((item) => item.getAttribute("tabindex") === "-1").length,
  role: sidebar.getAttribute("role"),
  focusAnchor: document.activeElement && document.activeElement.tagName === "A"
};
media.set(true);
receipt.mobileAgain = {
  hidden: sidebar.getAttribute("aria-hidden"),
  fallback: controls.filter((item) => item.getAttribute("tabindex") === "-1").length,
  total: controls.length,
  focusMenu: document.activeElement === menu
};
process.stdout.write(JSON.stringify(receipt));
'''
    )

    assert result["initial"] == {
        "hidden": "true",
        "fallback": result["initial"]["total"],
        "total": result["initial"]["total"],
        "expanded": "false",
        "backdrop": True,
    }
    assert result["initial"]["total"] >= 5
    assert result["open"] == {
        "open": True,
        "role": "dialog",
        "modal": "true",
        "hidden": None,
        "expanded": "true",
        "backdrop": False,
        "focusClose": True,
    }
    assert result["menuToggleClose"] == {
        "open": False,
        "hidden": "true",
        "expanded": "false",
        "backdrop": True,
        "focusMenu": True,
    }
    assert result["tab"] == {"prevented": True, "wrapped": True}
    assert result["shiftTab"] == {"prevented": True, "wrapped": True}
    assert result["escape"] == {"open": False, "hidden": "true", "expanded": "false", "focusMenu": True}
    assert result["backdrop"] == {"open": False, "focusMenu": True}
    assert result["close"] == {"open": False, "focusMenu": True}
    assert result["desktop"] == {"hidden": None, "fallback": 0, "role": None, "focusAnchor": True}
    assert result["mobileAgain"]["hidden"] == "true"
    assert result["mobileAgain"]["fallback"] == result["mobileAgain"]["total"]
    assert result["mobileAgain"]["focusMenu"] is True
