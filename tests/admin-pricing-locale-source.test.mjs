import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const PORTAL = readFileSync(join(ROOT, "static/portal/portal.js"), "utf8");
const I18N = readFileSync(join(ROOT, "static/portal/portal-i18n.js"), "utf8");
const start = PORTAL.indexOf("  function renderAdminPricing(");
const end = PORTAL.indexOf("  const BOT_COMPANION_COMMAND_PATTERN", start);
assert.ok(start >= 0 && end > start, "Pricing renderer must remain present");
const pricing = PORTAL.slice(start, end);
const cardStart = PORTAL.indexOf("  function renderAdminPricingCard(");
const cardEnd = PORTAL.indexOf("  let adminCommercialProductsState", cardStart);
assert.ok(cardStart >= 0 && cardEnd > cardStart, "Pricing card renderer must remain present");
const pricingCard = PORTAL.slice(cardStart, cardEnd);

const KEYS = [
  "section.canonical",
  "title.canonical",
  "catalog.version",
  "catalog.approval",
  "catalog.authority",
  "refresh",
  "table.ordinal",
  "table.sku",
  "table.family",
  "table.product",
  "table.salePrice",
  "table.status",
  "section.draft",
  "title.draft",
  "body.draft",
  "draft.save",
  "draft.create",
  "draft.id",
  "draft.baseVersion",
  "draft.reason",
  "publish",
  "section.audit",
  "title.history",
  "history.draftVersion",
  "history.baseCatalog",
  "history.author",
  "history.time",
  "history.reason",
  "diff.source",
  "diff.title",
  "diff.added",
  "diff.changed",
  "diff.removed",
  "diff.none",
  "history.emptyTitle",
  "history.emptyBody",
  "status.draftSaved",
  "status.published",
  "publish.boundary",
  "publish.boundaryBody",
  "body.history",
];
const CARD_KEYS = ["card.draftPrice", "card.salePrice"];

test("Admin Pricing fixed chrome resolves through the locale catalogue", () => {
  for (const key of KEYS) {
    assert.ok(pricing.includes(`pricingText("${key}"`), `Pricing renderer must use adminPricing.${key}`);
    assert.equal(I18N.split(`"adminPricing.${key}":`).length - 1, 3, `adminPricing.${key} must exist once per locale`);
  }
  for (const key of CARD_KEYS) {
    assert.ok(pricingCard.includes(`adminPricing.${key}`), `Pricing card must use adminPricing.${key}`);
    assert.equal(I18N.split(`"adminPricing.${key}":`).length - 1, 3, `adminPricing.${key} must exist once per locale`);
  }
});
