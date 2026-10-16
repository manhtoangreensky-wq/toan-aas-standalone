import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("static/portal/portal.js", "utf8");
const start = source.indexOf("function renderAdminSystemStewardship");
const end = source.indexOf("function renderAdminFinanceTaxNotes", start);
assert.ok(start >= 0 && end > start, "System stewardship renderer must remain present");
const renderer = source.slice(start, end);

test("System stewardship Vietnamese fallbacks stay in one language", () => {
  assert.doesNotMatch(renderer, /Automation Monitor|Security Posture|Access Posture|Governance Documents|Internal Document Archive|\\bRuntime\\b|\\bBackups\\b|Separately guarded|Web-owned surfaces|No hidden controls|Canonical authority/);
  assert.match(renderer, /text\("card\.automation\.title"/);
  assert.match(renderer, /text\("boundary\.noLedger\.title"/);
});

