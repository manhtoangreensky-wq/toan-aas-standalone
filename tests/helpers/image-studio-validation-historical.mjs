import assert from "node:assert/strict";
import fs from "node:fs";
import {freeToolsReadableColorsHistoricalSource, upstreamRealtimeBannerHistoricalSource, upstreamRealtimeProtectedHistoricalSource} from "./free-tools-readable-colors-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-validation-contract.json", import.meta.url), "utf8"));
assert.equal(contract.records.length, 30);
const scopes = new Map([
  ['"Ý định Image Studio không hợp lệ."', "imageArtboardPayload"],
  ['"Loại biến thể Image Studio không hợp lệ."', "imageDirectionPayload"]
]);

export function imageStudioValidationHistoricalSource(source, file) {
  source = upstreamRealtimeProtectedHistoricalSource(source, file);
  source = upstreamRealtimeBannerHistoricalSource(source, file);
  source = freeToolsReadableColorsHistoricalSource(source, file);
  const records = contract.records.filter(row => row.file === file);
  if (!records.some(row => source.includes(row.new))) return source;
  for (const record of [...records].reverse()) {
    const scope = scopes.get(record.old);
    if (scope) {
      const start = source.indexOf("  function " + scope + "("), end = source.indexOf("\n  }", start) + 4;
      assert.ok(start >= 0 && end > start, "Missing Image validation function scope");
      const body = source.slice(start, end);
      assert.equal(body.split(record.new).length - 1, 1, "Unreviewed scoped Image validation source");
      source = source.slice(0, start) + body.replace(record.new, () => record.old) + source.slice(end);
    } else {
      assert.equal(source.split(record.new).length - 1, 1, "Unreviewed Image validation source");
      source = source.replace(record.new, () => record.old);
    }
  }
  return source;
}

const catalogue = contract.records.find(row => row.file.endsWith("portal-i18n.js")).new;
const rows = catalogue.split("  const IMAGE_STUDIO_VALIDATION_COPY_ROWS = [\n")[1].split("\n  ];")[0]
  .split("\n").map(line => JSON.parse(line.trim().replace(/,$/, "")));
assert.equal(rows.length, 51);
const additions = new Map(rows.map(row => ["imageStudioValidationUi." + row[0], row]));

export function imageStudioValidationHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0 && Array.isArray(entries));
  const recognized = entries.filter(([key]) => additions.has(key));
  if (!recognized.length) return entries;
  assert.equal(recognized.length, 51, "Partial Image validation dictionary");
  assert.equal(new Set(recognized.map(([key]) => key)).size, 51, "Duplicate Image validation dictionary");
  return entries.filter(([key, value]) => {
    if (!additions.has(key)) return true;
    assert.equal(value, additions.get(key)[index], "Unreviewed Image validation value");
    return false;
  });
}
