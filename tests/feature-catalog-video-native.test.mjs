import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const root = process.env.CVN_TEST_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixturePath = process.env.CVN_TEST_FIXTURE || path.join(root, "tests/fixtures/feature-catalog-video-native.json");
const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const copySource = fs.readFileSync(path.join(root, "static/portal/portal-feature-catalog-copy.js"), "utf8").replace(/\r\n/g, "\n");
const source = fs.readFileSync(path.join(root, "static/portal/portal-features.js"), "utf8");

// Keep the real card renderer; this tree only records its text and attributes.
class Element {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.className = ""; this.textContent = ""; this.children = []; this.attributes = {}; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  appendChild(child) { this.children.push(child); return child; }
}
const document = { createElement: tag => new Element(tag) }, window = {};
const context = vm.createContext({ window, document, console, Set, Object, Array });
vm.runInContext(copySource, context);
const boot = "window.__TOAN_AAS_FEATURES_READY__ = hydrateFeatures();";
assert.equal(source.split(boot).length - 1, 1, "actual standalone hydration boundary must be unambiguous");
vm.runInContext(source.replace(boot, "window.__videoCopyTest = { featureCard, COPY };"), context);
const { featureCard, COPY } = window.__videoCopyTest;
const collect = node => [node, ...node.children.flatMap(collect)];
const dictionary = window.TOANAASFeatureCatalogCopy;
const states = [["guarded", "guarded"], ["web_native", "planning_only"], ["bot_companion", "available"]];
const inputFor = (entry, mode, status) => ({ key: entry.key, route: entry.route, group: "video", kind: "customer",
  title: entry.sourceTitle, description: entry.sourceDescription,
  engine: { mode, execution_state: mode === "guarded" ? "guarded" : "ready" }, readiness: { status } });

for (const locale of ["vi", "en", "zh"]) for (const entry of fixture.entries) {
  test(`native video card preserves route/search/state and source data: ${locale}.${entry.key}`, () => {
    const expected = fixture.copy[locale][entry.key];
    for (const [mode, status] of states) {
      const input = inputFor(entry, mode, status), before = JSON.stringify(input);
      const card = featureCard(input, COPY[locale], locale), nodes = collect(card);
      assert.equal(nodes.find(node => node.tagName === "H3").textContent, expected.title);
      assert.equal(nodes.find(node => node.tagName === "P").textContent, expected.description);
      assert.equal(nodes.find(node => node.tagName === "A").attributes.href, entry.route);
      assert.equal(card.attributes["data-feature-key"], entry.key);
      assert.equal(card.attributes["data-feature-route"], entry.route);
      assert.equal(nodes.find(node => node.className === "portal-engine-label").attributes["data-engine-mode"], mode);
      assert.equal(nodes.find(node => node.className === "portal-readiness-label").attributes["data-readiness"], status);
      for (const term of [expected.title, expected.description, input.title, input.description, entry.key, entry.route]) {
        if (term) assert.ok(card.attributes["data-catalog-text"].includes(term.toLocaleLowerCase()), "source and native search terms must both remain");
      }
      assert.equal(JSON.stringify(input), before);
    }
  });
}

for (const locale of ["vi", "en", "zh"]) {
  test(`unregistered future card retains source-authored copy in ${locale}`, () => {
    const input = inputFor({key: "future_video_tool", route: "/future-video-tool",
      sourceTitle: "Owner title <safe>", sourceDescription: "Owner text & details"}, "guarded", "guarded");
    const before = JSON.stringify(input), nodes = collect(featureCard(input, COPY[locale], locale));
    assert.equal(nodes.find(node => node.tagName === "H3").textContent, "Owner title <safe>");
    assert.equal(nodes.find(node => node.tagName === "P").textContent, "Owner text & details");
    assert.equal(JSON.stringify(input), before);
  });
}

test("all 135 registered customer cards have exactly one native copy entry per locale", () => {
  assert.equal(fixture.entries.length, 27);
  for (const locale of ["vi", "en", "zh"]) {
    const expected = [...Object.keys(fixture.beforeCopy[locale]), ...fixture.entries.map(entry => entry.key)].sort();
    assert.equal(expected.length, 135);
    assert.deepEqual(Object.keys(dictionary[locale]).sort(), expected);
  }
});

test("the existing 108 card translations in each locale remain unchanged", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, row] of Object.entries(fixture.beforeCopy[locale])) {
    assert.equal(dictionary[locale][key].title, row.title);
    assert.equal(dictionary[locale][key].description, row.description);
  }
});

test("the physical lightweight bundle contains only the reviewed data insertions", () => {
  assert.equal(createHash("sha256").update(copySource).digest("hex"), fixture.afterLfSha256);
});
