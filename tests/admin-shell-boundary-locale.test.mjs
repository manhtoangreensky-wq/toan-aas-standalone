import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const i18n = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const badgeStart = portal.indexOf("function pageStatusBadge(page, context)");
const badgeEnd = portal.indexOf("function icon(name)", badgeStart);
assert.ok(badgeStart >= 0 && badgeEnd > badgeStart, "Admin status badge renderer must remain present");
const badge = portal.slice(badgeStart, badgeEnd);

test("Admin shell boundary badges use reviewed locale keys", () => {
  for (const key of ["task", "planning", "generatorReady", "generatorGuarded"]) {
    assert.match(badge, new RegExp(`adminHome\\.boundary\\.${key}`));
  }
  assert.doesNotMatch(badge, /Job Bridge Sẵn sàng|AI Generator|Bộ tạo AI \(Chờ Adapter\)/);
  assert.match(badge, /isAdminPortalSurface\(page\)/);
});

test("Admin shell boundary catalogue is present in VI/EN/ZH", () => {
  const localeBlocks = ["vi", "en", "zh"].map((locale) => {
    const start = i18n.indexOf(`${locale}: {`, i18n.indexOf("const ADMIN_HOME_MESSAGES"));
    const next = locale === "vi" ? i18n.indexOf("    en: {", start) : locale === "en" ? i18n.indexOf("    zh: {", start) : i18n.indexOf("  };", start);
    assert.ok(start >= 0 && next > start, `${locale} Admin Home catalogue missing`);
    return i18n.slice(start, next);
  });
  for (const block of localeBlocks) {
    for (const key of ["task", "planning", "generatorReady", "generatorGuarded"]) {
      assert.match(block, new RegExp(`\\"adminHome\\.boundary\\.${key}\\"\\s*:`));
    }
  }
});
