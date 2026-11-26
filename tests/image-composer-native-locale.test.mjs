import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const root = new URL("../", import.meta.url);
const read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const contract = JSON.parse(read("tests/fixtures/image-composer-native-locale-contract.json"));
const hash = value => createHash("sha256").update(value).digest("hex");
const escape = text => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

for (const pin of contract.applicationSources) {
  test(`physical Composer source retains fixed release and only approved records: ${pin.file}`, () => {
    assert.equal(contract.base, "6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792");
    assert.equal(contract.records.length, 39);
    assert.equal(contract.copyRows.length, 85);
    let expected = execFileSync("git", ["show", contract.base + ":" + pin.file], {
      encoding: "utf8", maxBuffer: 30e6
    }).replace(/\r\n/g, "\n");
    assert.equal(hash(expected), pin.beforeLfSha256);
    for (const row of [...contract.records, ...(contract.amendments || [])].filter(row => row.file === pin.file)) {
      assert.equal(expected.split(row.old).length - 1, 1, "Unique reviewed OLD record");
      expected = expected.replace(row.old, () => row.new);
    }
    assert.equal(hash(expected), pin.afterLfSha256);
    assert.equal(hash(read(pin.file)), hash(expected), "Current application must contain exactly the accepted worker changes");
  });
}

const renderer = await pageMetaRenderer(pageMetaSources());
for (const [localeIndex, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: actual Composer frame renders native fixed copy and has no vacated explanatory panels`, () => {
    const value = key => {
      const row = contract.copyRows.find(row => row[0] === key);
      assert(row, key);
      return row[localeIndex + 1];
    };
    const raw = {imagePromptComposerEnabled: true, capabilities: {"image-prompt-compose": true}};
    const view = renderer(locale, "/image/prompt-composer", raw);
    const html = view.qa.renderPage(view.page, {...view.context, ...raw});
    assert.equal(view.title, value("page.title") + " · TOAN AAS");
    for (const key of ["intro.kicker", "intro.title", "intro.body", "form.title", "form.description", "form.submit", "empty.title"]) {
      assert(html.includes(escape(value(key))), `Native ${locale} copy missing for ${key}`);
    }
    assert.match(html, /portal-image-composer-customer/);
    assert.doesNotMatch(html, /portal-image-prompt-composer-boundary|Scope rõ ràng|<aside\b|<dl>/);
    assert.match(html, /data-portal-no-transient/);
    assert.match(html, /data-portal-action="image-prompt-compose"/);
    for (const field of ["goal_code", "ratio", "language", "custom_goal", "subject", "style_preset", "style"]) {
      assert(html.includes(`name="${field}"`), `Preserve ${field}`);
    }
  });
}
