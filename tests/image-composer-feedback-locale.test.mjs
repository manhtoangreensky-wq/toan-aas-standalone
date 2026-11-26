import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const source = fs.readFileSync(new URL("static/portal/integration.js", root), "utf8").replace(/\r\n/g, "\n");
const catalogue = fs.readFileSync(new URL("static/portal/portal-i18n.js", root), "utf8");
const copy = JSON.parse(fs.readFileSync(new URL("tests/fixtures/image-composer-feedback-copy.json", root), "utf8")).rows;
const a = source.indexOf('      if (action === "image-prompt-composer-select-variant") {');
const b = source.indexOf('      if (action === "image-prompt-compose") {', a);
assert(a >= 0 && b > a);
const action = source.slice(a, b);
const helperStart = source.indexOf("  function imageComposerFeedbackText(");
const helperEnd = helperStart < 0 ? -1 : source.indexOf("\n  }", helperStart) + 4;
const helper = helperStart < 0 ? "" : source.slice(helperStart, helperEnd);
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: blocked selection gives the approved plain-language message`, async () => {
    const noop = () => {};
    const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
      documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}}, body: {setAttribute: noop}};
    const window = {document, navigator: {language: locale}, location: {pathname: "/image/prompt-composer", search: ""},
      addEventListener: noop, dispatchEvent: noop, localStorage: {getItem: () => null, setItem: noop}};
    const box = vm.createContext({window, document, navigator: window.navigator, URL, URLSearchParams, Intl,
      base: () => ({capabilities: {"image-prompt-compose": false}})});
    vm.runInContext(catalogue, box);
    window.TOANAASI18n.setLocale(locale, {emit: false});
    vm.runInContext(helper + "\nthis.act=async function(action,fields){\n" + action + "\n};", box);
    await assert.rejects(box.act("image-prompt-composer-select-variant", {}), {
      message: copy.find(row => row.key === "chooseUnavailable")[locale]
    });
  });
}
