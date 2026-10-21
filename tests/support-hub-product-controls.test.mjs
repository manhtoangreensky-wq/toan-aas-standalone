import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const css = fs.readFileSync("static/portal/portal.css", "utf8");
const i18n = fs.readFileSync("static/portal/portal-i18n.js", "utf8");

const supportStart = portal.indexOf("  function renderSupportDesk(page, context)");
const accountNavStart = portal.indexOf("  function renderAccountSettingsNav(currentPath)", supportStart);
assert.ok(supportStart >= 0 && accountNavStart > supportStart, "Support renderer boundary exists");
const supportRenderer = portal.slice(supportStart, accountNavStart);

const viTicketStart = i18n.indexOf("Object.assign(SUPPORT_TICKET_MESSAGES.vi, {");
const enTicketStart = i18n.indexOf("Object.assign(SUPPORT_TICKET_MESSAGES.en, {", viTicketStart);
assert.ok(viTicketStart >= 0 && enTicketStart > viTicketStart, "Vietnamese Support catalogue exists");
const viTicket = i18n.slice(viTicketStart, enTicketStart);
const adminCopyStart = i18n.indexOf("const ADMIN_SUPPORT_COPY = Object.freeze([");
const adminCopyEnd = i18n.indexOf("  ]);", adminCopyStart);
assert.ok(adminCopyStart >= 0 && adminCopyEnd > adminCopyStart, "Admin Support catalogue exists");
const viAdmin = i18n.slice(adminCopyStart, adminCopyEnd);

test("Support customer routes use the natural Vietnamese name and preserve the workflow", () => {
  assert.match(portal, /customerPage\("\/support", "Trung tâm hỗ trợ khách hàng"/);
  assert.match(portal, /customerPage\("\/tickets", "Yêu cầu của tôi"/);
  for (const token of [
    'data-portal-action="support-case-create"',
    'data-portal-action="support-case-reply"',
    'data-support-case-id=',
    'data-support-case-revision=',
    'supportTicketText("desk.intake.title"',
    'supportTicketText("detail.thread.title"',
    'renderSupportRecoveryPlan(context, caseItem)'
  ]) assert.ok(supportRenderer.includes(token), `missing Support contract: ${token}`);
  assert.match(portal, /data-portal-action="support-case-attachment"/);
  assert.doesNotMatch(portal, /customerPage\("\/support", "Web Support Desk"/);
});

test("Support admin controls remain server-gated and keep public/internal reply separation", () => {
  assert.match(portal, /adminPage\("\/admin\/support", "Trung tâm hỗ trợ khách hàng"/);
  for (const token of [
    'data-portal-action="support-admin-case-reply"',
    'data-portal-action="support-admin-case-update"',
    'data-support-case-id=',
    'data-support-case-revision=',
    'name="visibility"',
    'value="public"',
    'value="internal"',
    'copy("detail.updateSectionTitle"'
  ]) assert.ok(supportRenderer.includes(token), `missing Admin Support contract: ${token}`);
  assert.match(supportRenderer, /supportCareStaffRole\(context\.supportAdminSummary\)/);
  assert.doesNotMatch(viAdmin, /Trung tâm hỗ trợ khách hàng Web/);
});

test("Support Vietnamese fixed chrome does not leak the old English desk label", () => {
  assert.doesNotMatch(viTicket, /Web Support Desk|Support Desk|Web App/);
  assert.match(viTicket, /"supportTicket\.desk\.intro\.title"/);
  assert.match(viTicket, /"supportTicket\.detail\.reply\.submit"/);
  assert.match(viAdmin, /"page\.list\.title", "Trung tâm hỗ trợ khách hàng"/);
});

test("Support surfaces keep the blue/teal system and vertical mobile fallback", () => {
  for (const selector of [
    ".portal-support-desk",
    ".portal-support-cases",
    ".portal-support-case-detail",
    ".portal-support-admin",
    ".portal-support-case-grid",
    ".portal-support-admin-forms"
  ]) assert.match(css, new RegExp(selector.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")));
  assert.match(css, /@media \(max-width: 620px\)/);
  assert.match(css, /\.portal-support-case-grid\s*\{[^}]*grid-template-columns:\s*1fr;/);
  assert.doesNotMatch(css, /\.portal-support[^}]*background:\s*(?:#000|black)/i);
});
