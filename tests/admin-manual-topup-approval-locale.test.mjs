import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(root, "static/portal/portal.js"), "utf8");
const i18n = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");
const start = portal.indexOf("  function renderAdminManualTopupCard");
const end = portal.indexOf("  function renderAdminManualTopupActions", start);
const actionStart = end;
const actionEnd = portal.indexOf("  function renderAdminManualTopupInspector", actionStart);
assert.ok(start >= 0 && end > start && actionEnd > actionStart, "manual top-up renderer boundaries exist");
const source = portal.slice(start, actionEnd);
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;

test("Manual top-up approval catalogue is balanced", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("adminManualTopup.approval.")).sort());
  assert.equal(keysets[0].length, 10);
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Manual top-up approval chrome is localized without changing draft contracts", () => {
  assert.match(source, /adminManualTopupText\("approval\.approveTitle"/);
  assert.match(source, /adminManualTopupText\("approval\.rejectTitle"/);
  for (const stale of [
    "Duyệt nạp tiền &amp; Cộng Xu",
    "Xác nhận tiền đã vào &amp; cộng Xu",
    "Chưa nhận được giao dịch / Bill không trùng khớp"
  ]) assert.doesNotMatch(source, new RegExp(stale.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), stale);
  for (const contract of [
    'data-portal-action="admin-manual-topup-draft"',
    'data-manual-admin-decision="approve"',
    'data-manual-admin-decision="reject"',
    'name="reason"'
  ]) assert.match(source, new RegExp(contract.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), contract);
});
