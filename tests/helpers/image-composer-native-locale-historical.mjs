import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-composer-native-locale-contract.json", import.meta.url), "utf8"));
assert.equal(contract.base, "6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792");
assert.equal(contract.records.length, 39);
const changes = [...contract.records, ...(contract.amendments || [])];
assert.equal(contract.copyRows.length, 85);
const additions = new Map(contract.copyRows.map(row => ["imageComposerUi." + row[0], row]));
const feedbackCopy = JSON.parse(fs.readFileSync(new URL("../fixtures/image-composer-feedback-copy.json", import.meta.url), "utf8")).rows;
const feedbackAdditions = new Map(feedbackCopy.map(row => ["imageComposerFeedbackUi." + row.key, row]));
const nav = new Map();
for (const row of contract.records.filter(row => row.file.endsWith("portal-i18n.js") && row.old.startsWith('      "'))) {
  const parse = text => Object.entries(JSON.parse("{" + text.trim().replace(/,$/, "") + "}"))[0];
  const [key, old] = parse(row.old), [newKey, next] = parse(row.new);
  assert.equal(newKey, key);
  if (!nav.has(key)) nav.set(key, []);
  nav.get(key).push({old, next});
}
assert.equal(nav.size, 2);
for (const rows of nav.values()) assert.equal(rows.length, 3);

export function imageComposerNativeLocaleHistoricalSource(source, file) {
  const records = changes.filter(row => row.file === file);
  if (!records.some(row => source.includes(row.new))) return source;
  for (const row of [...records].reverse()) {
    assert.equal(source.split(row.new).length - 1, 1, "Unreviewed Composer locale source");
    source = source.replace(row.new, () => row.old);
  }
  return source;
}

export function imageComposerNativeLocaleHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale);
  assert(index >= 0 && Array.isArray(entries));
  const feedback = entries.filter(([key]) => feedbackAdditions.has(key));
  if (feedback.length) {
    assert.equal(feedback.length, 15, "Partial Composer feedback dictionary");
    assert.equal(new Set(feedback.map(([key]) => key)).size, 15, "Duplicate Composer feedback dictionary");
    for (const [key, value] of feedback) assert.equal(value, feedbackAdditions.get(key)[locale], "Unreviewed Composer feedback value");
    entries = entries.filter(([key]) => !feedbackAdditions.has(key));
  }
  const recognized = entries.filter(([key]) => additions.has(key));
  if (!recognized.length) return entries;
  assert.equal(recognized.length, 85, "Partial Composer dictionary");
  assert.equal(new Set(recognized.map(([key]) => key)).size, 85, "Duplicate Composer dictionary");
  for (const [key, value] of recognized) assert.equal(value, additions.get(key)[index + 1], "Unreviewed Composer dictionary");
  for (const [key, rows] of nav) {
    const found = entries.filter(([name]) => name === key);
    assert.equal(found.length, 1, "Missing Composer navigation label");
    assert.equal(found[0][1], rows[index].next, "Unreviewed Composer navigation label");
  }
  return entries.filter(([key]) => !additions.has(key))
    .map(([key, value]) => [key, nav.has(key) ? nav.get(key)[index].old : value]);
}
