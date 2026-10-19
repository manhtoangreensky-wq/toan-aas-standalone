import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");

function between(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle);
  const end = source.indexOf(endNeedle, start + startNeedle.length);
  assert.ok(start >= 0 && end > start, `missing source boundary: ${startNeedle}`);
  return source.slice(start, end);
}

const card = between(portal, "  function renderAdminManualTopupCard", "  function renderAdminManualTopupActions");
const surface = between(portal, "  function renderAdminManualTopups", "  function renderAdminPricingCard");
const facts = between(portal, "  function adminManualTopupFacts", "  function renderAdminManualTopupCard");
const confirmation = between(portal, "  function renderAdminManualTopupConfirmation", "  function renderAdminManualTopups");

test("Manual top-up list and mobile card hide approval writes without server capability", () => {
  assert.match(card, /function renderAdminManualTopupCard\(record, selectedId, writeEnabled\)/);
  assert.match(card, /writeEnabled \? `[^`]*data-portal-action="admin-manual-topup-draft"/s);
  assert.match(card, /actions\.permissionBody/);
  assert.match(card, /actions\.readOnlyTitle/);
  assert.match(surface, /const writeEnabled = Boolean\(context\.capabilities && context\.capabilities\["admin-manual-topup-write"\] === true\)/);
  assert.match(surface, /writeEnabled \? `[^`]*data-portal-action="admin-manual-topup-draft"/s);
  assert.match(surface, /renderAdminManualTopupCard\(item, state\.selected && state\.selected\.request_id, writeEnabled\)/);
  assert.match(surface, /renderAdminManualTopupConfirmation\(state\.draft, state\.selected, writeEnabled\)/);
  assert.match(confirmation, /function renderAdminManualTopupConfirmation\(draft, selected, writeEnabled\)/);
  assert.match(confirmation, /if \(!writeEnabled \|\| !draft \|\| !draft\.confirmation_receipt\)/);
});

test("Manual top-up approval action is not an unconditional list affordance", () => {
  const pendingBranches = [...surface.matchAll(/item\.status === "pending_admin_review"[\s\S]*?:(?:\s*`|\s*<)/g)].map((match) => match[0]);
  assert.ok(pendingBranches.length > 0, "pending list branch exists");
  for (const branch of pendingBranches) {
    assert.match(branch, /writeEnabled/);
  }
  assert.doesNotMatch(card, /record\.status === "pending_admin_review"\s*\?\s*`[^`]*data-portal-action="admin-manual-topup-draft"/s);
});

test("Manual top-up UI never derives Xu from the submitted amount", () => {
  assert.doesNotMatch(facts, /Math\.floor\(.*amount_vnd/s);
  assert.doesNotMatch(confirmation, /Math\.floor\(.*amountVnd/s);
  assert.match(confirmation, /xuCandidate/);
  assert.match(confirmation, /adminNumericValue\(xuCandidate\)/);
  assert.match(confirmation, /draft\.approved_xu/);
  assert.match(confirmation, /activeSelected && activeSelected\.expected_xu/);
});
