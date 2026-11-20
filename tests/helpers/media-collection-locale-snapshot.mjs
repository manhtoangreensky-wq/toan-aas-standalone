import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";

const raw = fs.readFileSync(new URL("../fixtures/media-collection-locale-reviewed.json", import.meta.url));
const fail = "Unreviewed media collection locale", count = (value, part) => value.split(part).length - 1;
assert.equal(createHash("sha256").update(raw).digest("hex"),
  "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515", fail);
const fixture = JSON.parse(raw);
const baselineRaw = fs.readFileSync(new URL("../fixtures/media-collection-baseline-copy-reviewed.json", import.meta.url));
assert.equal(createHash("sha256").update(baselineRaw).digest("hex"),
  "03e14f63b5a9018f9ff948c2a4e39153ec25fc3dc8388bbff186e351175423a9", fail);
const baseline = JSON.parse(baselineRaw);
assert.equal(baseline.parentFixtureRawSha256,
  "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515", fail);
assert.equal(baseline.baseRows.length, 31, fail); assert.equal(baseline.newKeys.length, 7, fail);
assert.equal(fixture.task, "MEDIA-COLLECTION-LOCALE-20261120", fail);
assert.equal(fixture.base, "4080b879ad8d6ded081aa47313bf9cac67121f0b", fail);
assert.equal(fixture.canonicalChanges.length, 8, fail);
assert.equal(fixture.historicalFragments.length, 6, fail);
assert.equal(fixture.parentFixtureRawSha256,
  "9faedb1fe8c1aff3d456a658f82dd107a4d4fab7690c51eb071b1d93dc53edee", fail);
const markers = ["vi", "en", "zh"].map(locale =>
  "  Object.assign(MESSAGES." + locale + ', {"audioWorkspace.defaults.context":');

// Finite historical input projection only. Current acceptance independently
// compares complete physical files with the exact eight-record candidate and151 pins.
export function mediaCollectionHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  for (const group of fixture.historicalFragments.filter(row => row.file === file)) {
    if (file.endsWith("/portal.js")) {
      if (!source.includes(group.owner) && !source.includes(group.next)) continue;
      assert.equal(count(source, group.owner), 1, fail + " owner");
      assert.equal(count(source, group.next), 1, fail + " next owner");
      const start = source.indexOf(group.owner), end = source.indexOf(group.next, start);
      assert.ok(end > start, fail + " owner order");
      const body = source.slice(start, end);
      if (body === group.old) continue;
      assert.equal(body, group.new, fail + " exact function");
      assert.equal(count(source, group.new), 1, fail + " unique function");
      source = source.replace(group.new, () => group.old);
    } else {
      const hasNew = markers.some(marker => source.includes(marker))
        || source.includes('"audioWorkspace.defaults.context"')
        || source.includes('"audioWorkspace.pagination.range"');
      if (!hasNew && !source.includes(group.old)) continue;
      assert.equal(count(source, group.owner), 1, fail + " catalogue owner");
      assert.equal(count(source, group.next), 1, fail + " catalogue next");
      const start = source.indexOf(group.owner), end = source.indexOf(group.next, start);
      assert.ok(end > start, fail + " catalogue order");
      if (!hasNew) {
        assert.equal(count(source, group.old), 1, fail + " old catalogue"); continue;
      }
      for (const marker of markers) assert.equal(count(source, marker), 1, fail + " catalogue marker");
      assert.equal(count(source, group.new), 1, fail + " exact catalogue");
      const position = source.indexOf(group.new);
      assert.ok(position > start && position < end, fail + " catalogue placement");
      const freeze = "  deepFreeze(MESSAGES);";
      assert.equal(count(source, freeze), 1, fail + " freeze boundary");
      assert.ok(end < source.indexOf(freeze), fail + " catalogue before freeze");
      source = source.replace(group.new, () => group.old);
    }
  }
  return source;
}

// Entry-level companion for old full-catalogue goldens. The exact current38
// values must be present before restoring31 old values and removing7 additions.
export function mediaCollectionHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0 && Array.isArray(entries), fail + " snapshot input");
  assert.ok(entries.every(entry => Array.isArray(entry) && entry.length === 2), fail + " snapshot shape");
  const added = new Set(baseline.newKeys);
  if (!entries.some(([key]) => added.has(key))) return entries;
  const expected = fixture.copyRows.map(row => ["audioWorkspace." + row[0], row[index]]);
  for (const [key, value] of expected) {
    const matches = entries.filter(entry => entry[0] === key);
    assert.equal(matches.length, 1, fail + " complete unique snapshot");
    assert.equal(matches[0][1], value, fail + " exact snapshot value");
  }
  const positions = baseline.newKeys.map(key => entries.findIndex(entry => entry[0] === key));
  assert.ok(positions.every((position, offset) => position === positions[0] + offset), fail + " addition order");
  const oldPositions = baseline.baseRows.map(row => entries.findIndex(entry => entry[0] === row[0]));
  assert.ok(positions[0] > Math.max(...oldPositions), fail + " addition placement");
  const old = new Map(baseline.baseRows.map(row => [row[0], row[index]]));
  return entries.filter(([key]) => !added.has(key)).map(entry =>
    old.has(entry[0]) ? [entry[0], old.get(entry[0])] : entry);
}
