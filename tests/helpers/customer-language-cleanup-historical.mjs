// Historical inputs only; the current customer-facing tests read raw bundles.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const fail = "Unreviewed customer language history";
const sha = value => createHash("sha256").update(value).digest("hex");
const raw = fs.readFileSync(new URL("../fixtures/customer-language-cleanup-history.json", import.meta.url), "utf8").replace(/\r\n/g, "\n");
assert.equal(sha(raw), "7b7447e638ed9f9dbf250ec4b544f7dd786758009fceb2c4c7b2746befd3dacd", fail + " fixture");
const fixture = JSON.parse(raw), locales = ["vi", "en", "zh"];
assert.equal(fixture.base_sha, "2817dd9d221e04aa45945165ae60d5838cf9d920", fail + " base");
assert.equal(fixture.records.length, 48);
assert.equal(fixture.values.length, 16);
assert.equal(new Set(fixture.values.map(row => row.key)).size, 16);
assert.equal(fixture.existing_keys, 15);
assert.deepEqual(fixture.new_keys, ["interfaceLocale.saveBlocked"]);
const files = new Set(["static/portal/portal.js", "static/portal/portal-i18n.js"]);
for (const row of fixture.records) {
  assert(files.has(row.file) && row.before.length && row.after.length, fail + " record shape");
  assert.equal(sha(row.before), row.before_sha256, fail + " before");
  assert.equal(sha(row.after), row.after_sha256, fail + " after");
}
const owned = new Map(fixture.values.map(row => [row.key, row]));
const added = new Set(fixture.new_keys);

export function customerLanguageHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source");
  if (!files.has(file)) return source;
  const ending = source.includes("\r\n") ? "\r\n" : "\n";
  const records = fixture.records.filter(row => row.file === file).map(row => ({
    before: row.before.replace(/\n/g, ending), after: row.after.replace(/\n/g, ending)
  }));
  // Older epochs and arbitrary older subsets have no new owned record.
  // A partly changed new epoch still activates all exact-record checks.
  if (!records.some(row => source.includes(row.after) && (!row.before.includes(row.after) || !source.includes(row.before)))) return source;
  for (const {before, after} of records.reverse()) {
    assert.equal(source.split(after).length - 1, 1, fail + " missing, changed or duplicate owned record");
    source = source.replace(after, () => before);
  }
  return source;
}

export function customerLanguageHistoricalSnapshot(entries, locale) {
  assert(Array.isArray(entries) && locales.includes(locale), fail + " snapshot input");
  if (!entries.some(row => Array.isArray(row) && (row[0] === "chrome.newWorkflow" || added.has(row[0])))) return entries;
  const found = entries.filter(row => Array.isArray(row) && owned.has(row[0]));
  if (!found.some(row => added.has(row[0]))) {
    // Earlier epochs pass through unchanged to their own strict fixture.
    // A current dictionary missing only its newly added key is not earlier.
    assert(!(found.length === 15 && new Set(found.map(row => row[0])).size === 15
      && found.every(([key, value]) => value === owned.get(key).after[locale])), fail + " missing new key");
    return entries;
  }
  assert.equal(found.length, 16, fail + " incomplete values");
  assert.equal(new Set(found.map(row => row[0])).size, 16, fail + " duplicate values");
  for (const [key, value] of found) assert.equal(value, owned.get(key).after[locale], fail + " changed value");
  return entries.filter(row => !added.has(row[0])).map(row => owned.has(row[0]) ? [row[0], owned.get(row[0]).before[locale]] : row);
}
