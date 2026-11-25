import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/free-tools-readable-colors-contract.json", import.meta.url), "utf8"));
assert.equal(contract.base, "a8cf07490448548a2a1be6800fb7e146abeac726");
assert.equal(contract.records.length, 9);

export function freeToolsReadableColorsHistoricalSource(source, file) {
  const records = contract.records.filter(record => record.file === file);
  if (!records.some(record => source.includes(record.new))) return source;
  for (const record of [...records].reverse()) {
    assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Free Tools color source");
    source = source.replace(record.new, () => record.old);
  }
  return source;
}
