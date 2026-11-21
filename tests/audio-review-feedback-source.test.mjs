import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {ROOT, CONTRACT, hash} from "./helpers/audio-review-feedback-runtime.mjs";
import {audioReviewVisualHistoricalSource} from "./helpers/audio-review-visual-snapshot.mjs";
import {audioReviewPendingHistoricalSource} from "./helpers/audio-review-pending-snapshot.mjs";

const lf = value => value.replace(/\r\n/g, "\n");
const fromBase = file => execFileSync("git", ["show", CONTRACT.base + ":" + file],
  {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true});
function forward(file, original) {
  let next = original;
  for (const record of CONTRACT.canonicalChanges.filter(row => row.file === file)) {
    assert.equal(record.count, 1); assert.equal(next.split(record.old).length - 1, 1,
      "One exact forward anchor in immutable BASE: " + file);
    next = next.replace(record.old, record.new);
  }
  return next;
}
function pin(raw, row) {
  const normalized = lf(raw.toString("utf8"));
  assert.equal(hash(normalized), row.baseLfSha256, "Mandatory BASE LF content: " + row.file);
  const permitted = [row.baseRawSha256, row.baseLfSha256, hash(normalized.replace(/\n/g, "\r\n"))];
  assert.ok(permitted.includes(hash(raw)), "Only measured RAW, exact LF or uniform CRLF checkout: " + row.file);
}
function exactFunction(source, name) {
  const signature = "  " + (name === "api" ? "async " : "") + "function " + name + "(";
  assert.equal(source.split(signature).length - 1, 1, "Unique whole physical function " + name);
  const start = source.indexOf(signature), end = source.indexOf("\n  }", start);
  assert.ok(end > start); return source.slice(start, end + 4);
}
test("immutable Root contract has exact BASE,11 forward records split8/2/1 and31 unique literal rows", () => {
  assert.equal(CONTRACT.base, "7cb8cb10486f5c175dca5db2c286a9f93a133c23");
  assert.equal(CONTRACT.schema, "AUDIO_REVIEW_EXPECTED_CONTRACT_V1");
  assert.equal(CONTRACT.canonicalChanges.length, 11);
  assert.deepEqual(CONTRACT.allowedFiles.map(file => CONTRACT.canonicalChanges.filter(row => row.file === file).length), [8, 2, 1]);
  assert.equal(CONTRACT.copyRows.length, 31);
  assert.equal(new Set(CONTRACT.copyRows.map(row => row.key)).size, 31);
});
for (const file of CONTRACT.allowedFiles) {
  test(`historical ARF ${file} equals full BASE plus exact Root forward records after reviewed visual projection`, () => {
    const original = lf(fromBase(file)), row = CONTRACT.applicationBaseline.find(row => row.file === file);
    assert.equal(hash(original), row.baseLfSha256, "Immutable exact BASE source");
    const expected = forward(file, original), current = audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file), file);
    assert.equal(hash(current), hash(expected), "Full current source SHA: " + file);
    assert.equal(current, expected, "Full current source content: " + file);
  });
}
test("historical ARF source pins retain exactly148 protected paths after reviewed readability projection", () => {
  assert.equal(CONTRACT.applicationBaseline.length, 151);
  assert.equal(new Set(CONTRACT.applicationBaseline.map(row => row.file)).size, 151);
  const protectedRows = CONTRACT.applicationBaseline.filter(row => !CONTRACT.allowedFiles.includes(row.file));
  assert.equal(protectedRows.length, 148);
  for (const row of protectedRows) {
    const physical = fs.readFileSync(path.join(ROOT, row.file));
    const projected = audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(lf(physical.toString("utf8")), row.file), row.file);
    pin(projected === lf(physical.toString("utf8")) ? physical : Buffer.from(projected), row);
  }
});
test("portable source pins accept exact LF and uniform CRLF, not Windows-raw-only acceptance", () => {
  const row = CONTRACT.applicationBaseline.find(row => row.file === "admin_ops.py");
  const original = lf(fromBase(row.file));
  pin(Buffer.from(original), row); pin(Buffer.from(original.replace(/\n/g, "\r\n")), row);
});
test("portable source pins reject content edits and unmeasured mixed newlines", () => {
  const row = CONTRACT.applicationBaseline.find(row => row.file === "admin_ops.py"), original = lf(fromBase(row.file));
  assert.throws(() => pin(Buffer.from(original + " "), row), assert.AssertionError);
  let mixed = original.replace("\n", "\r\n");
  if (hash(mixed) === row.baseRawSha256) mixed = original.replace(/\n(?=[^\n]*\n)/, "\r\n");
  assert.notEqual(hash(mixed), row.baseRawSha256); assert.notEqual(hash(mixed), row.baseLfSha256);
  assert.notEqual(hash(mixed), hash(original.replace(/\n/g, "\r\n")));
  assert.throws(() => pin(Buffer.from(mixed), row), assert.AssertionError);
});
test("all21 shared validation/read/classifier/API/review guards/render factories retain exact UTF8 function bytes", () => {
  assert.equal(CONTRACT.protectedFunctions.length, 21);
  assert.equal(new Set(CONTRACT.protectedFunctions.map(row => row.file + ":" + row.name)).size, 21);
  const sources = Object.fromEntries(CONTRACT.allowedFiles.map(file => [file,
    audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file), file)]));
  for (const row of CONTRACT.protectedFunctions) {
    const body = exactFunction(sources[row.file], row.name);
    assert.equal(Buffer.byteLength(body), row.bytes, row.file + ":" + row.name);
    assert.equal(hash(body), row.lfSha256, row.file + ":" + row.name);
  }
});
test("the immutable forward integration change only opts this action into known-stock error display", () => {
  const original = lf(fromBase("static/portal/integration.js")), expected = forward("static/portal/integration.js", original);
  const catchStart = expected.indexOf("      const editorialError = ");
  const end = expected.indexOf("\n    } finally {", catchStart);
  assert.ok(catchStart > 0 && end > catchStart);
  const catchSource = expected.slice(catchStart, end);
  assert.equal((catchSource.match(/audioHubReviewFeedbackText/g) || []).length, 1);
  assert.ok(catchSource.includes('toast(action === "audio-hub-review-pack-compose" ? audioHubReviewFeedbackText('));
  assert.ok(catchSource.includes('action === "publish-review-pack-compose" ? publishReviewPackFeedbackText('));
});
