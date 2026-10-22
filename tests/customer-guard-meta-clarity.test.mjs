import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const css = fs.readFileSync("static/portal/portal.css", "utf8").replace(/\r\n/g, "\n");

test("remaining customer guard surfaces hide only repeated implementation chips", () => {
  for (const className of [
    "portal-project-package-panel",
    "portal-asset-vault",
    "portal-inbox",
    "portal-notification-automation",
    "portal-operations",
    "portal-finalization-intro"
  ]) assert.match(css, new RegExp(`\\.${className}[\\s\\S]*?\\.portal-state-meta`));
});
