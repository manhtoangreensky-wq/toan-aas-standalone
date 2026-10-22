import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("Image utility guard chips are hidden while the actionable state remains", () => {
  const block = css.match(/\.portal-page:is\(\s*\.portal-image-background-cleanup,\s*\.portal-image-operation-history,\s*\.portal-image-brand-overlay,\s*\.portal-storyboard-grid,\s*\.portal-image-resize,\s*\.portal-image-enhance\s*\) \.portal-state-meta\s*\{\s*display:\s*none;\s*\}/s)?.[0];
  assert.ok(block, "image utility selector block must be scoped");
  for (const className of ["portal-image-background-cleanup", "portal-image-operation-history", "portal-image-brand-overlay", "portal-storyboard-grid", "portal-image-resize", "portal-image-enhance"]) assert.match(block, new RegExp(`\\.${className}`));
  assert.doesNotMatch(css, /portal-image-[^}]+background:\s*(?:#000|black)/i);
});
