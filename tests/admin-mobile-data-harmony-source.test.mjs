import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const css = fs.readFileSync("static/portal/portal-theme.css", "utf8");
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

