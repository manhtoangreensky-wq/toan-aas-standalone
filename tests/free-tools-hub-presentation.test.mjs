import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const i18nSource = readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const cssSource = readFileSync(path.join(repoRoot, "static/portal/portal.css"), "utf8");
const rendererStart = portalSource.indexOf("  function renderFreeTools(page, context)");
const rendererEnd = portalSource.indexOf("\n  function handleFreeToolTab", rendererStart);
const tabStart = portalSource.indexOf("  function handleFreeToolTab(tabBtn)");
const tabEnd = portalSource.indexOf("\n  function handleFreeToolAction", tabStart);

assert.notEqual(rendererStart, -1, "Free Tools renderer exists");
assert.notEqual(rendererEnd, -1, "Free Tools renderer boundary exists");
assert.notEqual(tabStart, -1, "Free Tools tab handler exists");
assert.notEqual(tabEnd, -1, "Free Tools tab handler boundary exists");

const rendererSource = portalSource.slice(rendererStart, rendererEnd);
const tabSource = portalSource.slice(tabStart, tabEnd);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

function copyFor(key, fallback, params) {
  return String(fallback || "").replace(/\{([A-Za-z0-9_.-]+)\}/g, (_, name) => (
    Object.prototype.hasOwnProperty.call(params || {}, name) ? String(params[name]) : `{${name}}`
  ));
}

const renderFreeTools = new Function(
  "renderHero",
  "badge",
  "renderNotes",
  "safeText",
  "freeToolsText",
  "VIETQR_BANKS",
  `${rendererSource}\nreturn renderFreeTools;`
)(
  () => "<header>Free Tools</header>",
  (state) => `<span data-test-badge="${escapeHtml(state)}">${escapeHtml(state)}</span>`,
  () => "",
  escapeHtml,
  copyFor,
  [{ code: "VCB", shortName: "VCB", name: "Vietcombank" }]
);

function render(locale = "vi") {
  return renderFreeTools(
    { routePath: "/free-tools", title: "Free Tools" },
    { locale }
  );
}

test("Free Tools exposes an accessible six-tab presentation with one active panel", () => {
  const html = render();
  assert.match(html, /role="tablist"[^>]*aria-orientation="horizontal"/);
  assert.equal((html.match(/role="tab"/g) || []).length, 6);
  assert.equal((html.match(/role="tabpanel"/g) || []).length, 6);
  assert.equal((html.match(/aria-selected="true"/g) || []).length, 1);
  assert.equal((html.match(/aria-selected="false"/g) || []).length, 5);
  assert.equal((html.match(/tabindex="0"/g) || []).length, 1);
  assert.equal((html.match(/tabindex="-1"/g) || []).length, 5);
  assert.equal((html.match(/hidden data-free-tool-panel=/g) || []).length, 5);
  assert.match(html, /id="free-tools-panel-subtitle"[^>]*aria-hidden="false"/);
  assert.match(html, /id="free-tools-panel-youtube"[^>]*aria-hidden="true"[^>]*hidden/);
  assert.match(html, /aria-controls="free-tools-panel-codec"/);
});

test("Free Tools keeps fixed copy out of Vietnamese English-generic leakage", () => {
  for (const legacyCopy of [
    "100% Client-Side",
    "Xử lý tại Browser",
    "Subtitle Processor",
    "YouTube Extractor & Thumbnails",
    "Paragraphs",
    "Copy Link",
    "Developer Utilities",
    "Content & Typography",
    "Voiceover",
    "Encoding & Hashing Utilities",
    "Base64 Encode",
    "Base64 Decode",
    "URL Encode",
    "URL Decode"
  ]) {
    assert.doesNotMatch(rendererSource, new RegExp(legacyCopy.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), legacyCopy);
  }
  assert.match(rendererSource, /freeToolsText\(/);
  assert.match(i18nSource, /const FREE_TOOLS_COPY_ROWS = \[/);
  for (const key of ["intro.kicker", "nav.codec", "subtitle.stats", "youtube.title", "vietqr.title", "json.title", "text.title", "codec.title", "privacy.body"]) {
    assert.match(i18nSource, new RegExp(`\\["${key.replace(".", "\\.")}"`), `${key} has a reviewed locale row`);
  }
});

test("Free Tools tab keyboard navigation updates selection and panel visibility in place", () => {
  const helpers = new Function(`${tabSource}\nreturn { handleFreeToolTab, handleFreeToolTabKeydown };`)();
  const panels = [];
  const root = {
    querySelectorAll(selector) {
      if (selector === "[data-free-tool-tab]") return tabs;
      if (selector === "[data-free-tool-panel]") return panels;
      return [];
    }
  };
  const tabs = ["subtitle", "youtube", "vietqr", "json", "text", "codec"].map((key, index) => {
    const attributes = {
      "data-free-tool-tab": key,
      "aria-selected": index === 0 ? "true" : "false",
      "aria-pressed": index === 0 ? "true" : "false",
      tabindex: index === 0 ? "0" : "-1"
    };
    return {
      attributes,
      focused: false,
      closest() { return root; },
      getAttribute(name) { return attributes[name] ?? ""; },
      setAttribute(name, value) { attributes[name] = value; },
      focus() { this.focused = true; },
      classList: { toggle() {} }
    };
  });
  ["subtitle", "youtube", "vietqr", "json", "text", "codec"].forEach((key, index) => {
    const attributes = { "data-free-tool-panel": key, "aria-hidden": index === 0 ? "false" : "true" };
    panels.push({
      attributes,
      hidden: index !== 0,
      getAttribute(name) { return attributes[name] ?? ""; },
      setAttribute(name, value) { attributes[name] = value; },
      classList: { toggle() {} }
    });
  });

  const event = { key: "ArrowRight", prevented: false, preventDefault() { this.prevented = true; } };
  assert.equal(helpers.handleFreeToolTabKeydown(tabs[0], event), true);
  assert.equal(event.prevented, true);
  assert.equal(tabs[1].focused, true);
  assert.equal(tabs[1].attributes["aria-selected"], "true");
  assert.equal(tabs[0].attributes.tabindex, "-1");
  assert.equal(panels[0].hidden, true);
  assert.equal(panels[1].hidden, false);

  const endEvent = { key: "End", prevented: false, preventDefault() { this.prevented = true; } };
  assert.equal(helpers.handleFreeToolTabKeydown(tabs[1], endEvent), true);
  assert.equal(tabs[5].focused, true);
  assert.equal(tabs[5].attributes["aria-selected"], "true");
  assert.equal(panels[5].hidden, false);
});

test("Free Tools CSS targets the current renderer classes and stacks on narrow screens", () => {
  assert.match(cssSource, /\.portal-free-tools-tab\s*\{/);
  assert.match(cssSource, /\.portal-free-tool-panel\[hidden\]/);
  assert.match(cssSource, /\.portal-free-tools-intro\s*\{/);
  assert.match(cssSource, /@media \(max-width: 760px\)/);
});
