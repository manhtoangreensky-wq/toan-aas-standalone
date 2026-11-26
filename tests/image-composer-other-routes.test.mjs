import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/image-composer-native-locale-contract.json", import.meta.url), "utf8"));
const current = pageMetaSources(), historical = {...current};
for (const [key, file] of [["portal", "static/portal/portal.js"], ["i18n", "static/portal/portal-i18n.js"]]) {
  historical[key] = execFileSync("git", ["show", contract.base + ":" + file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
}
const before = await pageMetaRenderer(historical), after = await pageMetaRenderer(current);
for (const locale of ["vi", "en", "zh"]) for (const route of [
  "/image-studio", "/image-hub", "/image/edit", "/documents", "/voice", "/image/quick-planner"
]) {
  test(`${locale}/${route}: Composer-specific changes preserve other route titles, attributes and controls`, () => {
    const old = before(locale, route, {}), now = after(locale, route, {});
    assert.equal(now.title, old.title);
    assert.equal(now.attributes, old.attributes);
    const controls = html => [...html.matchAll(/<(?:form|input|textarea|select|option|button|a)\b[^>]*>/g)].map(row => row[0]);
    assert.deepEqual(controls(now.html), controls(old.html));
  });
}
