import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const integration = fs.readFileSync("static/portal/integration.js", "utf8");

function between(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle);
  const end = source.indexOf(endNeedle, start + startNeedle.length);
  assert.ok(start >= 0 && end > start, `missing source boundary: ${startNeedle}`);
  return source.slice(start, end);
}

const account = between(portal, "  function renderAccount(page, context)", "  function renderInterfaceLocaleNavigator");
const locale = between(portal, "  function renderInterfaceLocaleNavigator(page, context)", "  function renderAccountSecurity");
const security = between(portal, "  function renderAccountSecurity(page, context)", "  function accountActivityStatus");
const activity = between(portal, "  function renderAccountActivity(page, context)", "  function dataControlsRequestStateLabel");
const workspaceCare = between(portal, "  function renderWorkspaceCare(page, context)", "  function renderAccountDataControls");
const dataControls = between(portal, "  function renderAccountDataControls(page, context)", "  const GOVERNANCE_DOCUMENT_LABELS");
const accountRouteRegistry = between(portal, "  customerPage(\"/account\"", "  customerPage(\"/membership\"");
const accountCapabilities = integration;
const accountActivityCapability = integration;
const dataControlCapabilities = integration;
const secretCleanup = between(integration, 'document.querySelectorAll("[data-account-security-secret]")', 'function');

test("AC-01A account surface exposes the complete owner-scoped profile contract", () => {
  for (const field of ["display_name", "avatar_url", "locale", "timezone"]) {
    assert.match(account, new RegExp(field));
  }
  for (const action of ["update-profile", "select-avatar-preset", "upgrade-telegram-account", "auth-logout"]) {
    assert.match(account, new RegExp(`data-portal-action=\\"${action}\\"`));
  }
  for (const route of ["/account/security", "/account/activity", "/account/data-controls"]) {
    assert.match(account, new RegExp(`href=\\"${route}\\"`));
  }
  for (const provider of ["Telegram", "Google", "GitHub", "Apple"]) {
    assert.match(account, new RegExp(provider));
  }
  assert.doesNotMatch(account, /data-portal-action=\\"(?:wallet|topup|payos|provider-[^\\"]+)\\"/i);
});

test("AC-01A/AC-01B settings navigation and locale preference stay complete", () => {
  const expected = ["/account", "/account/interface-language", "/account/security", "/account/activity", "/account/data-controls"];
  for (const route of expected) {
    assert.match(portal, new RegExp(`path: \\"${route}\\"`));
  }
  assert.match(portal, /aria-current=\"page\"/);
  assert.match(locale, /data-portal-action=\"update-interface-locale\"/);
  assert.match(locale, /localeMetadata/);
  for (const value of ["vi", "en", "zh"]) assert.match(locale, new RegExp(`\\b${value}:`));
  assert.match(locale, /No Bot state|noBotState|Không chuyển state Telegram/);
  assert.doesNotMatch(locale, /data-portal-action=\"(?:wallet|topup|payos|provider-[^\"]+)\"/i);
});

test("AC-01C security surface has guarded sessions, password, OAuth, MFA and cleanup contracts", () => {
  assert.match(security, /security\.readState === \"read_only\"/);
  assert.match(security, /slice\(0, 20\)/);
  for (const action of [
    "account-security-refresh",
    "account-security-revoke-session",
    "account-security-revoke-others",
    "account-security-password-change",
    "account-security-oauth-unlink",
    "account-security-mfa-start",
    "account-security-mfa-confirm",
    "account-security-mfa-disable"
  ]) {
    assert.match(security, new RegExp(`data-portal-action=\\"${action}\\"`));
  }
  assert.match(security, /session_ref/);
  assert.match(security, /autocomplete=\"current-password\"/);
  assert.match(security, /autocomplete=\"new-password\"/);
  assert.match(security, /data-account-security-secret/);
  assert.match(security, /data-account-security-mfa-secret/);
  assert.doesNotMatch(security, /(?:window|globalThis)\s*\.\s*(?:localStorage|sessionStorage)/);
  assert.match(secretCleanup, /\.value = \"\"/);
});

test("AC-01D activity surface is bounded, refreshable and redacted", () => {
  assert.match(activity, /context\.accountActivity/);
  assert.match(activity, /slice\(0, 50\)/);
  assert.match(activity, /renderRowsTable/);
  assert.match(activity, /data-portal-action=\"refresh-account-activity\"/);
  assert.match(activity, /owner|chủ sở hữu|server/i);
  assert.match(activity, /Bot|Xu|PayOS|provider/i);
});

test("AC-01E workspace care and data controls keep guarded/read-only boundaries", () => {
  for (const route of ["/notes", "/reminders", "/account/data-controls"]) {
    assert.match(workspaceCare, new RegExp(`route: \\"${route}\\"`));
  }
  assert.match(workspaceCare, /data\.Bot|Bot companion|Không có dọn dẹp tự động/);
  for (const action of [
    "data-controls-refresh",
    "data-controls-export",
    "data-controls-erasure-request",
    "data-controls-erasure-cancel"
  ]) {
    assert.match(dataControls, new RegExp(`data-portal-action=\\"${action}\\"`));
  }
  assert.match(dataControls, /data-state=\"guarded\"/);
  assert.match(dataControls, /data-state=\"processing\"/);
  assert.match(dataControls, /data-controls-erasure-cancel/);
  assert.match(dataControls, /name=\"request_id\"/);
  assert.match(dataControls, /name=\"expected_revision\"/);
  assert.match(dataControls, /Không gọi Bot|Bot\/Telegram/);
});

test("AC-01 capability and route wiring remain server-gated", () => {
  for (const capability of [
    "account-security-view",
    "account-security-revoke-session",
    "account-security-revoke-others",
    "account-security-password-change",
    "account-security-oauth-unlink",
    "account-security-mfa-start",
    "account-security-mfa-confirm",
    "account-security-mfa-disable"
  ]) assert.match(accountCapabilities, new RegExp(`\\"${capability}\\":`));
  assert.match(accountActivityCapability, /refresh-account-activity/);
  for (const capability of [
    "data-controls-view",
    "data-controls-refresh",
    "data-controls-export",
    "data-controls-erasure-request",
    "data-controls-erasure-cancel"
  ]) assert.match(dataControlCapabilities, new RegExp(`\\"${capability}\\":`));
  for (const route of [
    "/account/interface-language",
    "/account/activity",
    "/account/security",
    "/account/data-controls",
    "/account/workspace-care"
  ]) assert.match(accountRouteRegistry + portal, new RegExp(route.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")));
});
