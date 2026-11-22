import assert from "node:assert/strict";
import fs from "node:fs";
import {imageStudioPresentationHistoricalSource, imageStudioPresentationHistoricalSnapshot} from "./image-studio-presentation-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-option-labels-contract.json", import.meta.url)));
const fail = "Unreviewed Image Studio option copy";
assert.equal(contract.base, "f4c5b6a9821cf957ce107778fd9abd884075fd50", fail);
assert.equal(contract.records.length, 6, fail);
export function imageStudioOptionsHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  source = imageStudioPresentationHistoricalSource(source, file);
  const records = contract.records.filter(row => row.file === file);
  if (!records.length) return source;
  const marker = file.endsWith("portal.js") ? 'imageStudioText(`ratio.${value}`' : "IMAGE_STUDIO_RATIO_COPY_ROWS";
  if (!source.includes(marker)) return source;
  for (const row of records) assert.equal(source.split(row.new).length - 1, 1, fail);
  for (const row of [...records].reverse()) source = source.replace(row.new, () => row.old);
  return source;
}
export function imageStudioOptionsHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(Array.isArray(entries) && index > 0, fail);
  entries = imageStudioPresentationHistoricalSnapshot(entries, locale);
  const ratioKeys = contract.ratioRows.map(row => row[0]);
  const found = entries.filter(([key]) => typeof key === "string" && key.startsWith("imageStudioUi.ratio."));
  if (!found.length) return entries;
  assert.deepEqual(found.map(([key]) => key), ratioKeys, fail);
  for (const row of contract.ratioRows) assert.equal(found.find(([key]) => key === row[0])[1], row[index], fail);
  for (const row of contract.formatNew) {
    const matches = entries.filter(([key]) => key === row[0]);
    assert.equal(matches.length, 1, fail);
    assert.equal(matches[0][1], row[index], fail);
  }
  return entries.filter(([key]) => !ratioKeys.includes(key)).map(row => {
    const old = contract.formatOld.find(([key]) => key === row[0]);
    return old ? [row[0], old[index]] : row;
  });
}
