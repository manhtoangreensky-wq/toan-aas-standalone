import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(i18nSource, context);
const messages = context.TOANAASI18n.messages;
const start = portalSource.indexOf("  const CAMPAIGN_PLAN_STATUSES");
const end = portalSource.indexOf("  function renderLanding", start);
assert.notEqual(start, -1, "Campaign renderer source boundary exists");
assert.notEqual(end, -1, "Campaign renderer ends before landing");
const source = portalSource.slice(start, end);

test("Campaign Planner has equal VI/EN/ZH fixed chrome", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("campaignUi.")).sort());
  assert.deepEqual(keysets[1], keysets[0], "Campaign Planner VI and EN keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "Campaign Planner VI and ZH keysets must remain equal");
  assert.ok(keysets[0].length >= 90, "Campaign catalogue must cover planning, detail, calendar and self-review");
  for (const key of [
    "campaignUi.page.newTitle",
    "campaignUi.board.title",
    "campaignUi.detail.title",
    "campaignUi.calendar.title",
    "campaignUi.approvals.title",
    "campaignUi.schedule.title",
    "campaignUi.status.review",
    "campaignUi.objective.conversion"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], "missing Campaign locale copy: " + key);
  }
});

test("Campaign fixed chrome is localized without changing its Web-only contracts", () => {
  for (const helperCall of [
    'campaignText("board.title"',
    'campaignText("authoring.title"',
    'campaignText("detail.title"',
    'campaignText("calendar.title"',
    'campaignText("approvals.title"'
  ]) {
    assert.ok(source.includes(helperCall), "Campaign renderer must use localized helper: " + helperCall);
  }
  for (const staleFixedCopy of [
    "New private campaign",
    "Execution boundary",
    "Private campaign operations",
    "Owner-scoped library",
    "Campaign Operations Board",
    "Content Calendar",
    "Self-review Queue",
    "signed account",
    "owner-scoped",
    "Web-owned"
  ]) {
    assert.ok(!source.includes(staleFixedCopy), "mixed-language Campaign copy remains: " + staleFixedCopy);
  }
  for (const contract of [
    'data-portal-action="campaign-create"',
    'data-portal-action="campaign-update"',
    'data-portal-action="campaign-update-status"',
    'data-portal-action="campaign-calendar-filter"',
    'data-portal-action="campaign-calendar-month"',
    'data-portal-action="campaign-calendar-refresh"',
    'data-portal-action="campaign-schedule-create"',
    'data-portal-action="campaign-schedule-cancel"',
    'data-portal-action="campaign-schedule-reconfirm"',
    'data-campaign-plan-id=',
    'data-campaign-plan-revision=',
    'data-campaign-schedule-intent-id=',
    'data-campaign-schedule-intent-revision='
  ]) {
    assert.ok(source.includes(contract), "Campaign workflow contract missing: " + contract);
  }
});
