import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {nativeLabelRecoveryHistoricalSource, nativeLabelRecoveryHistoricalSnapshot} from "./helpers/native-label-recovery-historical.mjs";
import {featureCatalogFullBundle135HistoricalSource} from "./helpers/feature-catalog-full-bundle135-historical.mjs";

const root = new URL("../", import.meta.url);
const read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const contract = JSON.parse(read("tests/fixtures/native-label-recovery-contract.json"));
const hash = value => createHash("sha256").update(value).digest("hex");
for (const pin of contract.applicationSources) {
  const before = execFileSync("git", ["show", contract.base + ":" + pin.file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
  const records = [...contract.records, ...(contract.amendments || [])].filter(row => row.file === pin.file);
  let expected = before;
  for (const row of records) {
    assert.equal(expected.split(row.old).length - 1, 1);
    expected = expected.replace(row.old, () => row.new);
  }
  test(`historical source before FBC contains only the original native-label records: ${pin.file}`, () => {
    assert.equal(hash(before), pin.beforeLfSha256);
    assert.equal(hash(expected), pin.afterLfSha256);
    assert.equal(featureCatalogFullBundle135HistoricalSource(read(pin.file),pin.file), expected);
  });
  test(`native-label inverse preserves unknown edits and rejects duplicates/partial application: ${pin.file}`, () => {
    const project = source => nativeLabelRecoveryHistoricalSource(source, pin.file);
    assert.equal(project(before), before);
    assert.equal(project(expected), before);
    assert.equal(project("/* unknown */\n" + expected + "\n/* tail */"), "/* unknown */\n" + before + "\n/* tail */");
    const unknown = text => text.replace("\n", "\n/* unknown internal */\n");
    assert.equal(project(unknown(expected)), unknown(before));
    assert.equal(nativeLabelRecoveryHistoricalSource(expected, "customer/other.js"), expected);
    assert.throws(() => project(expected + records.at(-1).new));
    const visible = [...records].reverse().find(row => expected.includes(row.new)); assert(visible);
    const mutated = expected.replace(visible.new, () => visible.new + "/* unreviewed */");
    let caught = false;
    try {caught = project(mutated) !== before;} catch (error) {assert.match(error.message, /Unreviewed native label recovery/); caught = true;}
    assert(caught);
    if (records.length > 1) assert.throws(() => project(expected.replace(visible.new, () => visible.old)));
  });
}
for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: dictionary inverse removes only14 reviewed keys and preserves arbitrary customer entries`, () => {
    const additions = contract.dictionaryRows.map(row => [row[0], row[index + 1]]);
    const unknown = ["customer.unknown", "Facebook TikTok media studio"];
    assert.deepEqual(nativeLabelRecoveryHistoricalSnapshot([...additions, unknown], locale), [unknown]);
    assert.deepEqual(nativeLabelRecoveryHistoricalSnapshot([unknown], locale), [unknown]);
    assert.throws(() => nativeLabelRecoveryHistoricalSnapshot(additions.slice(1), locale));
    assert.throws(() => nativeLabelRecoveryHistoricalSnapshot([...additions, additions[0]], locale));
    assert.throws(() => nativeLabelRecoveryHistoricalSnapshot(additions.map(([key, value], n) => [key, n === 0 ? "UNREVIEWED" : value]), locale));
  });
}
