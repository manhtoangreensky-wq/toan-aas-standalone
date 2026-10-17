import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const theme = fs.readFileSync("static/portal/portal-theme.css", "utf8");
const start = theme.indexOf('.portal-shell[data-portal-app-kind="admin"] .portal-admin-tabs {');
const end = theme.indexOf("/* A09 Admin Vertical Shell */", start);
const adminTabs = theme.slice(start, end);

test("Admin module navigation is a vertical, touch-sized list", () => {
  assert.match(adminTabs, /\.portal-admin-tabs\s*\{[^}]*display:\s*block/su);
  assert.match(adminTabs, /\.portal-admin-tabs-list\s*\{[^}]*display:\s*grid/su);
  assert.match(adminTabs, /grid-template-columns:\s*minmax\(0,\s*1fr\)/su);
  assert.match(adminTabs, /\.portal-admin-tab\s*\{[^}]*min-height:\s*44px/su);
  assert.match(adminTabs, /\.portal-admin-tab\s*\{[^}]*white-space:\s*normal/su);
  assert.doesNotMatch(adminTabs, /overflow-x:\s*auto/su);
  assert.doesNotMatch(adminTabs, /min-width:\s*max-content/su);
});
