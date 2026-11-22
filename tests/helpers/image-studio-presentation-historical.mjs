import assert from "node:assert/strict";
import fs from "node:fs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-presentation-contract.json", import.meta.url)));
const fail = "Unreviewed Image Studio presentation";
const line = row => "    [" + row.map(value => JSON.stringify(value)).join(", ") + "],";
const count = (source, value) => source.split(value).length - 1;
assert.equal(contract.base, "07a89b79c442981ecb7433b607c981740c95c774", fail);
assert.equal(contract.copy.length, 19, fail);
assert.equal(contract.otherRecords.length, 4, fail);

// Finite input inverse for older assertions only. Current acceptance reads the
// physical files and checks all 23 forward records independently.
export function imageStudioPresentationHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  if (file === "static/portal/portal-i18n.js") {
    if (!source.includes(line(contract.copy[0][2]))) return source;
    for (const [, , next] of contract.copy) assert.equal(count(source, line(next)), 1, fail);
    for (const [, old, next] of contract.copy) source = source.replace(line(next), () => line(old));
  } else if (file === "static/portal/portal.js") {
    if (!source.includes("  function renderImageStudioBoundary() {") || count(source, "renderImageStudioBoundary()") === 3) return source;
    assert.equal(count(source, "renderImageStudioBoundary()"), 1, fail);
    const create = '</button></div></form></section></div>\n      ${imageHub ? renderImageHubNextSteps() : ""}';
    const detail = '    </article>`;\n  }\n\n  // AI Chat Workspace';
    assert.equal(count(source, create), 1, fail);
    assert.equal(count(source, detail), 1, fail);
    source = source.replace(create, () => create.replace("</section></div>", "</section>${renderImageStudioBoundary()}</div>"));
    source = source.replace(detail, () => "      ${renderImageStudioBoundary()}\n" + detail);
  } else if (file === "static/portal/portal-theme.css") {
    const records = contract.otherRecords.filter(row => row.file === file);
    if (!records.some(row => source.includes(row.new))) return source;
    for (const row of records) assert.equal(count(source, row.new), 1, fail);
    for (const row of records) source = source.replace(row.new, () => row.old);
  }
  return source;
}

export function imageStudioPresentationHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(Array.isArray(entries) && index > 0, fail);
  const first = entries.find(([key]) => key === contract.copy[0][0] + contract.copy[0][2][0]);
  if (!first || first[1] !== contract.copy[0][2][index]) return entries;
  for (const [prefix, , next] of contract.copy) {
    const found = entries.filter(([key]) => key === prefix + next[0]);
    assert.equal(found.length, 1, fail);
    assert.equal(found[0][1], next[index], fail);
  }
  return entries.map(row => {
    const old = contract.copy.find(([prefix, value]) => row[0] === prefix + value[0]);
    return old ? [row[0], old[1][index]] : row;
  });
}
