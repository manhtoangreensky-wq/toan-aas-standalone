import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("remaining customer guard surfaces hide only repeated implementation chips", () => {
  const block = css.match(/\.portal-page :is\(\s*\.portal-project-package-panel,\s*\.portal-finalization-intro\s*\) \.portal-state-meta,\s*\.portal-page:is\(\s*\.portal-asset-vault,\s*\.portal-inbox,\s*\.portal-notification-automation,\s*\.portal-operations\s*\) \.portal-state-meta\s*\{\s*display:\s*none;\s*\}/s)?.[0];
  assert.ok(block, "customer guard selector must be route-scoped and match nested DOM");
  for (const className of ["portal-project-package-panel", "portal-finalization-intro", "portal-asset-vault", "portal-inbox", "portal-notification-automation", "portal-operations"]) {
    assert.match(block, new RegExp(`\\.${className}`));
  }
});
