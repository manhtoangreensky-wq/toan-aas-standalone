import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {imageStudioDetailDraftHistoricalSource} from "./helpers/image-studio-detail-draft-historical.mjs";
import {imageStudioLocaleCopyHistoricalSource} from "./helpers/image-studio-locale-copy-historical.mjs";

const file = "static/portal/portal.js";
const read = path => fs.readFileSync(new URL("../" + path, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const source = read(file);
const contract = JSON.parse(read("tests/fixtures/image-studio-detail-draft-contract.json"));
const loading = JSON.parse(read("tests/fixtures/image-studio-detail-loading-contract.json"));
const record = contract.records[0];
const start = source.indexOf("      if (!keepCustomerHeader) header.innerHTML = headerMarkup;");
const end = source.indexOf("\n      if (!isHydration) {", start);
assert.ok(start >= 0 && end > start);
const block = source.slice(start, end);
const id = "11111111-1111-4111-8111-111111111111";

test("physical source contains only the reviewed loading and form changes", () => {
  let expected = execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
  for (const row of [...loading.records.filter(row => row.file === file), record]) {
    assert.equal(expected.split(row.old).length - 1, 1);
    expected = expected.replace(row.old, () => row.new);
  }
  assert.equal(imageStudioLocaleCopyHistoricalSource(source, file), expected);
  assert.equal(block, record.new);
  assert.equal(imageStudioDetailDraftHistoricalSource(source, file), source.replace(record.new, () => record.old));
  assert.equal(imageStudioDetailDraftHistoricalSource(source + "\n/* unrelated */", file), source.replace(record.new, () => record.old) + "\n/* unrelated */");
  assert.throws(() => imageStudioDetailDraftHistoricalSource(source + record.new, file));
});

function control(name, value, type = "text", options = {}) {
  return {name, value, type, tagName: type === "select-one" ? "SELECT" : "INPUT", checked: false, ...options,
    matches(selector) {assert.equal(selector, ":disabled"); return Boolean(this.disabled || this.fieldsetDisabled);}};
}
function option(value, disabled = false, groupDisabled = false) {
  return {value, disabled, closest(selector) {assert.equal(selector, "optgroup:disabled"); return groupDisabled ? {} : null;}};
}
function form(action, route, revision, direction = "", directionRevision = "1") {
  const attributes = {"data-portal-action": action, "data-portal-route": route, "data-image-artboard-id": id,
    "data-image-artboard-revision": revision, "data-image-direction-id": direction, "data-image-direction-revision": directionRevision};
  return {attributes, controls: [control("title", "Saved " + (direction || action)), control("creative_brief", "Saved brief")],
    getAttribute: name => attributes[name] ?? null, querySelectorAll: () => this?.controls};
}
function makeForm(...args) {
  const value = form(...args);
  value.querySelectorAll = () => value.controls;
  return value;
}
function run(family, scenario = "same") {
  const route = family + "/" + id;
  const kinds = ["image-artboard-update", "image-direction-create", "image-direction-update", "image-direction-update"];
  const old = kinds.map((action, index) => makeForm(action, route, "1", index > 1 ? String(index) : ""));
  const next = kinds.map((action, index) => makeForm(action, route, scenario === "boardRevision" ? "2" : "1", index > 1 ? String(index) : "",
    scenario === "directionRevision" && index === 2 ? "2" : "1"));
  old.forEach((item, index) => {item.controls[0].value = "Edited " + index;});
  const state = {path: route, session: {authenticated: true, csrfToken: scenario === "session" ? "new-session" : "current-session"}};
  let normalizations = 0, currentForms = old;
  if (scenario === "duplicate") {
    old[3].attributes["data-image-direction-id"] = "2"; next[3].attributes["data-image-direction-id"] = "2";
  }
  if (scenario.startsWith("option")) {
    const selected = control("aspect_ratio", "4:5", "select-one", {options: [option("1:1"), option("4:5")], selectedIndex: 1});
    const options = scenario === "optionRemoved" ? [option("1:1")] : [option("1:1"), option("4:5", scenario === "optionDisabled", scenario === "optionGroup")];
    old[0].controls.push(selected); next[0].controls.push(control("aspect_ratio", "1:1", "select-one", {options, selectedIndex: 0}));
  }
  if (scenario === "disabled") old[0].controls[0].disabled = true;
  if (scenario === "fieldset") old[0].controls[0].fieldsetDisabled = true;
  const box = {keepCustomerHeader: true, header: {}, headerMarkup: "", lastCustomerHeaderMarkup: "",
    lastCustomerHeaderSessionToken: "current-session", headerSessionToken: state.session.csrfToken,
    isHydration: scenario !== "route", page: {layout: scenario === "unrelated" ? "dashboard" : "image-studio-detail"},
    context: state, actualPath: route, lastNormalizedRoute: route, mountGeneration: 1, mountId: 1,
    normalizePath: value => value, getBootstrap: () => {normalizations++; return state;},
    renderPage: () => {
      if (scenario === "logoutDuringRender") state.session.authenticated = false;
      if (scenario === "newerMount") box.mountGeneration++;
      return "next";
    },
    main: {querySelectorAll: () => currentForms}};
  Object.defineProperty(box.main, "innerHTML", {set: () => {currentForms = next;}});
  vm.createContext(box); vm.runInContext(block, box);
  return {old, next, normalizations, values: next.map(item => item.controls[0].value)};
}

for (const family of ["/image-studio", "/image-hub"]) {
  test(`${family}: hydration retains independent same-revision edits`, () => {
    assert.deepEqual(run(family).values, ["Edited 0", "Edited 1", "Edited 2", "Edited 3"]);
  });
  test(`${family}: changed session, route, revisions and currentness never restore stale edits`, () => {
    for (const scenario of ["session", "route", "boardRevision", "logoutDuringRender", "newerMount"]) {
      assert.ok(run(family, scenario).values.every(value => value.startsWith("Saved")), scenario);
    }
    assert.deepEqual(run(family, "directionRevision").values, ["Edited 0", "Edited 1", "Saved 2", "Edited 3"]);
  });
  test(`${family}: duplicate form identity does not transfer input between forms`, () => {
    assert.deepEqual(run(family, "duplicate").values, ["Edited 0", "Edited 1", "Saved 2", "Saved 3"]);
  });
  test(`${family}: disabled fields and unavailable selections keep server values`, () => {
    for (const scenario of ["disabled", "fieldset"]) assert.ok(run(family, scenario).values[0].startsWith("Saved"));
    for (const scenario of ["optionRemoved", "optionDisabled", "optionGroup"]) {
      const result = run(family, scenario);
      assert.equal(result.next[0].controls.at(-1).value, "1:1", scenario);
    }
  });
}

test("unrelated page hydration performs no additional bootstrap normalization", () => {
  assert.equal(run("/image-studio", "unrelated").normalizations, 0);
});
