import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageComposerNativeLocaleHistoricalSource, imageComposerNativeLocaleHistoricalSnapshot} from "./helpers/image-composer-native-locale-historical.mjs";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/image-composer-native-locale-contract.json", import.meta.url), "utf8"));
const prior = file => execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
for (const pin of contract.applicationSources) {
  test(`finite Composer source inverse keeps unknown bytes and rejects reviewed duplication: ${pin.file}`, () => {
    const before = prior(pin.file), records = [...contract.records, ...(contract.amendments || [])].filter(row => row.file === pin.file);
    let current = before;
    for (const row of records) current = current.replace(row.old, () => row.new);
    assert.equal(imageComposerNativeLocaleHistoricalSource(current, pin.file), before);
    assert.equal(imageComposerNativeLocaleHistoricalSource(before, pin.file), before);
    for (const [prefix, suffix] of [["/* unknown */\n", ""], ["", "\n/* unknown */"]]) {
      assert.equal(imageComposerNativeLocaleHistoricalSource(prefix + current + suffix, pin.file), prefix + before + suffix);
    }
    const unknown = text => text.replace("\n", "\n/* unknown internal */\n");
    assert.equal(imageComposerNativeLocaleHistoricalSource(unknown(current), pin.file), unknown(before));
    assert.equal(imageComposerNativeLocaleHistoricalSource(current, "customer/unrelated.js"), current);
    assert.throws(() => imageComposerNativeLocaleHistoricalSource(current + records.at(-1).new, pin.file));
    const visibleRecord = [...records].reverse().find(row => current.includes(row.new));
    assert(visibleRecord, "Use a present outermost record after composed amendments");
    const mutated = current.replace(visibleRecord.new, () => visibleRecord.new + "/* unreviewed */");
    // A mutation can split an earlier nested reviewed record. That must be
    // rejected, not silently normalized into the unmodified baseline.
    let mutationDetected = false;
    try {
      mutationDetected = imageComposerNativeLocaleHistoricalSource(mutated, pin.file) !== before;
    } catch (error) {
      assert.match(error.message, /Unreviewed Composer locale source/);
      mutationDetected = true;
    }
    assert(mutationDetected);
    if (records.length > 1) {
      assert.throws(() => imageComposerNativeLocaleHistoricalSource(current.replace(visibleRecord.new, () => visibleRecord.old), pin.file));
    }
  });
}

const sources = pageMetaSources();
for (const file of ["static/portal/portal.js", "static/portal/portal-i18n.js"]) {
  const key = file.endsWith("portal-i18n.js") ? "i18n" : "portal";
  sources[key] = prior(file);
  for (const row of [...contract.records, ...(contract.amendments || [])].filter(row => row.file === file)) sources[key] = sources[key].replace(row.old, () => row.new);
}
const after = await pageMetaRenderer(sources);
const before = await pageMetaRenderer({...sources, portal: prior("static/portal/portal.js"), i18n: prior("static/portal/portal-i18n.js")});
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: feedback dictionary rejects partial, duplicate or changed values without hiding unknown keys`, () => {
    const current = Object.entries(after(locale, "/image/prompt-composer", {}).messages[locale]);
    const key = "imageComposerFeedbackUi.chooseUnavailable";
    const row = current.find(([name]) => name === key);
    assert(row);
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot(current.filter(([name]) => name !== key), locale));
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot([...current, row], locale));
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot(current.map(([name, value]) => [name, name === key ? "UNREVIEWED" : value]), locale));
    const unknown = ["customer.unreviewed", "Facebook TikTok media studio"];
    const historical = imageComposerNativeLocaleHistoricalSnapshot([...current, unknown], locale);
    assert.deepEqual(historical.at(-1), unknown);
  });
  test(`${locale}: historical dictionary keeps unknown entries and restores only85keys plus2navigation values`, () => {
    const current = Object.entries(after(locale, "/image/prompt-composer", {}).messages[locale]);
    const old = Object.entries(before(locale, "/image/prompt-composer", {}).messages[locale]);
    assert.deepEqual(imageComposerNativeLocaleHistoricalSnapshot(current, locale), old);
    assert.deepEqual(imageComposerNativeLocaleHistoricalSnapshot(old, locale), old);
    const unknown = ["customer.unknown", "Facebook TikTok media studio"];
    assert.deepEqual(imageComposerNativeLocaleHistoricalSnapshot([...current, unknown], locale), [...old, unknown]);
    const key = "imageComposerUi." + contract.copyRows[0][0];
    const partial = current.filter(([name]) => name !== key);
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot(partial, locale));
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot([...current, current.find(([name]) => name === key)], locale));
    assert.throws(() => imageComposerNativeLocaleHistoricalSnapshot(current.map(([name, value]) => [name, name === key ? "UNREVIEWED" : value]), locale));
  });
}
