import assert from "node:assert/strict";

const fail = "Unreviewed required-field warning";
const portal = "static/portal/portal.js", catalogue = "static/portal/portal-i18n.js";
const key = "portal.form.requiredWarning";
const oldToast = 'showToast("Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.", "warning");';
const newToast = 'showToast(uiText("portal.form.requiredWarning", "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục."), "warning");';
const additions = '  MESSAGES.vi["portal.form.requiredWarning"] = "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.";\n' +
  '  MESSAGES.en["portal.form.requiredWarning"] = "Complete the required fields before continuing.";\n' +
  '  MESSAGES.zh["portal.form.requiredWarning"] = "请先填写必填项，然后继续。";\n\n';
const count = (source, part) => source.split(part).length - 1;

// Only historical comparisons may use this; the current source has its own
// forward and behavior checks and is never approved by this projection alone.
export function requiredWarningHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  assert.equal(typeof file, "string", fail);
  if (![portal, catalogue].includes(file) || !source.includes(key)) return source;
  if (file === portal) {
    assert.equal(count(source, key), 1, fail);
    assert.equal(count(source, newToast), 1, fail);
    const start = source.indexOf("  function dispatchAction(source, context) {");
    const end = source.indexOf("  function bindInteractions() {");
    const at = source.indexOf(newToast);
    assert.ok(start >= 0 && start < at && at < end, fail);
    return source.replace(newToast, oldToast);
  }
  assert.equal(count(source, key), 3, fail);
  assert.equal(count(source, additions), 1, fail);
  assert.equal(count(source, additions + "  verifyEqualKeysets();"), 1, fail);
  return source.replace(additions, "");
}

const copy = {
  vi: "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.",
  en: "Complete the required fields before continuing.",
  zh: "请先填写必填项，然后继续。"
};
export function requiredWarningHistoricalSnapshot(entries, locale) {
  assert.ok(Array.isArray(entries) && Object.hasOwn(copy, locale), fail);
  const found = entries.filter(([entryKey]) => entryKey === key);
  if (!found.length) return entries;
  assert.equal(found.length, 1, fail);
  assert.equal(found[0][1], copy[locale], fail);
  return entries.filter(([entryKey]) => entryKey !== key);
}
