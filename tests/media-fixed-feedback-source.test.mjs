import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {ROOT, hash} from "./helpers/media-fixed-feedback-runtime.mjs";
import {audioReviewHistoricalSource} from "./helpers/audio-review-snapshot.mjs";

const fixture = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/media-fixed-feedback-contract.json"), "utf8"));
const lf = text => text.replace(/\r\n/g, "\n");
const fromBase = file => execFileSync("git", ["show", fixture.base + ":" + file],
  {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true});
function forward(file, source) {
  let next = source;
  for (const edit of fixture.canonicalChanges.filter(row => row.file === file)) {
    assert.equal(edit.count, 1);
    assert.equal(next.split(edit.old).length - 1, 1, "Unique full forward anchor");
    next = next.replace(edit.old, edit.new);
  }
  return next;
}
function exactFunction(source, name) {
  const start = source.indexOf("  function " + name + "(");
  assert.ok(start >= 0); assert.equal(source.split("  function " + name + "(").length - 1, 1);
  const end = source.indexOf("\n  }", start);
  assert.ok(end > start); return source.slice(start, end + 4);
}
function assertProtectedSourceBytes(raw, row) {
  const canonical = lf(raw.toString("utf8"));
  assert.equal(hash(canonical), row.baseLfSha256, row.file);
  assert.ok([row.baseRawSha256, row.baseLfSha256, hash(canonical.replace(/\n/g, "\r\n"))].includes(hash(raw)),
    "Only measured/LF/uniformCRLF checkout:" + row.file);
}
test("historical PR786 two source inputs equal its BASE plus exact11 Root-owned forward records after reviewed ARF input projection", () => {
  assert.equal(fixture.canonicalChanges.length, 11);
  for (const file of fixture.allowedFiles) {
    const original = lf(fromBase(file)), row = fixture.applicationBaseline.find(row => row.file === file);
    assert.equal(hash(original), row.baseLfSha256);
    const current = audioReviewHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file), expected = forward(file, original);
    assert.equal(hash(current), hash(expected), file);
    assert.equal(current, expected, file);
  }
});
test("historical PR786 all149 other source inputs retain exact RAW/LF BASE and151 unique paths after reviewed ARF projection", () => {
  assert.equal(fixture.applicationBaseline.length, 151);
  assert.equal(new Set(fixture.applicationBaseline.map(row => row.file)).size, 151);
  const protectedRows = fixture.applicationBaseline.filter(row => !fixture.allowedFiles.includes(row.file));
  assert.equal(protectedRows.length, 149);
  for (const row of protectedRows) {
    const physical = fs.readFileSync(path.join(ROOT, row.file));
    const projected = audioReviewHistoricalSource(lf(physical.toString("utf8")), row.file);
    const raw = projected === lf(physical.toString("utf8")) ? physical : Buffer.from(projected);
    assertProtectedSourceBytes(raw, row);
  }
});
test("source pin portability accepts exact LF and uniform CRLF checkout bytes", () => {
  const row = fixture.applicationBaseline.find(row => row.file === "admin_ops.py");
  const text = lf(fromBase(row.file));
  assertProtectedSourceBytes(Buffer.from(text), row);
  assertProtectedSourceBytes(Buffer.from(text.replace(/\n/g, "\r\n")), row);
});
test("source pin portability rejects changed content even with a valid checkout newline style", () => {
  const row = fixture.applicationBaseline.find(row => row.file === "admin_ops.py");
  const text = lf(fromBase(row.file));
  assert.throws(() => assertProtectedSourceBytes(Buffer.from(text + " "), row), assert.AssertionError);
});
test("source pin portability rejects an unmeasured mixed-newline encoding with unchanged content", () => {
  const row = fixture.applicationBaseline.find(row => row.file === "admin_ops.py");
  const text = lf(fromBase(row.file)), mixed = text.replace("\n", "\r\n");
  assert.notEqual(hash(mixed), row.baseRawSha256);
  assert.notEqual(hash(mixed), row.baseLfSha256);
  assert.throws(() => assertProtectedSourceBytes(Buffer.from(mixed), row), assert.AssertionError);
});
test("all shared validation producers, Music/SFX classifier and existing read-feedback helper retain exact function bytes", () => {
  const source = audioReviewHistoricalSource(lf(fs.readFileSync(path.join(ROOT, "static/portal/integration.js"), "utf8")),
    "static/portal/integration.js");
  assert.equal(fixture.protectedFunctions.length, 10);
  for (const row of fixture.protectedFunctions) {
    const body = exactFunction(source, row.name);
    assert.equal(Buffer.byteLength(body), row.function_utf8_bytes, row.name);
    assert.equal(hash(body), row.function_sha256, row.name);
  }
});
