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

const helperStart = portalSource.indexOf("  function setYouTubeThumbnailPreview(");
const helperNextFunc = portalSource.indexOf("\n  function ", helperStart + 1);
const helperEnd = helperNextFunc !== -1 ? helperNextFunc : portalSource.indexOf("\n  }", helperStart) + 4;

assert.notEqual(rendererStart, -1, "Free Tools renderer exists");
assert.notEqual(rendererEnd, -1, "Free Tools renderer boundary exists");
assert.notEqual(tabStart, -1, "Free Tools tab handler exists");
assert.notEqual(tabEnd, -1, "Free Tools tab handler boundary exists");
assert.notEqual(helperStart, -1, "Free Tools thumbnail helper exists");
assert.notEqual(helperEnd, -1, "Free Tools thumbnail helper boundary exists");

const rendererSource = portalSource.slice(rendererStart, rendererEnd);
const tabSource = portalSource.slice(tabStart, tabEnd);
const helperSource = portalSource.slice(helperStart, helperEnd);
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

test("Free Tools exposes an accessible ten-tab presentation with one active panel", () => {
  const html = render();
  assert.match(html, /role="tablist"[^>]*aria-orientation="horizontal"/);
  assert.equal((html.match(/role="tab"/g) || []).length, 10);
  assert.equal((html.match(/role="tabpanel"/g) || []).length, 10);
  assert.equal((html.match(/aria-selected="true"/g) || []).length, 1);
  assert.equal((html.match(/aria-selected="false"/g) || []).length, 9);
  assert.equal((html.match(/tabindex="0"/g) || []).length, 1);
  assert.equal((html.match(/tabindex="-1"/g) || []).length, 9);
  assert.equal((html.match(/hidden data-free-tool-panel=/g) || []).length, 9);
  assert.match(html, /id="free-tools-panel-subtitle"[^>]*aria-hidden="false"/);
  assert.match(html, /id="free-tools-panel-youtube"[^>]*aria-hidden="true"[^>]*hidden/);
  assert.match(html, /aria-controls="free-tools-panel-codec"/);
});

