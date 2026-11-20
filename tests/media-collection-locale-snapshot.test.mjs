import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {sources, runtime, hash} from "./helpers/media-collection-locale-runtime.mjs";
import {mediaCollectionHistoricalSnapshot as inverse} from "./helpers/media-collection-locale-snapshot.mjs";

const raw = fs.readFileSync(new URL("./fixtures/media-collection-baseline-copy-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), before = runtime(sources({baseline: true})).messages;
const current = runtime(sources()).messages, locales = ["vi", "en", "zh"], fail = /Unreviewed media collection locale/;
test("31 immutable old copy rows are bound to actual complete BASE i18n and main reviewed authority", () => {
  assert.equal(hash(raw), "03e14f63b5a9018f9ff948c2a4e39153ec25fc3dc8388bbff186e351175423a9");
  assert.equal(fixture.base, "4080b879ad8d6ded081aa47313bf9cac67121f0b");
  assert.equal(fixture.baseI18nLfSha256, "768b1ba4102ed67b387ba4f62b98009cbcd82fb76decdc1992365aa84393aed2");
  assert.equal(fixture.baseRows.length, 31); assert.equal(new Set(fixture.baseRows.map(row => row[0])).size, 31);
  assert.equal(fixture.newKeys.length, 7); assert.equal(new Set(fixture.newKeys).size, 7);
  for (const [index, locale] of locales.entries()) {
    for (const row of fixture.baseRows) assert.equal(row[index + 1], before[locale][row[0]], row[0]);
    for (const key of fixture.newKeys) assert.equal(Object.hasOwn(before[locale], key), false);
  }
});
for (const locale of locales) {
  const now = Object.entries(current[locale]), base = Object.entries(before[locale]);
  const oldKey = fixture.baseRows[0][0], newKey = fixture.newKeys[0];
  test(locale + ": exact current catalogue restores only38 reviewed keys to full BASE with order retained", () => {
    assert.deepEqual(inverse(now, locale), base); assert.deepEqual(inverse(base, locale), base);
    assert.deepEqual(inverse(inverse(now, locale), locale), base);
  });
  test(locale + ": unknown/customer entries before and after remain unchanged and input is immutable", () => {
    const first = ["customer.Facebook", 'media studio <img>& "literal"'], last = ["unknown.outside", {literal: "TikTok"}];
    const input = [first, ...now.map(entry => Object.freeze([...entry])), last];
    const snapshot = JSON.stringify(input); Object.freeze(input);
    assert.deepEqual(inverse(input, locale), [first, ...base, last]); assert.equal(JSON.stringify(input), snapshot);
  });
  for (const [kind, mutate] of [
    ["missing addition", entries => entries.filter(([key]) => key !== newKey)],
    ["changed old row", entries => entries.map(entry => entry[0] === oldKey ? [oldKey, "UNKNOWN"] : entry)],
    ["changed new row", entries => entries.map(entry => entry[0] === newKey ? [newKey, "UNKNOWN"] : entry)],
    ["duplicate row", entries => [...entries, entries.find(([key]) => key === oldKey)]],
    ["reordered additions", entries => { const value = [...entries], at = value.findIndex(([key]) => key === newKey);
      [value[at], value[at + 1]] = [value[at + 1], value[at]]; return value; }],
    ["detached addition", entries => [entries.find(([key]) => key === newKey), ...entries.filter(([key]) => key !== newKey)]]
  ]) test(locale + ": historical snapshot rejects " + kind, () => {
    assert.throws(() => inverse(mutate(now), locale), fail);
  });
}
test("historical snapshot retains strict locale, entry shape and array types", () => {
  for (const value of [null, undefined, 1, {}, ["bad"], [["key"]]]) assert.throws(() => inverse(value, "vi"), fail);
  assert.throws(() => inverse([], "unknown"), fail);
});
