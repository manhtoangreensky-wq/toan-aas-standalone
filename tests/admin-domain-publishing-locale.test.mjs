import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;
const start = portal.indexOf('"/admin/publishing": {');
const end = portal.indexOf('"/admin/growth": {', start);
assert.ok(start >= 0 && end > start, "publishing domain source boundary exists");
const source = portal.slice(start, end);

test("Publishing Admin domain catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("adminDomainUi.publishing.")).sort());
  assert.equal(keysets[0].length, 14);
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Publishing Admin domain uses locale copy and preserves routes", () => {
  assert.match(portal, /isPublishingDomain/);
  assert.match(portal, /adminDomainText\("publishing\.kicker"/);
  assert.match(portal, /adminDomainText\("publishing\.stream\.campaign\.title"/);
  assert.match(portal, /adminDomainText\("common\.boundaryTitle"/);
  for (const route of ["/admin/campaigns", "/admin/calendar", "/admin/approvals", "/admin/analytics"]) {
    assert.match(source, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), route);
  }
});

test("Growth and Trends Admin domains use locale projections", () => {
  for (const scope of ["growth", "trends"]) {
    assert.match(portal, new RegExp(`adminDomainText\\("${scope}\\.(kicker|title|description)`));
    assert.match(portal, new RegExp(`adminDomainText\\("${scope}\\.boundary`));
  }
  for (const route of ["/admin/leads", "/admin/growth/postback-readiness", "/admin/promos", "/admin/trends", "/admin/features"]) {
    assert.match(portal, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), route);
  }
});