test("Free Tools exposes the four utility lanes with explicit guarded states", () => {
  const html = render();
  for (const lane of ["avatar", "rate", "weather", "downloader"]) {
    assert.match(html, new RegExp(`data-free-tool-tab="${lane}"`));
    assert.match(html, new RegExp(`data-free-tool-panel="${lane}"`));
    assert.match(html, new RegExp(`data-free-tool-result="${lane}"`));
  }
  assert.match(html, /data-free-tool-action="prepare-avatar" disabled/);
  assert.match(html, /data-free-tool-action="refresh-rate" disabled/);
  assert.match(html, /data-free-tool-action="lookup-weather" disabled/);
  assert.match(html, /data-free-tool-action="inspect-download" disabled/);
  assert.match(html, /free-tools-downloader-rights/);
  assert.match(html, /free-tools-avatar-rights/);
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
  assert.doesNotMatch(rendererSource, /onerror\s*=/, "Free Tools thumbnails do not use inline CSP handlers");
  assert.doesNotMatch(render(), /<img[^>]+src=["']\s*["']/, "Free Tools does not mount empty image sources anywhere in rendered output");
  assert.doesNotMatch(rendererSource, /<img[^>]+src=["']\s*["']/, "Free Tools renderer source contains no empty image sources");
  assert.doesNotMatch(rendererSource, /youtube\.preview\.pending/, "Free Tools does not retain fixed pending placeholder copy");
  assert.doesNotMatch(render(), /youtube\.preview\.pending/, "Rendered Free Tools contains no fixed pending placeholder copy");
  assert.match(i18nSource, /const FREE_TOOLS_COPY_ROWS = \[/);
  for (const key of ["intro.kicker", "nav.codec", "nav.avatar", "nav.rate", "nav.weather", "nav.downloader", "subtitle.stats", "youtube.title", "youtube.preview.loading", "youtube.preview.unavailable", "vietqr.title", "avatar.title", "rate.title", "weather.title", "downloader.title", "json.title", "text.title", "codec.title", "privacy.body"]) {
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
  const tabs = ["subtitle", "youtube", "vietqr", "avatar", "rate", "weather", "downloader", "json", "text", "codec"].map((key, index) => {
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
  ["subtitle", "youtube", "vietqr", "avatar", "rate", "weather", "downloader", "json", "text", "codec"].forEach((key, index) => {
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
  assert.equal(tabs[9].focused, true);
  assert.equal(tabs[9].attributes["aria-selected"], "true");
  assert.equal(panels[9].hidden, false);
});

test("Free Tools CSS targets the current renderer classes and stacks on narrow screens", () => {
  assert.match(cssSource, /\.portal-free-tools-tab\s*\{/);
  assert.match(cssSource, /\.portal-free-tool-panel\[hidden\]/);
  assert.match(cssSource, /\.portal-free-tools-intro\s*\{/);
  assert.match(cssSource, /@media \(max-width: 760px\)/);
});

test("Free Tools YouTube thumbnail preview helper manages lifecycle and replaces listeners", () => {
  const setYouTubeThumbnailPreview = new Function(
    "document",
    "freeToolsText",
    `${helperSource}\nreturn setYouTubeThumbnailPreview;`
  )(
    {
      getElementById(id) {
        return elements.get(id) || null;
      }
    },
    copyFor
  );

  const elements = new Map();

  function createStubElement(id, initialAttrs = {}) {
    return {
      id,
      hidden: false,
      alt: "",
      src: "",
      textContent: "",
      naturalWidth: 0,
      onload: null,
      onerror: null,
      ...initialAttrs
    };
  }

  // 1. Missing elements and empty url are safe
  assert.doesNotThrow(() => {
    setYouTubeThumbnailPreview("missing-image", "missing-state", "https://img.youtube.com/vi/abc/hqdefault.jpg", "alt");
  }, "Missing elements do not throw");

  const image = createStubElement("free-tools-yt-thumb-max", { hidden: false });
  const state = createStubElement("free-tools-yt-thumb-max-state", { hidden: true });
  elements.set("free-tools-yt-thumb-max", image);
  elements.set("free-tools-yt-thumb-max-state", state);

  assert.doesNotThrow(() => {
    setYouTubeThumbnailPreview("free-tools-yt-thumb-max", "free-tools-yt-thumb-max-state", "", "alt");
  }, "Empty URL returns safely");

  // 2. Initial loading lifecycle
  const firstUrl = "https://img.youtube.com/vi/abc123xyz/maxresdefault.jpg";
  setYouTubeThumbnailPreview("free-tools-yt-thumb-max", "free-tools-yt-thumb-max-state", firstUrl, "Ảnh thu nhỏ tối đa");
  assert.equal(image.hidden, true, "Image hidden during initial loading");
  assert.equal(state.hidden, false, "State visible during initial loading");
  assert.equal(state.textContent, "Đang tải ảnh thu nhỏ…", "State shows loading copy");
  assert.equal(image.alt, "Ảnh thu nhỏ tối đa", "Image alt is set");
  assert.equal(image.src, firstUrl, "Image src assigned after handlers");
  assert.equal(typeof image.onload, "function", "onload handler registered");
  assert.equal(typeof image.onerror, "function", "onerror handler registered");

  // 3. Load -> real image (naturalWidth > 0)
  image.naturalWidth = 1280;
  image.onload();
  assert.equal(state.hidden, true, "State hidden on successful image load");
  assert.equal(image.hidden, false, "Real image visible on successful load");

  // 4. Failed -> plain error & handler replacement
  const secondUrl = "https://img.youtube.com/vi/badid404/maxresdefault.jpg";
  const firstOnload = image.onload;
  const firstOnerror = image.onerror;
  setYouTubeThumbnailPreview("free-tools-yt-thumb-max", "free-tools-yt-thumb-max-state", secondUrl, "Ảnh thu nhỏ lỗi");
  assert.notEqual(image.onload, firstOnload, "onload handler replaced on second request");
  assert.notEqual(image.onerror, firstOnerror, "onerror handler replaced on second request");
  assert.equal(image.hidden, true, "Image hidden during load");
  assert.equal(state.hidden, false, "State visible during load");

  image.naturalWidth = 0;
  image.onerror();
  assert.equal(image.hidden, true, "Image hidden on error");
  assert.equal(state.hidden, false, "State visible on error");
  assert.equal(state.textContent, "Không tải được ảnh thu nhỏ từ YouTube.", "State shows unavailable copy");

  // 5. Retry -> load recovery
  const thirdUrl = "https://img.youtube.com/vi/retryvalid/hqdefault.jpg";
  const secondOnload = image.onload;
  const secondOnerror = image.onerror;
  setYouTubeThumbnailPreview("free-tools-yt-thumb-max", "free-tools-yt-thumb-max-state", thirdUrl, "Ảnh thu nhỏ phục hồi");
  assert.notEqual(image.onload, secondOnload, "onload handler replaced on retry");
  assert.notEqual(image.onerror, secondOnerror, "onerror handler replaced on retry");
  assert.equal(image.hidden, true, "Image hidden on retry load");
  assert.equal(state.hidden, false, "State visible on retry load");

  image.naturalWidth = 480;
  image.onload();
  assert.equal(state.hidden, true, "State hidden after successful retry load");
  assert.equal(image.hidden, false, "Image visible after successful retry load");

  // Edge case: onload with naturalWidth <= 0 triggers unavailable state
  setYouTubeThumbnailPreview("free-tools-yt-thumb-max", "free-tools-yt-thumb-max-state", "https://img.youtube.com/vi/zero/hqdefault.jpg", "Ảnh 0px");
  image.naturalWidth = 0;
  image.onload();
  assert.equal(image.hidden, true, "Image hidden when naturalWidth is 0");
  assert.equal(state.hidden, false, "State visible when naturalWidth is 0");
  assert.equal(state.textContent, "Không tải được ảnh thu nhỏ từ YouTube.");
});
