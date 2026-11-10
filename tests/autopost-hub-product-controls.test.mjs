import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { renderChild } from './helpers/publishing-child-render.mjs';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portal = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const css = fs.readFileSync(path.join(repoRoot, "static/portal/portal.css"), "utf8");
const i18n = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(i18n, context);
const messages = context.TOANAASI18n.messages;
const start = portal.indexOf("function renderAutoPostHub(page, context)");
const end = portal.indexOf("function renderPublishReviewPack(page, context)", start);
assert.ok(start >= 0 && end > start, "AutoPost renderer boundary exists");
const renderer = portal.slice(start, end);
const autopostKeys = Object.keys(messages.vi).filter((key) => /^autopostHub\./.test(key));

test("Publishing maps only the three existing operational destinations", () => {
  assert.match(portal, /customerPage\("\/publishing", "AutoPost Hub"/);
  assert.match(portal, /layout: "autopost-hub", type: "autopost-hub"/);
  assert.match(portal, /case "autopost-hub": return renderAutoPostHub\(page, context\);/);
  const view=renderChild('vi','/publishing',{});
  const links=[...view.html.matchAll(/<a\b[^>]*href="([^"]*)"/g)].map(m=>m[1]);
  assert.deepEqual(links,['/content/channel-strategy','/calendar','/content/publish-review']);
  assert.equal(view.html.includes('data-autopost-source='),false);
  assert.equal(view.html.includes('portal-autopost-steps'),false);
});

test("AutoPost Hub keeps planning presentation separate from external execution", () => {
  for (const token of [
    '"/content/channel-strategy"',
    '"/calendar"',
    '"/content/publish-review"'
  ]) assert.ok(renderer.includes(token), `missing AutoPost contract: ${token}`);
  assert.doesNotMatch(renderer, /fetch\s*\(|api\s*\(|providerCall|wallet|PayOS|createJob/i);
  assert.doesNotMatch(renderChild('vi','/publishing',{}).html,/type="button" disabled/);
});

test("AutoPost Hub fixed chrome is balanced across VI/EN/ZH", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => /^autopostHub\./.test(key)).sort());
  assert.deepEqual(keysets[1], keysets[0], "VI and EN AutoPost keys must match");
  assert.deepEqual(keysets[2], keysets[0], "VI and ZH AutoPost keys must match");
  assert.ok(autopostKeys.length >= 60, "AutoPost catalogue must cover source, steps, lanes and boundaries");
  for (const key of [
    "autopostHub.page.title",
    "autopostHub.source.topic.title",
    "autopostHub.source.plan.body",
    "autopostHub.channels.status",
    "autopostHub.queue.status",
    "autopostHub.boundary.title",
    "autopostHub.boundary.metricsState"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], `missing AutoPost locale copy: ${key}`);
  }
});

test("AutoPost Hub uses the existing blue/teal system and vertical mobile layout", () => {
  for (const selector of [
    ".portal-autopost-hub",
    ".portal-autopost-intro",
    ".portal-autopost-steps",
    ".portal-autopost-source",
    ".portal-autopost-boundary-grid"
  ]) assert.match(css, new RegExp(selector.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")));
  assert.ok(css.includes("@media (max-width: 620px)"), "mobile breakpoint exists");
  assert.match(css, /\.portal-autopost-intro\s*\{[^}]*var\(--portal-surface/);
  assert.match(css, /\.portal-autopost-steps ol\s*\{[^}]*grid-template-columns:\s*repeat\(5/);
  assert.match(css, /@media \(max-width: 620px\)[\s\S]*\.portal-autopost-steps ol, \.portal-autopost-boundary-grid \{ grid-template-columns: 1fr; }/);
  assert.doesNotMatch(css, /\.portal-autopost[^}]*background:\s*(?:#000|black)/i);
});
