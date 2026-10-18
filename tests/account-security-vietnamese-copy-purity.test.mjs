import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";

const source = fs.readFileSync(new URL("../static/portal/portal-i18n.js", import.meta.url), "utf8");
const start = source.indexOf("  Object.assign(ACCOUNT_SECURITY_MESSAGES.vi, {");
const end = source.indexOf("\n  });", start);
assert.ok(start >= 0 && end > start, "Vietnamese Account Security catalogue must exist");
const viValues = [...source.slice(start, end).matchAll(/^\s+"[^"]+":\s*"([^"\\]*(?:\\.[^"\\]*)*)"/gm)]
  .map((match) => match[1])
  .join(" | ");
const visibleVi = viValues.replace(/\{[^}]+\}/g, "");

test("Vietnamese Account Security chrome does not leak generic English phrases", () => {
  assert.doesNotMatch(
    visibleVi,
    /\b(?:owner-scoped|signed\s+(?:read|session)|mailbox|recovery|merge\s+account|provider|adapter|identity|canonical|contact\s+provider|server|factor|sanitize|Telegram-first|Web\s+App|notification|credential|token|session|flow|email)\b/i,
    "generic English leaked into the Vietnamese Account Security catalogue",
  );
});

test("Vietnamese Account Security keeps reviewed replacements for the affected labels", () => {
  for (const phrase of [
    "thuộc phạm vi tài khoản",
    "phiên đã xác thực",
    "hộp thư",
    "nhà cung cấp",
    "định danh chính thống",
    "luồng khôi phục",
    "phương thức"
  ]) {
    assert.ok(viValues.includes(phrase), `Missing Vietnamese replacement: ${phrase}`);
  }
});
