import assert from "node:assert/strict";
import fs from "node:fs";
import {imageStudioDetailDraftHistoricalSource} from "./image-studio-detail-draft-historical.mjs";
import {imageStudioLocaleCopyHistoricalSource} from "./image-studio-locale-copy-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-detail-loading-contract.json", import.meta.url)));
assert.equal(contract.base, "e177ce5f5791fd22e517d95706331051223e0ccb");
assert.equal(contract.records.length, 3);

export function imageStudioDetailLoadingHistoricalSource(source, file) {
  source = imageStudioLocaleCopyHistoricalSource(source, file);
  source = imageStudioDetailDraftHistoricalSource(source, file);
  const record = contract.records.find(row => row.file === file);
  if (!record) return source;
  const count = source.split(record.new).length - 1;
  if (!count) return source;
  assert.equal(count, 1, "Unreviewed Image Studio detail loading");
  assert.equal(source.replace(record.new, "").split(record.old).length - 1, 0, "Mixed Image Studio detail loading");
  return source.replace(record.new, () => record.old);
}
