import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderCampaignDetail(");
const end = source.indexOf("\n  function renderCampaignCalendar", start);
assert.ok(start >= 0 && end > start, "Campaign detail renderer boundary must remain present");
const approvalsStart = source.indexOf("  function renderCampaignApprovals(");
const approvalsEnd = source.indexOf("\n  function ", approvalsStart + 10);
assert.ok(approvalsStart >= 0 && approvalsEnd > approvalsStart, "Campaign approvals renderer boundary must remain present");

test("Campaign detail and approval boundaries keep useful copy without technical chips", () => {
  const renderer = source.slice(start, end);
  const approvals = source.slice(approvalsStart, approvalsEnd);
  assert.doesNotMatch(renderer, /portal-state-meta/);
  assert.doesNotMatch(approvals, /portal-state-meta/);
  assert.match(renderer, /campaignText\("detail\.boundaryBody"/);
  assert.match(approvals, /campaignText\("approvals\.boundaryBody"/);
});
