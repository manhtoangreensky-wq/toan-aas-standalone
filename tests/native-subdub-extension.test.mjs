import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const rows = JSON.parse(fs.readFileSync(new URL("./fixtures/native-subdub-extension-copy.json", import.meta.url), "utf8"));
const render = await pageMetaRenderer(pageMetaSources());
const escape = text => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  test(`${locale}: actual SubDub banner is fully native, offers the real archive and never links to the Store homepage`, () => {
    const view = render(locale, "/subdub", {});
    const start = view.html.indexOf('<section class="portal-card portal-card-pad portal-subdub-extension-card"');
    assert(start >= 0);
    const end = view.html.indexOf("</section>", start);
    const banner = view.html.slice(start, end + 10);
    for (const row of rows) assert(banner.includes(escape(row[index + 1])), row[0]);
    assert(!banner.includes("chromewebstore.google.com/detail/toan-aas-live-translate"));
    assert.equal((banner.match(/<a\b/g) || []).length, 1);
    assert(banner.includes('href="/api/v1/live-translate/extension-download"'));
    assert(banner.includes('download="toan-aas-chrome-live-translate.zip"'));
    assert.match(banner, /<details\b[^>]*class="portal-subdub-extension-guide"[^>]*>/);
    assert.doesNotMatch(banner.match(/<details\b[^>]*>/)?.[0] || "", /\bopen\b/);
    assert.equal((banner.match(/class="portal-subdub-extension-step"/g) || []).length, 3);
    assert(!banner.includes('style="'), "Banner must use scoped theme rules, not hardcoded inline colors");
  });
}
