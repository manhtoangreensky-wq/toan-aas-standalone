import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf('    if (!allowed && !loading) {', source.indexOf('  function renderSupportAdminBase('));
const end = source.indexOf('    if (loading) {', start);
assert.ok(start >= 0 && end > start, "Support Admin guard branch must remain present");

test("Support Admin guard keeps one useful message without technical chips", () => {
  const branch = source.slice(start, end);
  assert.match(branch, /Quyền hỗ trợ chưa được cấp/);
  assert.match(branch, /Máy chủ chỉ mở dữ liệu chăm sóc khách hàng/);
  assert.doesNotMatch(branch, /portal-state-meta|Vai trò do máy chủ xác minh|Không gọi cầu nối Bot/);
});
