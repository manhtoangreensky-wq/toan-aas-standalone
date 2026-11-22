import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-locale-copy-contract.json", import.meta.url)));
assert.equal(contract.base, "d165bad407a51a8cf6339b019a073f8a1a1eb37a");
assert.equal(contract.records.length, 32);

export function imageStudioLocaleCopyHistoricalSource(source, file) {
  const records = contract.records.filter(row => row.file === file);
  if (!records.length || !source.includes(records[0].new)) return source;
  for (const record of [...records].reverse()) {
    assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Image locale source");
    source = source.replace(record.new, () => record.old);
  }
  return source;
}

const changedLibrary = contract.records.filter(row => row.file.endsWith("portal-i18n.js") && row.old.trim().startsWith("[") && !row.old.includes('"page.newTitle"'))
  .map(row => ({old: JSON.parse(row.old.trim().replace(/,$/, "")), next: JSON.parse(row.new.trim().replace(/,$/, ""))}));
const detailRows = [
  ...contract.records.find(row => row.file.endsWith("portal-i18n.js") && row.old.includes('"page.newTitle"')).new.trim().split("\n").slice(0, -1),
  ...contract.records.find(row => row.file.endsWith("portal-i18n.js") && row.old.startsWith("  const IMAGE_STUDIO_DETAIL_COPY_ROWS")).new.trim().split("\n").slice(1)
].map(row => JSON.parse(row.trim().replace(/,$/, "")));

export function imageStudioLocaleCopyHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0 && Array.isArray(entries));
  const library = new Map(changedLibrary.map(row => ["imageStudioLibraryUi." + row.next[0], row]));
  const added = new Map(detailRows.map(row => ["imageStudioDetailUi." + row[0], row]));
  const recognized = entries.filter(([key]) => library.has(key) || added.has(key));
  if (!recognized.some(([key, value]) => added.has(key) || value === library.get(key)?.next[index])) return entries;
  const output = [];
  for (const entry of entries) {
    const [key, value] = entry;
    if (added.has(key)) {assert.equal(value, added.get(key)[index], "Unreviewed Image locale key"); continue;}
    if (library.has(key)) {
      const row = library.get(key);
      assert.equal(value, row.next[index], "Unreviewed Image library copy");
      output.push([key, row.old[index]]);
    } else output.push(entry);
  }
  return output;
}
