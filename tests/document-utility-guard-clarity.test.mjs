import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("Document/PDF utility guard chips are hidden route-by-route", () => {
  for (const className of [
    "portal-document-hub",
    "portal-pdf-split",
    "portal-pdf-merge",
    "portal-pdf-optimize",
    "portal-pdf-to-images",
    "portal-pdf-to-word",
    "portal-image-ocr",
    "portal-pdf-ocr",
    "portal-pdf-ocr-to-word",
    "portal-image-to-pdf"
  ]) assert.match(css, new RegExp(`\\.${className}[\\s\\S]*?\\.portal-state-meta`));
});
