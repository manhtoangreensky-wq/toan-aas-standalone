import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {mediaFixedFeedbackHistoricalSource, mediaFixedFeedbackHistoricalSnapshot} from "./media-fixed-feedback-snapshot.mjs";

const raw = fs.readFileSync(new URL("../fixtures/media-detail-customer-copy-reviewed.json", import.meta.url));
const fail = "Unreviewed media detail customer copy", count = (value, part) => value.split(part).length - 1;
assert.equal(createHash("sha256").update(raw).digest("hex"),
  "a2209d2a371b0323480cadaa01d1726ac330c5fc6c3cc5473b13df8726fd79bd", fail + " authority");
const fixture = JSON.parse(raw), portal = "static/portal/portal.js", catalogue = "static/portal/portal-i18n.js";
const css = "static/portal/portal-theme.css";
assert.equal(fixture.schema, "MEDIA_DETAIL_CUSTOMER_COPY_REVIEWED_V1", fail);
assert.equal(fixture.base, "051b936695638a5f083396194730861dc7831da1", fail);
assert.equal(fixture.historicalFragments.length, 9, fail);
assert.equal(fixture.canonicalChanges.length, 53, fail);
const marker = source => /audioWorkspace(?:Text\("pagination\.audioFiles"|Text\("detail\.tagsPlaceholder"|\.(?:pagination\.audioFiles|detail\.tagsPlaceholder))/.test(source)
  || source.includes('}, "media-item-attach")');
const boundary = (source, value) => {
  assert.equal(count(source, value), 1, fail + " unique boundary:" + value);
  return source.indexOf(value);
};

// Historical test-input projection only. Raw current acceptance separately
// compares all151 physical sources with Git BASE +53 immutable forward records.
export function mediaDetailCustomerCopyHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source type");
  assert.equal(typeof file, "string", fail + " file type");
  source = mediaFixedFeedbackHistoricalSource(source, file);
  if (![portal, catalogue, css].includes(file)) return source;
  if (file === css) {
    const fragment = fixture.historicalFragments.find(row => row.file === css);
    const owned = source.includes(fragment.owner) ||
      source.includes(".portal-page:is(.portal-media-workspace-detail, .portal-audio-hub-detail)");
    if (!owned) return source;
    assert.equal(count(source, fragment.owner), 1, fail + " CSS owner");
    assert.equal(count(source, fragment.new), 1, fail + " exact CSS block");
    return source.replace(fragment.new, () => fragment.old);
  }
  if (!marker(source)) return source;
  const fragments = fixture.historicalFragments.filter(row => row.file === file);
  if (file === portal) {
    let result = source, last = -1;
    for (const fragment of fragments) {
      const start = boundary(result, fragment.owner), end = boundary(result, fragment.next);
      assert.ok(start > last && end > start, fail + " function order");
      assert.equal(result.slice(start, end), fragment.new, fail + " complete bounded function");
      assert.equal(count(result, fragment.new), 1, fail + " unique complete function");
      result = result.slice(0, start) + fragment.old + result.slice(end);
      last = start;
    }
    assert.equal(marker(result), false, fail + " detached/partial current marker");
    return result;
  }
  const [fragment] = fragments;
  const start = boundary(source, fragment.owner), next = boundary(source, fragment.next);
  assert.equal(count(source, fragment.new), 1, fail + " complete catalogue append");
  const position = source.indexOf(fragment.new), freeze = boundary(source, "  deepFreeze(MESSAGES);");
  assert.ok(start < position && position < next && next < freeze, fail + " catalogue placement");
  assert.ok(source.slice(position + fragment.new.length).startsWith("\n\n  function deepFreeze(value) {"),
    fail + " immediate catalogue next boundary");
  const result = source.replace(fragment.new, () => fragment.old);
  assert.equal(marker(result), false, fail + " detached catalogue marker");
  return result;
}

export function mediaDetailCustomerCopyHistoricalSnapshot(entries, locale) {
  entries = mediaFixedFeedbackHistoricalSnapshot(entries, locale);
  const index = ["vi", "en", "zh"].indexOf(locale);
  assert.ok(index >= 0, fail + " locale");
  assert.ok(Array.isArray(entries) && entries.every(row => Array.isArray(row) && row.length === 2), fail + " entry shape");
  const additions = fixture.copyRows.filter(row => row.old === null), keys = new Set(additions.map(row => row.key));
  if (!entries.some(([key]) => keys.has(key))) {
    // A partial new catalogue must not masquerade as historical input after
    // dropping its two new keys. Distinct current reviewed values reveal it.
    assert.ok(!fixture.copyRows.some(row => row.old && row.old[index] !== row.new[index]
      && entries.some(([key, value]) => key === row.key && value === row.new[index])), fail + " partial catalogue");
    return entries;
  }
  for (const row of fixture.copyRows) {
    const matches = entries.filter(([key]) => key === row.key);
    assert.equal(matches.length, 1, fail + " complete unique reviewed row");
    assert.equal(matches[0][1], row.new[index], fail + " exact reviewed value");
  }
  const positions = additions.map(row => entries.findIndex(([key]) => key === row.key));
  assert.equal(positions[1], positions[0] + 1, fail + " ordered consecutive additions");
  const oldPositions = fixture.copyRows.filter(row => row.old).map(row => entries.findIndex(([key]) => key === row.key));
  assert.ok(positions[0] > Math.max(...oldPositions), fail + " additions after existing keys");
  const old = new Map(fixture.copyRows.filter(row => row.old).map(row => [row.key, row.old[index]]));
  return entries.filter(([key]) => !keys.has(key)).map(row => old.has(row[0]) ? [row[0], old.get(row[0])] : row);
}
