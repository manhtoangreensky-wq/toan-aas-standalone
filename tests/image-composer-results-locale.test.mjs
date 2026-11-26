import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {imageComposerRuntime} from "./helpers/image-composer-native-runtime.mjs";

const read = name => JSON.parse(fs.readFileSync(new URL("./fixtures/" + name, import.meta.url), "utf8"));
const contract = read("image-composer-native-locale-contract.json"), fixture = read("image-composer-native-text-results.json");
assert.equal(fixture.base, contract.base);
assert.equal(fixture.rows.length, 26);
assert.equal(fixture.source_lf_sha256, contract.applicationSources.find(pin => pin.file === "copyfast_image_studio.py").afterLfSha256);
const sources = pageMetaSources(), historical = {...sources};
for (const [key, file] of [["portal", "static/portal/portal.js"], ["i18n", "static/portal/portal-i18n.js"]]) {
  historical[key] = execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
}
const currentRenderer = await imageComposerRuntime(sources), oldRenderer = await imageComposerRuntime(historical);
const route = "/image/prompt-composer", current = currentRenderer("vi", route, {}), old = oldRenderer("vi", route, {});
const controls = html => [...html.matchAll(/<(?:form|input|textarea|select|option|button|a)\b[^>]*>/g)]
  .map(match => {
    let tag = match[0].replace(/\s(?:placeholder|title|aria-label|data-portal-confirm)="[^"]*"/g, "");
    // COMP-GOAL adds only this reviewed dynamic-required metadata. Actual
    // hidden/required/disabled behavior is exercised in the browser matrix.
    if (tag.includes('name="custom_goal"')) tag = tag.replace(' aria-required="false"', "");
    return tag;
  });
const escape = text => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const context = (view, locale, raw) => view.qa.normalizeBootstrap({
  path: route, interfaceLocale: locale, profile: {locale, displayName: "QA"},
  session: {authenticated: true, csrfToken: "synthetic-local-only"}, ...raw
});
const render = (view, locale, raw) => {
  view.setLocale(locale);
  const state = context(view, locale, raw);
  return {state, html: view.qa.renderPage(view.qa.resolvePage(route), state)};
};
let expectedViews = 0;
for (const row of fixture.rows) {
  const fullSelection = row.source.style_preset === "auto" || row.source.goal_code === "custom";
  const saveStates = fullSelection ? [false, true] : [true], indices = fullSelection ? [0, 1, 2, 3] : [0];
  for (const [localeIndex, locale] of ["vi", "en", "zh"].entries()) for (const canSave of saveStates) for (const index of indices) {
    expectedViews++;
    test(`${locale}/${row.source.language}/${row.source.goal_code}/${row.source.style_preset}/save${canSave}/index${index}: native chrome, selected output and controls remain separate`, () => {
      const raw = {imagePromptComposerEnabled: true,
        capabilities: {"image-prompt-compose": true, "image-prompt-composer-save-memory": canSave},
        imagePromptComposerResult: row.result, imagePromptComposerSaveSource: row.source,
        imagePromptComposerSelectedVariantIndex: index};
      const before = render(old, locale, raw), after = render(current, locale, raw);
      assert.deepEqual(controls(after.html), controls(before.html));
      assert.match(after.html, /name="custom_goal"[^>]*aria-required="false"/);
      assert.deepEqual(JSON.parse(JSON.stringify(after.state)), JSON.parse(JSON.stringify(before.state)));
      assert.equal(after.state.imagePromptComposerResult.composer.language, row.source.language);
      for (const key of ["title", "goal_label", "style", "short_prompt", "detailed_prompt", "negative_prompt"]) {
        assert(after.html.includes(escape(row.result.composer[key])), `Preserve selected-language ${key}`);
      }
      for (const value of [...row.result.composer.variants, ...row.result.composer.review_before_use]) assert(after.html.includes(escape(value)));
      for (const key of ["prompt.short", "prompt.detailed", "prompt.negative", "review.title", "result.note", "save.button"]) {
        const label = contract.copyRows.find(item => item[0] === key)[localeIndex + 1];
        assert(after.html.includes(escape(label)), `Native fixed label ${key}`);
      }
      const save = controls(after.html).find(tag => tag.includes('data-portal-action="image-prompt-composer-save-memory"'));
      assert(save);
      assert.equal(/\sdisabled(?:\s|>)/.test(save), !canSave);
      assert.equal((after.html.match(/data-image-prompt-variant-index=/g) || []).length, 4);
      assert.equal((after.html.match(/aria-pressed="true"/g) || []).length, 1);
      assert(after.html.includes(`data-image-prompt-variant-index="${index}" aria-pressed="true"`));
    });
  }
}
assert.equal(expectedViews, 246);

for (const locale of ["vi", "en", "zh"]) {
  for (const invalidKind of ["provider_called", "payment_started", "missing_result"]) {
    test(`${locale}: ${invalidKind} never produces a saved-description control`, () => {
      const row = fixture.rows[0];
      const bad = invalidKind === "missing_result" ? {} : {...row.result, [invalidKind]: true};
      const raw = {imagePromptComposerEnabled: true,
        capabilities: {"image-prompt-compose": true, "image-prompt-composer-save-memory": true},
        imagePromptComposerResult: bad, imagePromptComposerSaveSource: row.source};
      const view = render(current, locale, raw);
      assert(!view.html.includes('data-portal-action="image-prompt-composer-save-memory"'));
      assert.deepEqual(JSON.parse(JSON.stringify(view.state.imagePromptComposerResult)), {});
    });
  }
  test(`${locale}: arbitrary customer markup remains escaped and untranslated`, () => {
    const row = structuredClone(fixture.rows[0]), customer = 'Facebook TikTok media studio <img src=x onerror="evil()">';
    row.result.composer.title = customer;
    const view = render(current, locale, {imagePromptComposerEnabled: true,
      capabilities: {"image-prompt-compose": true}, imagePromptComposerResult: row.result});
    assert(view.html.includes(escape(customer)));
    assert(!view.html.includes('<img src=x onerror="evil()">'));
    assert.equal(view.state.imagePromptComposerResult.composer.title, customer);
  });
}
