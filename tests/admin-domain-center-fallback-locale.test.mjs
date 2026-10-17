import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("static/portal/portal.js", "utf8");
const start = source.indexOf("const ADMIN_DOMAIN_CENTERS");
const end = source.indexOf("function renderAdminDomain", start);
assert.ok(start >= 0 && end > start, "Admin domain center catalogue must remain present");
const domain = source.slice(start, end);

test("Admin publishing/growth/trends fallbacks stay Vietnamese", () => {
  assert.doesNotMatch(domain, /Publishing control center|Campaign Center|Content Calendar|Approval Queue|Growth & affiliate control center|Leads|Postback readiness|Trend & reference control center|Campaign briefs|Creative analytics|Publishing handoff|Feature readiness/);
  for (const route of ["/admin/publishing", "/admin/growth", "/admin/trends", "/admin/campaigns", "/admin/calendar", "/admin/approvals", "/admin/analytics"]) {
    assert.match(domain, new RegExp(route.replaceAll("/", "\\/")));
  }
});
