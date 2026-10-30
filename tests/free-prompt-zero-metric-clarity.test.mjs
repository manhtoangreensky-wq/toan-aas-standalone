import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderFreePromptGallery(page, context)");
assert.ok(start >= 0, "Free Prompt Gallery renderer must remain present");
const end = source.indexOf("\n  function ", start + 10);

test("Free Prompt Gallery intro keeps real counts without zero-only execution metric", () => {
  const renderer = source.slice(start, end);
  assert.doesNotMatch(renderer, /intro\.stat\.execution|<dt>0<\/dt>/);
  assert.match(renderer, /intro\.stat\.categories/);
  assert.match(renderer, /intro\.stat\.industries/);
});
