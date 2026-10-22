import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const portal = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");
const start = portal.indexOf("  function renderSubDubHub(page, context)");
const end = portal.indexOf("\n  function renderDocumentHub", start);
assert.ok(start >= 0 && end > start, "SubDub renderer boundary must remain present");

test("SubDub Smart Multi does not show an empty speaker-map box", () => {
  const renderer = portal.slice(start, end);
  assert.match(renderer, /data-subdub-speaker-map/);
  assert.match(renderer, /data-status="guarded"/);
  assert.doesNotMatch(renderer, /voiceLaneSmartMulti\).*voiceLaneGuarded/);
  assert.match(css, /\.portal-subdub-speaker-map\[data-status="guarded"\]\s*\{\s*display:\s*none;/);
});
