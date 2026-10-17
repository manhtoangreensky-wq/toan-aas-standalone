import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const i18n = fs.readFileSync("static/portal/portal-i18n.js", "utf8");

const rendererStart = portal.indexOf("function renderAdminCustomerSafetyModal");
const rendererEnd = portal.indexOf("function enrichAdminCustomer360Detail", rendererStart);
assert.ok(rendererStart >= 0 && rendererEnd > rendererStart, "Customer 360 renderers must remain present");
const renderer = portal.slice(rendererStart, rendererEnd);

const catalogueStart = i18n.indexOf("const ADMIN_CUSTOMER_360_MESSAGES = {");
const catalogueEnd = i18n.indexOf("// Finance Operations Planning", catalogueStart);
assert.ok(catalogueStart >= 0 && catalogueEnd > catalogueStart, "Customer 360 locale catalogue must remain present");
const catalogue = i18n.slice(catalogueStart, catalogueEnd);

test("Customer 360 fixed chrome is routed through the locale helper", () => {
  assert.match(renderer, /copy\("accountSafety\.title"/);
  assert.match(renderer, /adminCustomer360Text\("modal\.banWarning"/);
  assert.doesNotMatch(renderer, /\b(?:Charged|Tier|Assets|Support Desk|Audit Trail)\b/);
});

test("Customer 360 locale catalogue covers all supported locales with the same keys", () => {
  const locales = ["vi", "en", "zh"];
  const blocks = new Map();
  for (const locale of locales) {
    const start = catalogue.indexOf(`${locale}: {`);
    assert.ok(start >= 0, `${locale} catalogue missing`);
    const nextLocale = locales.find((candidate) => candidate !== locale && catalogue.indexOf(`${candidate}: {`, start) > start);
    const end = nextLocale ? catalogue.indexOf(`${nextLocale}: {`, start) : catalogue.indexOf("  };", start);
    assert.ok(end > start, `${locale} catalogue boundary missing`);
    blocks.set(locale, catalogue.slice(start, end));
  }
  const keySets = locales.map((locale) => new Set([...blocks.get(locale).matchAll(/"(adminCustomer360\.[^"]+)"\s*:/g)].map((match) => match[1])));
  assert.ok(keySets[0].size >= 45, `expected the complete Customer 360 catalogue, found ${keySets[0].size}`);
  for (let i = 1; i < keySets.length; i += 1) {
    assert.deepEqual([...keySets[i]].sort(), [...keySets[0]].sort(), `${locales[i]} keys must match Vietnamese keys`);
  }
});

test("Vietnamese Customer 360 chrome does not leak generic English labels", () => {
  const viStart = catalogue.indexOf("vi: {");
  const enStart = catalogue.indexOf("en: {", viStart);
  const vi = catalogue.slice(viStart, enStart);
  const values = [...vi.matchAll(/:\s*"([^"]*)"/g)].map((match) => match[1]).join(" | ");
  assert.doesNotMatch(values, /\b(?:Charged|Tier|Assets|Support Desk|Audit Trail|Block|Restore|Account permissions|Active Web sessions)\b/i);
});
