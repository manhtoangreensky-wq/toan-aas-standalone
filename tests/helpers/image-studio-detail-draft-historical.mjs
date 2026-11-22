import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-detail-draft-contract.json", import.meta.url)));
assert.equal(contract.base, "e177ce5f5791fd22e517d95706331051223e0ccb");
assert.equal(contract.records.length, 1);

export function imageStudioDetailDraftHistoricalSource(source, file) {
  const record = contract.records[0];
  if (record.file !== file || !source.includes(record.new)) return source;
  assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Image detail form preservation");
  return source.replace(record.new, () => record.old);
}
