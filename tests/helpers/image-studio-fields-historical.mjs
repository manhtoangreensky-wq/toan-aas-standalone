import assert from "node:assert/strict";
import fs from "node:fs";
import {imageStudioOptionsHistoricalSource, imageStudioOptionsHistoricalSnapshot} from "./image-studio-options-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-create-fields-contract.json", import.meta.url)));
const fail = "Unreviewed Image Studio field copy";
assert.equal(contract.base, "05b7ba761bd35cf4da498443db9046ed59429d90", fail);
assert.equal(contract.records.length, 2, fail);
assert.equal(contract.rows.length, 18, fail);

export function imageStudioFieldsHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  source = imageStudioOptionsHistoricalSource(source, file);
  const record = contract.records.find(row => row.file === file);
  if (!record || !source.includes(file.endsWith("portal.js") ? 'imageStudioText("form.' : "IMAGE_STUDIO_FORM_COPY_ROWS")) return source;
  assert.equal(source.split(record.new).length - 1, 1, fail);
  const at = source.indexOf(record.new);
  const start = source.indexOf(file.endsWith("portal.js") ? "  function imageStudioArtboardFields(context) {" : "  const IMAGE_STUDIO_COPY_ROWS = [");
  const end = source.indexOf(file.endsWith("portal.js") ? "  function imageStudioArtboardValues(value) {" : "  const IMAGE_STUDIO_LIBRARY_COPY_ROWS = [");
  assert.ok(start >= 0 && start <= at && at < end, fail);
  return source.replace(record.new, () => record.old);
}

export function imageStudioFieldsHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(Array.isArray(entries) && index > 0, fail);
  entries = imageStudioOptionsHistoricalSnapshot(entries, locale);
  const keys = contract.rows.map(row => row[0]);
  const found = entries.filter(([key]) => typeof key === "string" && key.startsWith("imageStudioUi.form."));
  if (!found.length) return entries;
  assert.deepEqual(found.map(([key]) => key), keys, fail);
  for (const row of contract.rows) assert.equal(found.find(([key]) => key === row[0])[1], row[index], fail);
  return entries.filter(([key]) => !keys.includes(key));
}
