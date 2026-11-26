import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {freeToolsReadableColorsHistoricalSource, upstreamRealtimeBannerHistoricalSource, upstreamRealtimeProtectedHistoricalSource} from "./helpers/free-tools-readable-colors-historical.mjs";
import * as historical from "./helpers/free-tools-readable-colors-historical.mjs";
import {imageComposerNativeLocaleHistoricalSource} from "./helpers/image-composer-native-locale-historical.mjs";

const root = new URL("../", import.meta.url);
const read = file => imageComposerNativeLocaleHistoricalSource(fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n"), file);
const contract = JSON.parse(read("tests/fixtures/free-tools-readable-colors-contract.json"));
const revisionSource = (revision, file) => execFileSync("git", ["show", revision + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const prior = file => revisionSource(contract.base, file);

test("physical Free Tools sources are delivered BASE plus exactly nine reviewed color records", () => {
  assert.equal(contract.model, "gemini-4-hydrogen-xhigh");
  assert.equal(contract.records.length, 9);
  assert.deepEqual([...new Set(contract.records.map(record => record.file))].sort(),
    ["static/portal/portal-theme.css", "static/portal/portal.js"]);
  for (const file of new Set(contract.records.map(record => record.file))) {
    let expected = revisionSource(contract.catalog_sync.base, file);
    for (const record of contract.records.filter(record => record.file === file)) {
      assert.equal(expected.split(record.old).length - 1, 1);
      expected = expected.replace(record.old, () => record.new);
    }
    assert.equal(read(file), expected, file);
  }
  assert.equal(read("static/portal/portal.css"), revisionSource(contract.catalog_sync.base, "static/portal/portal.css"));
});

test("catalog historical projection accepts only three exact fixed-main files and preserves mutations, unknown files and already projected bytes", () => {
  assert.equal(typeof historical.upstreamCatalogHistoricalSource, "function");
  assert.equal(contract.catalog_sync.base, "0a9022cefd272369ac150e3b108768fc9f0fb91e");
  assert.equal(contract.catalog_sync.prior, contract.main_sync.base);
  assert.deepEqual(contract.catalog_sync.source_pins.map(row => row.file),
    ["static/portal/portal.js", "static/portal/portal-theme.css", "static/portal/portal.css"]);
  assert.equal(contract.catalog_sync.records.length, 3);
  const hash = text => createHash("sha256").update(text).digest("hex");
  for (const pin of contract.catalog_sync.source_pins) {
    const before = revisionSource(contract.catalog_sync.prior, pin.file);
    const upstream = revisionSource(contract.catalog_sync.base, pin.file);
    assert.equal(hash(before), pin.beforeLfSha256);
    assert.equal(hash(upstream), pin.afterLfSha256);
    assert.equal(historical.upstreamCatalogHistoricalSource(upstream, pin.file), before);
    assert.equal(historical.upstreamCatalogHistoricalSource(before, pin.file), before);
    for (const [changed, expected] of [
      [upstream + "\n/* unknown */", before + "\n/* unknown */"],
      ["/* customer */\n" + upstream, "/* customer */\n" + before],
      [upstream + " ", before + " "],
    ]) {
      assert.equal(historical.upstreamCatalogHistoricalSource(changed, pin.file), expected);
      assert.notEqual(hash(expected), pin.beforeLfSha256);
    }
    const record = contract.catalog_sync.records.find(row => row.file === pin.file);
    assert.equal(before.split(record.old).length - 1, 1);
    assert.equal(before.replace(record.old, () => record.new), upstream);
    const internal = text => text.replace("\n", "\n/* unreviewed internal byte */\n");
    assert.equal(historical.upstreamCatalogHistoricalSource(internal(upstream), pin.file), internal(before));
    assert.notEqual(hash(internal(before)), pin.beforeLfSha256);
    const changedRecord = upstream.replace(record.new, () => record.new.replace("\n", "\n/* mutation */\n"));
    assert.equal(historical.upstreamCatalogHistoricalSource(changedRecord, pin.file), changedRecord);
    assert.throws(() => historical.upstreamCatalogHistoricalSource(upstream + record.new, pin.file));
    assert.equal(historical.upstreamCatalogHistoricalSource(upstream, "unrelated.js"), upstream);
    const other = contract.catalog_sync.source_pins.find(row => row.file !== pin.file).file;
    assert.equal(historical.upstreamCatalogHistoricalSource(upstream, other), upstream);
    const composed = freeToolsReadableColorsHistoricalSource(read(pin.file), pin.file);
    assert.equal(composed, upstream);
    assert.equal(historical.upstreamCatalogHistoricalSource(composed, pin.file), before);
  }
});

test("independently delivered upstream portal source is exactly the original baseline plus its two banner insertions", () => {
  assert.equal(contract.main_sync.prior, contract.base);
  assert.equal(contract.main_sync.base, "fbcbfdf4f6dc3563ceba8b4f2815ae1ebb63d90b");
  assert.equal(contract.main_sync.portal_insertions.length, 2);
  const file = "static/portal/portal.js", upstream = revisionSource(contract.main_sync.base, file);
  assert.equal(upstreamRealtimeBannerHistoricalSource(upstream, file), prior(file));
  assert.equal(upstreamRealtimeBannerHistoricalSource(prior(file), file), prior(file));
  assert.equal(upstreamRealtimeBannerHistoricalSource(upstream + "\n/* unknown */", file), prior(file) + "\n/* unknown */");
  for (const record of contract.main_sync.portal_insertions) {
    assert.throws(() => upstreamRealtimeBannerHistoricalSource(upstream + record, file));
    assert.throws(() => upstreamRealtimeBannerHistoricalSource(upstream.replace(record, ""), file));
  }
  assert.equal(upstreamRealtimeBannerHistoricalSource(upstream, "unrelated.js"), upstream);
});

test("historical protected-file pins accept only exact delivered upstream bytes while raw physical sources remain fixed-main exact", () => {
  const hash = text => createHash("sha256").update(text).digest("hex");
  assert.deepEqual(contract.main_sync.protected_source_pins.map(row => row.file),
    ["copyfast_api.py", "copyfast_realtime_translate.py"]);
  for (const pin of contract.main_sync.protected_source_pins) {
    const before = prior(pin.file), upstream = revisionSource(contract.main_sync.base, pin.file);
    assert.equal(hash(before), pin.beforeLfSha256);
    assert.equal(hash(upstream), pin.afterLfSha256);
    assert.equal(read(pin.file), upstream, "Current protected application source is unprojected fixed-main exact");
    assert.equal(upstreamRealtimeProtectedHistoricalSource(upstream, pin.file), before);
    assert.equal(upstreamRealtimeProtectedHistoricalSource(before, pin.file), before);
    assert.equal(upstreamRealtimeProtectedHistoricalSource(upstream + "\n/* unknown */", pin.file), upstream + "\n/* unknown */");
    assert.notEqual(hash(upstreamRealtimeProtectedHistoricalSource(upstream + " ", pin.file)), pin.beforeLfSha256);
    assert.equal(upstreamRealtimeProtectedHistoricalSource(upstream, "unrelated.py"), upstream);
  }
});

test("reviewed JavaScript records change color fragments only and leave QR image surface and every non-style byte intact", () => {
  const records = contract.records.filter(record => record.file.endsWith("portal.js"));
  assert.equal(records.length, 7);
  const strip = text => text.replace(/\b(?:background|color):\s*[^;]+;/g, "");
  for (const record of records) assert.equal(strip(record.new), strip(record.old));
  const source = read("static/portal/portal.js"), start = source.indexOf('id="free-tools-qr-preview-container"');
  const qr = source.slice(start, source.indexOf('id="free-tools-qr-img"', start));
  assert.match(qr, /background: #ffffff;/);
  assert.match(source, /function handleFreeToolTab\(tabBtn\)/);
  assert.match(source, /function handleFreeToolTabKeydown\(tabBtn, event\)/);
});

test("new CSS rules are scoped to Free Tools and contain only paired colors or focus color, not layout or functionality changes", () => {
  const records = contract.records.filter(record => record.file.endsWith(".css"));
  assert.equal(records.length, 2);
  for (const record of records) {
    let added;
    if (record.new.startsWith(record.old)) added = record.new.slice(record.old.length);
    else {assert(record.new.endsWith(record.old)); added = record.new.slice(0, -record.old.length);}
    const css = added.replace(/\/\*[\s\S]*?\*\//g, "");
    const rules = [...css.matchAll(/([^{}]+)\{([^{}]+)\}/g)];
    assert(rules.length > 0);
    for (const [, selectors, body] of rules) {
      for (const selector of selectors.replace(/:is\([^)]*\)/g, ":is(*)").split(",")) {
        assert.match(selector, /\.portal-page\.portal-free-tools/);
      }
      const declarations = body.split(";").map(part => part.trim()).filter(Boolean);
      for (const declaration of declarations) assert.match(declaration, /^(?:background|color|outline-color): var\(--portal-[a-z-]+\)(?: !important)?$/);
    }
  }
});

test("finite color inverse restores the exact baseline while retaining unknown bytes and rejecting missing or duplicated records", () => {
  for (const file of new Set(contract.records.map(record => record.file))) {
    const records = contract.records.filter(record => record.file === file);
    let candidate = prior(file);
    for (const record of records) candidate = candidate.replace(record.old, () => record.new);
    assert.equal(freeToolsReadableColorsHistoricalSource(candidate, file), prior(file));
    assert.equal(freeToolsReadableColorsHistoricalSource(prior(file), file), prior(file));
    assert.equal(freeToolsReadableColorsHistoricalSource(candidate + "\n/* unknown */", file), prior(file) + "\n/* unknown */");
    assert.equal(freeToolsReadableColorsHistoricalSource(candidate, "unrelated.css"), candidate);
    assert.throws(() => freeToolsReadableColorsHistoricalSource(candidate + records[0].new, file));
    assert.throws(() => freeToolsReadableColorsHistoricalSource(candidate.replace(records.at(-1).new, () => records.at(-1).old), file));
  }
});
