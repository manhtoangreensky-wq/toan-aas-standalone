import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/free-tools-readable-colors-contract.json", import.meta.url), "utf8"));
assert.equal(contract.base, "a8cf07490448548a2a1be6800fb7e146abeac726");
assert.equal(contract.records.length, 9);
const priorProtectedSources = new Map();

export function upstreamCatalogHistoricalSource(source, file) {
  const records = contract.catalog_sync.records.filter(row => row.file === file);
  if (!records.some(row => source.includes(row.new))) return source;
  for (const record of [...records].reverse()) {
    assert.equal(source.split(record.new).length - 1, 1, "Unreviewed upstream catalog source");
    source = source.replace(record.new, () => record.old);
  }
  return source;
}

export function upstreamRealtimeProtectedHistoricalSource(source, file) {
  const pin = contract.main_sync.protected_source_pins.find(row => row.file === file);
  if (!pin || createHash("sha256").update(source).digest("hex") !== pin.afterLfSha256) return source;
  if (!priorProtectedSources.has(file)) {
    const prior = execFileSync("git", ["show", contract.main_sync.prior + ":" + file],
      {cwd: new URL("../../", import.meta.url), encoding: "utf8", maxBuffer: 30e6, windowsHide: true}).replace(/\r\n/g, "\n");
    assert.equal(createHash("sha256").update(prior).digest("hex"), pin.beforeLfSha256);
    priorProtectedSources.set(file, prior);
  }
  return priorProtectedSources.get(file);
}

export function upstreamRealtimeBannerHistoricalSource(source, file) {
  if (file !== "static/portal/portal.js") return source;
  const records = contract.main_sync.portal_insertions;
  if (!records.some(record => source.includes(record))) return source;
  for (const record of records) {
    assert.equal(source.split(record).length - 1, 1, "Unreviewed upstream realtime banner source");
    source = source.replace(record, "");
  }
  return source;
}

export function freeToolsReadableColorsHistoricalSource(source, file) {
  const records = contract.records.filter(record => record.file === file);
  if (!records.some(record => source.includes(record.new))) return source;
  for (const record of [...records].reverse()) {
    assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Free Tools color source");
    source = source.replace(record.new, () => record.old);
  }
  return source;
}
