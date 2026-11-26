import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/native-label-recovery-contract.json", import.meta.url), "utf8"));
assert.equal(contract.base, "1a57e62152855b1cff39956d43ad0ccfd5f3d5cb");
assert.equal(contract.records.length, 8);
const dictionary = new Map(contract.dictionaryRows.map(row => [row[0], row]));
const changes = [...contract.records, ...(contract.amendments || [])];

export function nativeLabelRecoveryHistoricalSource(source, file) {
  const records = changes.filter(row => row.file === file);
  if (!records.some(row => source.includes(row.new))) return source;
  for (const row of [...records].reverse()) {
    assert.equal(source.split(row.new).length - 1, 1, "Unreviewed native label recovery source");
    source = source.replace(row.new, () => row.old);
  }
  return source;
}

export function nativeLabelRecoveryHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale);
  assert(index >= 0 && Array.isArray(entries));
  const additions = entries.filter(([key]) => dictionary.has(key));
  if (!additions.length) return entries;
  assert.equal(additions.length, 14, "Partial native label dictionary");
  assert.equal(new Set(additions.map(([key]) => key)).size, 14, "Duplicate native label dictionary");
  for (const [key, value] of additions) assert.equal(value, dictionary.get(key)[index + 1], "Unreviewed native label copy");
  return entries.filter(([key]) => !dictionary.has(key));
}
