import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-root-heading-contract.json", import.meta.url)));
assert.equal(contract.base, "3d21e950fb8e676ffd0b8c945a5ff6d9c8425736");
assert.equal(contract.records.length, 1);
const [record] = contract.records;

export function imageStudioRootHeadingHistoricalSource(source, file) {
  if (file !== record.file || !source.includes(record.new)) return source;
  assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Image root heading CSS");
  return source.replace(record.new, () => record.old);
}
