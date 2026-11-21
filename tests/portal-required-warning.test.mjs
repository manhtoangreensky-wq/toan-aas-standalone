import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {webcrypto} from "node:crypto";

const portal = fs.readFileSync(new URL("../static/portal/portal.js", import.meta.url), "utf8");
const i18n = fs.readFileSync(new URL("../static/portal/portal-i18n.js", import.meta.url), "utf8");
const anchor = "  window.TOANAASPortal = Object.freeze({";
assert.equal(portal.split(anchor).length - 1, 1);

function invalidForm(locale, loadI18n = true) {
  const nodes = [], events = [], focus = [], noop = () => {};
  const region = {querySelectorAll: () => nodes, appendChild: node => nodes.push(node)};
  const document = {
    readyState: "loading", addEventListener: noop,
    querySelector: selector => selector === "[data-portal-toast]" ? region : null,
    querySelectorAll: () => [], getElementById: () => null,
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}},
    body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop},
    createElement: () => ({attributes: {}, setAttribute(key, value) { this.attributes[key] = value; }})
  };
  const window = {
    document, navigator: {language: locale}, location: {pathname: "/image-studio", search: ""},
    addEventListener: noop, dispatchEvent: event => events.push(event),
    matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: {getItem: () => null, setItem: noop}, setTimeout: noop, clearTimeout: noop, crypto: webcrypto
  };
  const box = vm.createContext({
    window, document, navigator: window.navigator, location: window.location,
    URL, URLSearchParams, Intl, console, crypto: webcrypto, setTimeout: noop, clearTimeout: noop
  });
  if (loadI18n) vm.runInContext(i18n, box);
  vm.runInContext(portal.replace(anchor, "  window.__requiredWarningQA = {dispatchAction};\n" + anchor), box);
  if (loadI18n) window.TOANAASI18n.setLocale(locale, {emit: false});
  let validityCalls = 0;
  const invalid = {focus: () => focus.push(true)};
  const form = {
    getAttribute: key => key === "data-portal-action" ? "image-artboard-create" : "",
    matches: selector => selector === "form",
    reportValidity: () => { validityCalls += 1; return false; },
    querySelector: selector => selector === ":invalid" ? invalid : null
  };
  window.__requiredWarningQA.dispatchAction(form, {path: "/image-studio"});
  return {nodes, events, focus, validityCalls};
}

for (const [locale, expected] of Object.entries({
  vi: "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.",
  en: "Complete the required fields before continuing.",
  zh: "请先填写必填项，然后继续。"
})) {
  test(`${locale}: invalid form focuses the field and shows a warning in the selected language`, () => {
    const result = invalidForm(locale);
    assert.equal(result.validityCalls, 1);
    assert.deepEqual(result.focus, [true]);
    assert.deepEqual(result.events, []);
    assert.equal(result.nodes.length, 1);
    assert.equal(result.nodes[0].attributes.role, "alert");
    assert.equal(result.nodes[0].textContent, expected);
  });
}

test("without the translation service an invalid form retains its Vietnamese fallback", () => {
  const result = invalidForm("vi", false);
  assert.equal(result.validityCalls, 1);
  assert.deepEqual(result.focus, [true]);
  assert.deepEqual(result.events, []);
  assert.equal(result.nodes[0].textContent, "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.");
});
