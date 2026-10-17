import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf('    if (module === "providers")');
const end = portal.indexOf('    if (["provider-cost",', start);
assert.ok(start >= 0 && end > start, "provider renderer boundary exists");
const source = portal.slice(start, end);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("Admin provider catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("adminProviderUi.")).sort());
  assert.equal(keysets[0].length, 22);
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Admin provider table uses locale helper without changing read-only boundary", () => {
  assert.match(portal, /function adminProviderText\(/);
  assert.ok((source.match(/adminProviderText\(/g) || []).length >= 18);
  for (const stale of ["Capabilities", "Healthy", "Degraded", "Unavailable", "Unknown", "Routing"]) {
    assert.doesNotMatch(source, new RegExp(`>[\\s]*${stale}<`), stale);
  }
  assert.match(portal, /module === "providers"/);
  assert.match(source, /type="button" disabled/);
});
