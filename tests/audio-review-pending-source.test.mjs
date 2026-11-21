import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {audioReviewPendingHistoricalSource as historical} from "./helpers/audio-review-pending-snapshot.mjs";
import {requiredWarningHistoricalSource} from "./helpers/portal-required-warning-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/audio-review-pending-contract.json", import.meta.url), "utf8"));
const lf = value => value.replace(/\r\n/g, "\n");

for (const file of ["static/portal/integration.js", "static/portal/portal-i18n.js"]) {
  test(`${file}: full physical source is BASE plus the exact reviewed feedback records`, () => {
    const base = lf(execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 20e6}));
    const actual = requiredWarningHistoricalSource(lf(fs.readFileSync(file, "utf8")), file);
    let expected = base;
    for (const row of contract.records.filter(item => item.file === file)) {
      assert.equal(expected.split(row.old).length - 1, 1, "Unique forward anchor");
      expected = expected.replace(row.old, () => row.new);
    }
    assert.equal(actual, expected, "Physical source must match BASE plus only these records");
    assert.equal(historical(actual, file), base, "Historical input only");
    assert.equal(historical(base, file), base);
    assert.equal(historical("/* customer */\n" + actual, file), "/* customer */\n" + base);
    for (const row of contract.records.filter(item => item.file === file)) {
      const altered = row.file.endsWith("integration.js") && row.new.includes("throw error;")
        ? row.new.replace("throw error;", "throw new Error('altered');")
        : row.new.replace("review.", "unreviewed.");
      assert.notEqual(altered, row.new);
      assert.throws(() => historical(actual.replace(row.new, () => altered), file), /Unreviewed audio review pending feedback/);
      assert.throws(() => historical(actual + "\n" + row.new, file), /Unreviewed audio review pending feedback/);
    }
  });
}
