import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const sha = raw => createHash("sha256").update(raw).digest("hex");
const raw = fs.readFileSync(new URL("../fixtures/media-fixed-feedback-reviewed.json", import.meta.url));
const contractRaw = fs.readFileSync(new URL("../fixtures/media-fixed-feedback-contract.json", import.meta.url));
const fail = "Unreviewed media fixed feedback", count = (source, part) => source.split(part).length - 1;
assert.equal(sha(raw), "808d89af0587a53a13bb78e83be5e8fab6f6e7e98240183b9966766ae5febfa6", fail + " reviewed authority");
assert.equal(sha(contractRaw), "b1a1293fd200c49ac4348c7e2f9965df6b9d5b0ae83562fff240a1ae013eddbc", fail + " Root authority");
const fixture = JSON.parse(raw), contract = JSON.parse(contractRaw);
assert.equal(fixture.schema, "MEDIA_FIXED_FEEDBACK_REVIEWED_PROVENANCE_V1", fail);
assert.equal(fixture.base, "6f04b8449d7354ca44397c199ccdda77107f577e", fail);
assert.equal(fixture.rootContractRawSha256, sha(contractRaw), fail);
assert.equal(fixture.canonicalRecords, 11); assert.equal(fixture.historicalFragments.length, 9);
const I = "static/portal/integration.js", L = "static/portal/portal-i18n.js";
const owned = source => /\bmediaWorkspace(?:FeedbackText|ErrorText)\b|audioWorkspace\.feedback\./.test(source);
const boundary = (source, marker) => {
  assert.equal(count(source, marker), 1, fail + " unique boundary:" + marker);
  return source.indexOf(marker);
};

// Finite historical-input compatibility only. Current acceptance uses the
// separate complete151 BASE +11-record forward gate, never this projection.
export function mediaFixedFeedbackHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source type");
  assert.equal(typeof file, "string", fail + " file type");
  if (![I, L].includes(file) || !owned(source)) return source;
  const fragments = fixture.historicalFragments.filter(row => row.file === file);
  if (file === I) {
    for (const fragment of fragments) {
      const start = boundary(source, fragment.owner), end = boundary(source, fragment.next);
      assert.ok(end > start, fail + " bounded owner order");
      assert.equal(source.slice(start, end), fragment.new, fail + " complete bounded region");
      assert.equal(count(source, fragment.new), 1, fail + " unique current region");
    }
  } else {
    assert.equal(fragments.length, 1);
    const [fragment] = fragments;
    const verify = boundary(source, fragment.owner), next = boundary(source, fragment.next);
    const call = boundary(source, "  verifyEqualKeysets();"), freeze = boundary(source, "  deepFreeze(MESSAGES);");
    assert.equal(count(source, fragment.new), 1, fail + " exact latest catalogue append");
    const at = source.indexOf(fragment.new);
    assert.ok(verify < at && at < call && call < next && next < freeze, fail + " catalogue order");
    assert.ok(source.slice(at + fragment.new.length).startsWith("\n\n  function deepFreeze(value) {"),
      fail + " immediate catalogue boundary");
  }
  let result = source;
  for (const fragment of [...fragments].reverse()) result = result.replace(fragment.new, () => fragment.old);
  assert.equal(owned(result), false, fail + " partial or detached owned marker");
  return result;
}

export function mediaFixedFeedbackHistoricalSnapshot(entries, locale) {
  assert.ok(["vi", "en", "zh"].includes(locale), fail + " locale");
  assert.ok(Array.isArray(entries) && entries.every(row => Array.isArray(row) && row.length === 2), fail + " entries");
  const rows = [...contract.errors, ...contract.toasts], keys = rows.map(row => "audioWorkspace.feedback." + row.key);
  const current = entries.filter(([key]) => typeof key === "string" && key.startsWith("audioWorkspace.feedback."));
  if (!current.length) return entries;
  assert.equal(current.length, 43, fail + " complete key count");
  assert.deepEqual(current.map(([key]) => key), keys, fail + " exact namespace/key order");
  const positions = [];
  for (const [index, row] of rows.entries()) {
    const matches = entries.filter(([key]) => key === keys[index]);
    assert.equal(matches.length, 1, fail + " unique key");
    assert.equal(matches[0][1], row[locale], fail + " exact locale value");
    positions.push(entries.findIndex(([key]) => key === keys[index]));
  }
  assert.ok(positions.every((at, index) => index === 0 || at === positions[index - 1] + 1), fail + " consecutive new rows");
  const remove = new Set(keys);
  return entries.filter(([key]) => !remove.has(key));
}
