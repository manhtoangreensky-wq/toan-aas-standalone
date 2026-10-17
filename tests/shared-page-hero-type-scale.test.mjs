import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const portalCss = fs.readFileSync(path.join(root, "static", "portal", "portal.css"), "utf8");
const themeCss = fs.readFileSync(path.join(root, "static", "portal", "portal-theme.css"), "utf8");
const shellHtml = fs.readFileSync(path.join(root, "templates", "portal_shell.html"), "utf8");

function rulesForSelector(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return [...source.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "g"))].map((match) => match[1]);
}

test("shared route hero descriptions use the 16px body scale", () => {
  assert.match(portalSource, /<p class="portal-description">\$\{safeText\(localizedPageDescription\(page\)\)\}<\/p>/);
  const rule = themeCss.match(/\.portal-page > \.portal-hero \.portal-description,\s*\.portal-shell\[data-portal-app-kind="admin"\] \.portal-page\.portal-admin-home > \.portal-hero \.portal-description\s*\{([^}]*)\}/);
  assert.ok(rule, "shared customer and Admin hero descriptions must have an explicit shared rule");
  assert.match(rule[1], /font-size:\s*16px\s*;/);
  assert.match(rule[1], /line-height:\s*1\.65\s*;/);
});

test("the final shared rule wins route-specific compact description styling", () => {
  assert.match(portalCss, /\.portal-page:is\(\.portal-image-create, \.portal-image-suite-hub\)[\s\S]*?font-size:\s*14px/);
  const adminSelector = ".portal-shell[data-portal-app-kind=\"admin\"] .portal-page.portal-admin-home > .portal-hero .portal-description";
  const adminRules = rulesForSelector(themeCss, adminSelector);
  assert.ok(adminRules.length >= 2, "the shared override must follow the earlier Admin mobile rule");
  assert.match(adminRules.at(-1), /font-size:\s*16px\s*;/);
});

test("the theme stylesheet is loaded after the base stylesheet", () => {
  assert.ok(shellHtml.indexOf("/static/portal/portal.css") < shellHtml.indexOf("/static/portal/portal-theme.css"));
});

test("primary in-app H1 rules meet the 32px minimum and 1.25 leading", () => {
  assert.match(portalCss, /\.portal-title\s*\{[^}]*font-size:\s*clamp\(32px,\s*3vw,\s*42px\)[^}]*line-height:\s*1\.25\s*;/);
  assert.match(portalCss, /\.portal-dashboard-overview h1\s*\{[^}]*font-size:\s*clamp\(32px,\s*3\.6vw,\s*46px\)[^}]*line-height:\s*1\.25\s*;/);
  assert.match(portalCss, /\.portal-dashboard-overview h1\s*\{\s*font-size:\s*clamp\(32px,\s*9vw,\s*40px\);\s*line-height:\s*1\.25;/);
  assert.match(portalCss, /\.portal-workspace-command-center \.portal-dashboard-overview h1\s*\{[^}]*font-size:\s*clamp\(32px,\s*3\.4vw,\s*44px\)[^}]*line-height:\s*1\.25\s*;/);
  assert.match(themeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-page\.portal-admin-home > \.portal-hero \.portal-title\s*\{[^}]*font-size:\s*clamp\(32px,\s*3vw,\s*40px\)[^}]*line-height:\s*1\.25\s*;/);
  assert.match(themeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-page\.portal-admin-home > \.portal-hero \.portal-title\s*\{\s*max-width:\s*none;\s*margin-block:\s*0;\s*font-size:\s*32px;\s*line-height:\s*1\.25;/);
});

test("the rendered Admin titlebar uses true H1/body text sizes", () => {
  assert.match(portalSource, /class="portal-admin-titlebar"[\s\S]*?<h1>\$\{safeText\(adminText\("title"/);
  assert.match(themeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-admin-titlebar h1\s*\{[^}]*font-size:\s*clamp\(32px,\s*3vw,\s*40px\)[^}]*line-height:\s*1\.25\s*;/);
  assert.match(themeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-admin-titlebar p\s*\{[^}]*font-size:\s*16px\s*;[^}]*line-height:\s*1\.625\s*;/);
  assert.match(themeCss, /\.portal-shell\[data-portal-app-kind="admin"\] \.portal-admin-session-status em\s*\{[^}]*font-size:\s*14px\s*;/);
});

test("shared section H2 uses the 24px role and stacks with actions on mobile", () => {
  assert.match(portalCss, /\.portal-section-heading h2\s*\{[^}]*font-size:\s*24px;[^}]*line-height:\s*1\.25;/);
  for (const selector of [
    ".portal-admin-work-queues .portal-section-heading h2",
    ".portal-stewardship-section .portal-section-heading h2",
    ".portal-tax-readiness-section .portal-section-heading h2",
    ".portal-postback-readiness-section .portal-section-heading h2",
    ".portal-job-recovery-section .portal-section-heading h2",
  ]) {
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const rule = portalCss.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
    assert.ok(rule, `${selector} must keep a route-specific type rule`);
    assert.match(rule[1], /font-size:\s*(?:24px|clamp\(\s*24px,)/);
    assert.match(rule[1], /line-height:\s*1\.25\s*;/);
  }
  const mobileBlocks = [...portalCss.matchAll(/@media\s*\(max-width:\s*700px\)\s*\{([\s\S]*?)^\}/gm)];
  assert.ok(mobileBlocks.some((block) => /\.portal-section-heading\s*\{\s*align-items:\s*flex-start;\s*flex-direction:\s*column;\s*\}/.test(block[1])));
});
