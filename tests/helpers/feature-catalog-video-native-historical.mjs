import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {featureCatalogDescriptions108HistoricalSource} from "./feature-catalog-descriptions108-historical.mjs";

const raw = fs.readFileSync(new URL("../fixtures/feature-catalog-video-native.json", import.meta.url), "utf8").replace(/\r\n/g, "\n");
assert.equal(createHash("sha256").update(raw).digest("hex"), "779bcfefeb30412268baf725b334af65f8e6922e7d748f2f40c0c10e11ed4f42");
const fixture = JSON.parse(raw), file = "static/portal/portal-feature-catalog-copy.js";
assert.equal(fixture.base_sha, "ccf824a1482ef3ae7fd2d4187932902e36ddbc14");
assert.equal(fixture.beforeLfSha256, "164b3dbe7384a78985e5c1f279eebea12f7f5cb4c74e4091b7396821d596a799");
assert.equal(fixture.afterLfSha256, "8680e808c06e64358fe63ed08a7b06d21f9ccdc08e48f6e3cf4a19de35f4e329");
const keys = fixture.entries.map(entry => entry.key), rows = fixture.records;
assert.equal(keys.length, 27);
assert.equal(new Set(keys).size, 27);
assert.equal(rows.length, 9);
assert.ok(rows.every(row => row.file === file && row.new.endsWith(row.old)));
const count = (source, fragment) => source.split(fragment).length - 1;
const failure = "Unreviewed catalogue video historical source";

// Only older source-pin consumers use this inverse; current acceptance reads raw bytes.
export function featureCatalogVideoNativeHistoricalSource(source, target) {
  source = featureCatalogDescriptions108HistoricalSource(source, target);
  if (target !== file) return source;
  const declarations = keys.map(key => [...source.matchAll(new RegExp('^    "' + key + '": \\{', "gm"))].length);
  if (!declarations.some(Boolean)) return source;
  assert.ok(declarations.every(total => total === 3), failure);
  for (const row of rows) assert.equal(count(source, row.new), 1, failure);
  const order = rows.map((row, index) => ({index, at: source.indexOf(row.new)}))
    .sort((left, right) => left.at - right.at).map(row => row.index);
  assert.deepEqual(order, [0, 3, 6, 1, 4, 7, 2, 5, 8], failure);
  for (const row of rows) source = source.replace(row.new, () => row.old);
  return source;
}
