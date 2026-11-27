import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {galleryReadabilityHistoricalSource as project} from "./helpers/gallery-readability-historical.mjs";
import {FAMILY_READABILITY_ADDITION} from "./helpers/feature-family-readability-historical.mjs";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixtures/gallery-readability.json", import.meta.url), "utf8"));
const prior = JSON.parse(fs.readFileSync(new URL("./fixtures/gallery-customer-copy.json", import.meta.url), "utf8"));
const cssFile = "static/portal/portal-theme.css", portalFile = fixture.portalRecord.file;
const addition = "\n" + fixture.cssMarker + "\n" + fixture.cssRules.join("\n") + "\n";
const record = fixture.portalRecord, fail = /Unreviewed Gallery readability/;
const hash = value => createHash("sha256").update(value).digest("hex");
const base = {}, before = {}, current = {};
for (const file of [cssFile, portalFile]) {
  base[file] = execFileSync("git", ["show", fixture.base_sha + ":" + file], {
    encoding: "utf8", maxBuffer: 12e6
  }).replace(/\r\n/g, "\n");
  before[file] = base[file];
  for (const row of prior.records.filter(row => row.file === file)) {
    assert.equal(before[file].split(row.old).length - 1, 1);
    before[file] = before[file].replace(row.old, () => row.new);
  }
  current[file] = file === cssFile ? before[file] + addition : before[file].replace(record.old, () => record.new);
}

test("independent public BASE + GPC56 source matches frozen pre-GPR pins", () => {
  assert.equal(hash(before[cssFile]), fixture.cssBeforeLfSha256);
  assert.equal(hash(before[portalFile]), fixture.portalBeforeLfSha256);
  assert(before[cssFile].endsWith(FAMILY_READABILITY_ADDITION));
  assert.equal(before[portalFile].split(record.old).length - 1, 1);
});
test("an unrelated old CSS font edit survives without a full-source hash gate", () => {
  const bad = current[cssFile].replace("font-size: 16px;", "font-size: 17px;");
  const expected = before[cssFile].replace("font-size: 16px;", "font-size: 17px;");
  assert.notEqual(expected, before[cssFile]);
  assert.equal(project(bad, cssFile), expected);
});
test("unknown bytes inside the function but outside the owned metric slot survive", () => {
  const point = "    const catalogTotal =";
  const at = current[portalFile].indexOf(point, current[portalFile].indexOf("  function renderFreePromptGallery("));
  assert(at >= 0);
  const edited = current[portalFile].slice(0, at) + "    /* UNKNOWN */\n" + current[portalFile].slice(at);
  const beforeAt = before[portalFile].indexOf(point, before[portalFile].indexOf("  function renderFreePromptGallery("));
  assert.equal(project(edited, portalFile),
    before[portalFile].slice(0, beforeAt) + "    /* UNKNOWN */\n" + before[portalFile].slice(beforeAt));
});
for (const file of [cssFile, portalFile]) {
  test(file + " BASE and pre-GPR sources are unchanged", () => {
    assert.equal(project(base[file], file), base[file]);
    assert.equal(project(before[file], file), before[file]);
  });
  test(file + " exact GPR inverse restores pre-GPR and is idempotent", () => {
    assert.equal(project(current[file], file), before[file]);
    assert.equal(project(project(current[file], file), file), before[file]);
  });
  test(file + " unknown prefix, suffix, and internal bytes survive", () => {
    assert.equal(project("/* CUSTOMER */\r\n" + current[file] + "\r\n/* TAIL */", file),
      "/* CUSTOMER */\r\n" + before[file] + "\r\n/* TAIL */");
    assert.equal(project(current[file].replace("\n", "\n/* UNKNOWN */\n"), file),
      before[file].replace("\n", "\n/* UNKNOWN */\n"));
    assert.equal(project(current[file].replace("\n", "\n/* UNKNOWN */\n"), "customer/unrelated.js"),
      current[file].replace("\n", "\n/* UNKNOWN */\n"));
  });
  test(file + " unrelated target remains unchanged even for malformed owned input", () => {
    assert.equal(project(current[file] + addition + record.new, "customer/unrelated.js"),
      current[file] + addition + record.new);
  });
}

const css = current[cssFile], rules = fixture.cssRules;
const cssCases = {
  "partial rule set": css.replace(rules[5] + "\n", ""),
  "changed CSS value": css.replace(rules[0], rules[0].replace("font-size: 16px;", "font-size: 17px;")),
  "missing marker": css.replace(fixture.cssMarker, ""),
  "duplicate marker": css + fixture.cssMarker,
  "duplicate addition": css + addition,
  "detached addition": addition + before[cssFile],
  "addition before prior FCR": before[cssFile].replace(FAMILY_READABILITY_ADDITION,
    addition + FAMILY_READABILITY_ADDITION),
  "gap after prior FCR": before[cssFile] + "\n/* UNKNOWN GAP */\n" + addition,
  "reordered rules": css.replace(rules[0] + "\n" + rules[1], rules[1] + "\n" + rules[0]),
  "duplicate selector owner": css + rules[0].replace("16px", "18px") + "\n",
  "selector without marker": before[cssFile] + "\n" + rules[0] + "\n",
  "changed prior FCR anchor": css.replace(FAMILY_READABILITY_ADDITION,
    FAMILY_READABILITY_ADDITION.replace("color: var(--portal-text);", "color: red;"))
};
for (const [name, bad] of Object.entries(cssCases)) {
  test("CSS inverse rejects " + name, () => {
    assert.notEqual(bad, css);
    assert.throws(() => project(bad, cssFile), fail);
  });
}

const portal = current[portalFile], owner = "  function renderFreePromptGallery(";
const intro = '<section class="portal-content-prompt-pack-intro">';
const portalCases = {
  "changed condition": portal.replace(record.new, record.new.replace("canBrowse", "canRead")),
  "changed false branch": portal.replace(record.new, record.new.replace('` : ""}', '` : "pending"}')),
  "changed metric content": portal.replace(record.new, record.new.replace("intro.stat.categories", "intro.stat.UNKNOWN")),
  "changed metrics opening tag": portal.replace(record.new, record.new.replace("<dl>", "<ul>")),
  "partial conditional opening": portal.replace(record.new, record.new.slice("${canBrowse ? `".length)),
  "partial conditional closing": portal.replace(record.new, record.new.slice(0, -'` : ""}'.length)),
  "duplicate fragment": portal + "\n" + record.new,
  "detached fragment": portal.replace(record.new, "") + "\n" + record.new,
  "misplaced inside the correct function": portal.replace(record.new, "").replace(intro, intro + record.new),
  "wrong function owner": portal.replace(owner, "  function UNREVIEWED("),
  "duplicate function owner": portal + "\n" + owner + ") {\n  }\n",
  "extra old metrics outside conditional": portal + "\n" + record.old,
  "recognizable partial fragment": before[portalFile] + "\n${canBrowse ? `<dl",
  "standalone fragment without owner": record.new
};
for (const [name, bad] of Object.entries(portalCases)) {
  test("portal inverse rejects " + name, () => {
    assert.notEqual(bad, portal);
    assert.throws(() => project(bad, portalFile), fail);
  });
}
