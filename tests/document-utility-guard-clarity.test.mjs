import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("Document/PDF utility guard chips are hidden route-by-route", () => {
  const block = css.match(/\.portal-page:is\(\s*\.portal-document-hub,\s*\.portal-pdf-split,\s*\.portal-pdf-merge,\s*\.portal-pdf-optimize,\s*\.portal-pdf-to-images,\s*\.portal-pdf-to-word,\s*\.portal-image-ocr,\s*\.portal-pdf-ocr,\s*\.portal-pdf-ocr-to-word,\s*\.portal-image-to-pdf\s*\) \.portal-state-meta\s*\{\s*display:\s*none;\s*\}/s)?.[0];
  assert.ok(block, "document utility selector block must be scoped");
  for (const className of ["portal-document-hub", "portal-pdf-split", "portal-pdf-merge", "portal-pdf-optimize", "portal-pdf-to-images", "portal-pdf-to-word", "portal-image-ocr", "portal-pdf-ocr", "portal-pdf-ocr-to-word", "portal-image-to-pdf"]) assert.match(block, new RegExp(`\\.${className}`));
});
