import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const I18N = readFileSync(join(ROOT, "static/portal/portal-i18n.js"), "utf8");
const start = PORTAL.indexOf('if (["pricing", "packages"].includes(module))');
const end = PORTAL.indexOf('if (module === "providers")', start);
assert.ok(start >= 0 && end > start, "Generic commercial pricing branch must remain present");
const branch = PORTAL.slice(start, end);

const KEYS = [
  "pricing.column.packageId",
  "pricing.column.name",
  "pricing.column.family",
  "pricing.column.priceXu",
  "pricing.column.priceVnd",
  "pricing.column.limits",
  "pricing.column.status",
  "pricing.column.updatedAt",
  "pricing.column.actions",
  "pricing.emptyTitle",
  "pricing.emptyBody",
  "pricing.action.edit",
  "pricing.action.lockedReason",
  "pricing.family.default",
];

test("Generic commercial pricing table uses native locale copy without field-code jargon", () => {
  assert.doesNotMatch(branch, /PACKAGE_ID|PRICE_XU|PRICE_VND|LIMITS|STATUS|ACTIONS/, "Fixed table chrome must not expose schema field codes");
  for (const key of KEYS) {
    assert.ok(branch.includes(`adminGenericText("${key}"`), `Generic pricing branch must use adminGeneric.${key}`);
    assert.equal(I18N.split(`"adminGeneric.${key}":`).length - 1, 3, `adminGeneric.${key} must exist once per locale`);
  }
});
