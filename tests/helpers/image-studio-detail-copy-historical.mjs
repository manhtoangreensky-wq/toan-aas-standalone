import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-detail-customer-copy-contract.json", import.meta.url)));
const fail = "Unreviewed Image Studio detail copy";
assert.equal(contract.base, "f6aee803a72a80bf70cd0a4ce786858f94f9d7cc", fail);
assert.equal(contract.records.length, 22, fail);
const rows = contract.records.filter(row => row.file.endsWith("portal-i18n.js")).map(row => ({
  old: JSON.parse(row.old.trim().replace(/,$/, "")),
  next: JSON.parse(row.new.trim().replace(/,$/, ""))
}));
assert.equal(rows.length, 21, fail);

export function imageStudioDetailCopyHistoricalSource(source, file) {
  const records = contract.records.filter(row => row.file === file);
  if (!records.length || !source.includes(records[0].new)) return source;
  for (const row of records) assert.equal(source.split(row.new).length - 1, 1, fail);
  for (const row of [...records].reverse()) source = source.replace(row.new, () => row.old);
  return source;
}

export function imageStudioDetailCopyHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(Array.isArray(entries) && index > 0, fail);
  const marker = entries.find(([key]) => key === "imageStudioDetailUi." + rows[0].next[0]);
  if (!marker || marker[1] !== rows[0].next[index]) return entries;
  for (const row of rows) {
    const found = entries.filter(([key]) => key === "imageStudioDetailUi." + row.next[0]);
    assert.equal(found.length, 1, fail);
    assert.equal(found[0][1], row.next[index], fail);
  }
  return entries.map(entry => {
    const row = rows.find(item => entry[0] === "imageStudioDetailUi." + item.next[0]);
    return row ? [entry[0], row.old[index]] : entry;
  });
}
