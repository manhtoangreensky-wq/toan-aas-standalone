import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("function renderImageStudioBoundary");
const end = source.indexOf("\n  function ", start + 10);
assert.ok(start >= 0 && end > start, "Image Studio boundary renderer must remain present");

test("Image Studio boundary uses one capability explanation", () => {
  const renderer = source.slice(start, end);
  assert.match(renderer, /portal-image-studio-guard-list/);
  assert.match(renderer, /boundary\.summary/);
  assert.doesNotMatch(renderer, /boundary\.provider.*boundary\.image.*boundary\.job.*boundary\.wallet/s);
});
