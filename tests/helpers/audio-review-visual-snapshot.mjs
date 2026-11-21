import assert from "node:assert/strict";
import fs from "node:fs";
import {audioReviewReadabilityHistoricalSource} from "./audio-review-readability-snapshot.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/audio-review-visual-contract.json", import.meta.url), "utf8"));
const fail = "Unreviewed audio review visual";
const count = (text, fragment) => text.split(fragment).length - 1;
assert.equal(contract.base, "ea4da7c446059f911f3b59d61f9f92f63ea95c94", fail);
assert.equal(contract.records.length, 3, fail);

export function audioReviewVisualHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  assert.equal(typeof file, "string", fail);
  source = audioReviewReadabilityHistoricalSource(source, file);
  const records = contract.records.filter(row => row.file === file);
  if (!records.length) return source;
  const markers = file.endsWith("portal.js")
    ? ["page.layout === \"audio-hub-detail\" ? audioWorkspaceText('workspace.hubLabel'",
       'audioWorkspaceText(count === 1 ? "review.reference"']
    : ['"audioWorkspace.review.reference"'];
  if (!markers.some(marker => source.includes(marker))) return source;
  for (const row of records) {
    assert.equal(count(source, row.new), 1, fail + " exact current record");
    if (!row.new.includes(row.old)) assert.equal(count(source, row.old), 0, fail + " mixed previous record");
  }
  for (const row of records) source = source.replace(row.new, () => row.old);
  assert.ok(markers.every(marker => !source.includes(marker)), fail + " detached marker");
  return source;
}

export function audioReviewVisualHistoricalSnapshot(entries, locale) {
  assert.ok(["vi", "en", "zh"].includes(locale) && Array.isArray(entries), fail);
  const key = "audioWorkspace.review.reference", matches = entries.filter(row => row[0] === key);
  if (!matches.length) return entries;
  assert.equal(matches.length, 1, fail);
  assert.equal(matches[0][1], {vi: "tệp tham khảo", en: "reference file", zh: "个参考文件"}[locale], fail);
  return entries.filter(row => row !== matches[0]);
}
