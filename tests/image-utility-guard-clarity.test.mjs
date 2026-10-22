import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("Image utility guard chips are hidden while the actionable state remains", () => {
  for (const className of [
    "portal-image-background-cleanup",
    "portal-image-operation-history",
    "portal-image-brand-overlay",
    "portal-storyboard-grid",
    "portal-image-resize",
    "portal-image-enhance"
  ]) assert.match(css, new RegExp(`\\.${className}[\\s\\S]*?\\.portal-state-meta`));
  assert.match(css, /\.portal-state-meta\s*\{\s*display:\s*none;\s*\}/);
  assert.doesNotMatch(css, /portal-image-[^}]+background:\s*(?:#000|black)/i);
});
