import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const start = PORTAL.indexOf("const ADMIN_TAB_GROUPS = [");
const end = PORTAL.indexOf("function renderAdminModuleTabs", start);
assert.ok(start >= 0 && end > start, "Admin tab catalogue must remain present");
const catalogue = PORTAL.slice(start, end);

test("Vietnamese Admin module tabs do not leak generic English UI terms", () => {
  const labels = [...catalogue.matchAll(/\blabel:\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.ok(labels.length >= 40, `expected the complete Admin tab catalogue, found ${labels.length}`);
  const genericEnglish = /\b(?:Autopilot|Leads|Support Desk|Tickets|Jobs|Automation Monitor|Providers?|Workers|Runtime|Features|Freeze|Packages|Promo|Analytics|Affiliate|System Stewardship|Audit)\b/i;
  assert.deepEqual(labels.filter((label) => genericEnglish.test(label)), [], "VI labels must be translated; keep product/acronym names only when intentional");
});

test("English Admin module tab labels remain explicit", () => {
  const labels = [...catalogue.matchAll(/\blabelEn:\s*"([^"]+)"/g)].map((match) => match[1]);
  assert.ok(labels.length >= 40, `expected the complete English Admin tab catalogue, found ${labels.length}`);
  assert.ok(labels.includes("Analytics"));
  assert.ok(labels.includes("Provider Cost"));
  assert.ok(labels.includes("System"));
});
