import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {imageStudioRootHeadingHistoricalSource} from "./helpers/image-studio-root-heading-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/image-studio-root-heading-contract.json", import.meta.url)));
const [record] = contract.records;
const base = execFileSync("git", ["show", contract.base + ":" + record.file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const expected = base.replace(record.old, () => record.new);
const current = fs.readFileSync(new URL("../" + record.file, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const hash = value => createHash("sha256").update(value).digest("hex");

test("physical root heading CSS is exactly BASE plus the one reviewed light-selector extension", () => {
  assert.equal(base.split(record.old).length - 1, 1);
  assert.equal(hash(current), hash(expected));
});

test("finite heading CSS projection preserves unknown changes and rejects duplicate reviewed rules", () => {
  assert.equal(imageStudioRootHeadingHistoricalSource(expected, record.file), base);
  assert.equal(imageStudioRootHeadingHistoricalSource(base, record.file), base);
  assert.equal(imageStudioRootHeadingHistoricalSource(expected + "\n/* unknown */", record.file), base + "\n/* unknown */");
  assert.equal(imageStudioRootHeadingHistoricalSource(expected, "static/portal/portal.js"), expected);
  assert.throws(() => imageStudioRootHeadingHistoricalSource(expected + record.new, record.file));
});
