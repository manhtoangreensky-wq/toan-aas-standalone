import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const start = PORTAL.indexOf("  function renderAdminPricing(");
const end = PORTAL.indexOf("  const BOT_COMPANION_COMMAND_PATTERN", start);
assert.ok(start >= 0 && end > start, "Pricing renderer must remain present");
const pricing = PORTAL.slice(start, end);

test("Admin Pricing write affordances are fail-closed without server-issued capabilities", () => {
  assert.match(pricing, /admin-pricing-draft-create[\s\S]*\$\{draftCreateDisabled\}/, "Create draft must use its capability gate");
  assert.match(pricing, /admin-pricing-draft-save[\s\S]*\$\{draftSaveDisabled\}/, "Save draft must use its capability gate");
  assert.match(pricing, /admin-pricing-publish-modal-open[\s\S]*\$\{publishDisabled\}/, "Publish affordance must use its capability gate");
  assert.match(pricing, /const canDraftCreate = capabilities\["admin-pricing-draft-create"\] === true/, "Create capability must be read from server context");
  assert.match(pricing, /const canDraftSave = capabilities\["admin-pricing-draft-save"\] === true/, "Save capability must be read from server context");
  assert.match(pricing, /const canPublish = capabilities\["admin-pricing-publish-modal-open"\] === true/, "Publish capability must be read from server context");
});
