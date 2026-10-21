import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const css = fs.readFileSync("static/portal/portal-theme.css", "utf8");
const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const start = css.indexOf("/* Admin ERP mobile data surface harmony");
const end = css.indexOf("/* Customer Shell Harmony", start);
assert.ok(start >= 0, "Admin mobile data harmony layer must remain present");
const layer = css.slice(start, end >= 0 ? end : undefined);

test("Admin data table mobile harmony is scoped and tokenized", () => {
  for (const selector of [
    '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table-scroll-hint',
    '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table th:first-child',
    '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table tbody tr:hover > td:first-child:not(.portal-empty-cell)'
  ]) assert.ok(layer.includes(selector), `missing scoped selector: ${selector}`);
  assert.match(layer, /@media \(max-width: 700px\)/);
  for (const token of ["var(--portal-border)", "var(--portal-surface-soft)", "var(--portal-surface-light)", "var(--portal-light-hover-surface)", "var(--portal-muted)", "var(--portal-ink)"]) assert.ok(layer.includes(token), `missing theme token: ${token}`);
  assert.match(layer, /color-mix\(in srgb, var\(--portal-ink\) 60%, transparent\)/);
  assert.doesNotMatch(layer, /fetch\(|XMLHttpRequest|\/api\/|data-portal-action|wallet|payos|provider|telegram|data-portal-app-kind="customer"/i);
});

test("Admin data records expose reviewed column labels for compact phone cards", () => {
  const syncStart = portal.indexOf("function syncAdminDataViewRows(root)");
  const syncEnd = portal.indexOf("function renderAdminDataSurface", syncStart);
  assert.ok(syncStart >= 0 && syncEnd > syncStart, "admin data row synchronizer must remain present");
  const sync = portal.slice(syncStart, syncEnd);
  assert.match(sync, /const headers = Array\.from\(surface\.querySelectorAll\("thead th"\)\)/);
  assert.match(sync, /cell\.setAttribute\("data-label", label\)/);
  const compactStart = css.indexOf("/* Admin ERP compact records");
  const compactEnd = css.indexOf("/* Customer Shell Harmony", compactStart);
  assert.ok(compactStart >= 0 && compactEnd > compactStart, "compact record layer must remain scoped");
  const compact = css.slice(compactStart, compactEnd);
  for (const token of ["@media (max-width: 560px)", "tbody tr[data-admin-data-row]", "content: attr(data-label)", "display: none !important", "var(--portal-border)", "var(--portal-surface-light)"]) {
    assert.ok(compact.includes(token), `missing compact record contract: ${token}`);
  }
  assert.doesNotMatch(compact, /fetch\(|XMLHttpRequest|\/api\/|data-portal-action|wallet|payos|provider|telegram/i);
});

test("Admin phone cards fit the viewport without hiding table headings from assistive technology", () => {
  const compactStart = css.indexOf("/* Admin ERP compact records");
  const compactEnd = css.indexOf("/* Customer Shell Harmony", compactStart);
  const compact = css.slice(compactStart, compactEnd);
  assert.match(compact, /\.portal-data-table\s*\{[^}]*width:\s*100%;[^}]*min-width:\s*0;/);
  assert.match(compact, /\.portal-data-table-scroll-hint\s*\{\s*display:\s*none;/);
  assert.match(compact, /\.portal-data-table thead\s*\{[^}]*left:\s*-10000px;/);
  assert.match(compact, /\.portal-data-table tbody tr\[data-admin-data-row\]\s*>\s*td\s+:is\([^)]*\.portal-delivery-state[^)]*\)\s*\{[^}]*white-space:\s*normal;[^}]*overflow-wrap:\s*anywhere;/);
  assert.match(compact, /td\s+\.portal-inline-actions\s*\{[^}]*justify-content:\s*flex-start;/);
});
