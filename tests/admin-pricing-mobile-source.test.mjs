import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const CSS = readFileSync(join(ROOT, "static/portal/portal-theme.css"), "utf8");

test("Admin Pricing exposes a vertical mobile card lane without inline display:none", () => {
  const pricingStart = PORTAL.indexOf('class="portal-page portal-admin-pricing"');
  const pricingEnd = PORTAL.indexOf("const BOT_COMPANION_COMMAND_PATTERN", pricingStart);
  assert.ok(pricingStart >= 0 && pricingEnd > pricingStart, "Pricing markup must remain present");
  const markup = PORTAL.slice(pricingStart, pricingEnd);
  assert.doesNotMatch(markup, /portal-admin-pricing-mobile[^>]*display:\s*none/i, "Mobile pricing lane must not be hidden inline");
  assert.match(CSS, /portal-admin-pricing-mobile[^{]*\{[^}]*display:\s*none/i, "Desktop default must hide mobile cards");
  assert.match(CSS, /@media\s*\(max-width:\s*700px\)[\s\S]*portal-admin-pricing-mobile[^{]*\{[^}]*display:\s*block/i, "Mobile breakpoint must show vertical cards");
  assert.match(CSS, /@media\s*\(max-width:\s*700px\)[\s\S]*portal-admin-pricing-desktop[^{]*\{[^}]*display:\s*none/i, "Mobile breakpoint must hide clipped desktop table");
});
