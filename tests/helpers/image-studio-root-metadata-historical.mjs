import assert from "node:assert/strict";
import fs from "node:fs";
import {imageStudioRootHeadingHistoricalSource} from "./image-studio-root-heading-historical.mjs";
import {imageStudioValidationHistoricalSource, imageStudioValidationHistoricalSnapshot} from "./image-studio-validation-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-root-metadata-contract.json", import.meta.url)));
assert.equal(contract.base, "3d21e950fb8e676ffd0b8c945a5ff6d9c8425736");
assert.equal(contract.records.length, 7);

export function imageStudioRootMetadataHistoricalSource(source, file) {
  source = imageStudioValidationHistoricalSource(source, file);
  source = imageStudioRootHeadingHistoricalSource(source, file);
  const records = contract.records.filter(row => row.file === file);
  if (!records.length || !source.includes(records[0].new)) return source;
  for (const record of [...records].reverse()) {
    assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Image root metadata source");
    source = source.replace(record.new, () => record.old);
  }
  return source;
}

const parseRow = text => JSON.parse(text.trim().replace(/,$/, ""));
const added = new Map(contract.records[2].new.split("\n").slice(1).map(parseRow)
  .map(row => ["imageStudioUi." + row[0], row]));
const changed = new Map(contract.records.slice(3).map(record => {
  const old = parseRow(record.old), next = parseRow(record.new);
  return ["imageStudioLibraryUi." + next[0], {old, next}];
}));

export function imageStudioRootMetadataHistoricalSnapshot(entries, locale) {
  entries = imageStudioValidationHistoricalSnapshot(entries, locale);
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0 && Array.isArray(entries));
  const recognized = entries.filter(([key]) => added.has(key) || changed.has(key));
  if (!recognized.some(([key, value]) => added.has(key)
    || (changed.get(key)?.old[index] !== changed.get(key)?.next[index] && value === changed.get(key)?.next[index]))) return entries;
  assert.equal(recognized.length, 6, "Partial Image root metadata dictionary");
  assert.equal(new Set(recognized.map(([key]) => key)).size, 6, "Duplicate Image root metadata dictionary");
  const result = [];
  for (const entry of entries) {
    const [key, value] = entry;
    if (added.has(key)) {
      assert.equal(value, added.get(key)[index], "Unreviewed Image root metadata key");
    } else if (changed.has(key)) {
      const row = changed.get(key);
      assert.equal(value, row.next[index], "Unreviewed Image root library metadata");
      result.push([key, row.old[index]]);
    } else result.push(entry);
  }
  return result;
}
