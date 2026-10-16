import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("static/portal/portal.js", "utf8");
const start = source.indexOf("function adminFinanceDomain()");
const end = source.indexOf("const ADMIN_DOMAIN_CENTERS", start);
assert.ok(start >= 0 && end > start, "Finance domain projection must remain present");
const domain = source.slice(start, end);

test("Finance domain fallbacks stay Vietnamese and preserve route projection", () => {
  assert.doesNotMatch(domain, /Finance & revenue control center|Payments|Topups|Revenue|Refunds|Finance planning|Tax readiness|payment canonical|revenue projection|catalog pricing|accounting/);
  for (const route of ["/admin/payments", "/admin/topups", "/admin/revenue", "/admin/refunds", "/admin/pricing", "/admin/finance/planning", "/admin/finance/tax-readiness"]) {
    assert.match(domain, new RegExp(route.replaceAll("/", "\\/")));
  }
  assert.match(domain, /adminFinanceText\("stream\.payments\.title"/);
  assert.match(domain, /adminFinanceText\("boundary\.itemOne"/);
});

