import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(root, "static", "portal", "portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const themeSource = fs.readFileSync(path.join(root, "static", "portal", "portal-theme.css"), "utf8");

function loadMessages() {
  const document = { title: "", documentElement: { lang: "", setAttribute() {} } };
  const window = { document, navigator: { language: "vi" }, dispatchEvent() {}, CustomEvent: function CustomEvent() {} };
  const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp });
  vm.runInContext(i18nSource, context, { filename: "portal-i18n.js" });
  return window.TOANAASI18n.messages;
}

const messages = loadMessages();
const landingKeys = Object.keys(messages.vi).filter((key) => key.startsWith("landing.")).sort();
assert.equal(landingKeys.length, 92);
const allowedChineseLatin = new Set(["TOAN", "AAS", "TELEGRAM", "BOT", "AI", "ASR", "SRT", "VTT", "PDF", "OCR", "PAYOS", "XU"]);
const mixedVietnameseTerms = /\b(?:web app|workspace|workflow|brief|project|studio|engine|companion|capability|prompt|output|preview|delivery|self-review|content|audio|collection|direction|cue sheet|authoring|signed session|ownership|audit|browser|provider|ledger|payment|job|file|scene|storyboard|series|input|image|voice|cta|canonical|quote|policy|adapter|owner|url|private|asset|chat|hook|script|caption|dubbing|workflow|webhook)\b/i;

test("landing hero emphasis preserves the full title in all three locales", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const title = messages[locale]["landing.hero.title"];
    const emphasis = messages[locale]["landing.hero.titleEmphasis"];
    assert.ok(title && emphasis, `${locale} needs both title and emphasis copy`);
    assert.ok(title.endsWith(emphasis), `${locale} emphasis must be a suffix of the complete title`);
    assert.equal(`${title.slice(0, -emphasis.length)}${emphasis}`, title);
  }

  const landing = portalSource.slice(portalSource.indexOf("function renderLanding(page, context)"), portalSource.indexOf("function renderVideoFinalization"));
  assert.match(landing, /const heroTitleMarkup = heroTitleEmphasis && heroTitle\.endsWith\(heroTitleEmphasis\)/);
  assert.match(landing, /<span class="portal-landing-title-emphasis">\$\{safeText\(heroTitleEmphasis\)\}<\/span>/);
  assert.match(landing, /<h1 id="portal-landing-title">\$\{heroTitleMarkup\}<\/h1>/);
});

test("landing copy is clean Vietnamese and English, with only approved Chinese technical names", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const keys = Object.keys(messages[locale]).filter((key) => key.startsWith("landing.")).sort();
    assert.deepEqual(keys, landingKeys, `${locale} landing keys must stay complete`);
  }

  const vietnameseIssues = landingKeys
    .filter((key) => mixedVietnameseTerms.test(messages.vi[key]))
    .map((key) => `vi.${key}: ${messages.vi[key]}`);
  assert.deepEqual(vietnameseIssues, [], vietnameseIssues.join("; "));

  for (const key of landingKeys) {
    assert.doesNotMatch(messages.en[key], /[\u00C0-\u024F]/u, `en.${key}: ${messages.en[key]}`);
    const latinWords = messages.zh[key].match(/[A-Za-z][A-Za-z0-9]*/g) || [];
    const unexpected = latinWords.filter((word) => !allowedChineseLatin.has(word.toUpperCase()));
    assert.deepEqual(unexpected, [], `zh.${key}: ${unexpected.join(", ")} in ${messages.zh[key]}`);
  }
});

function luminance(hex) {
  const channels = hex.slice(1).match(/.{2}/g).map((channel) => parseInt(channel, 16) / 255);
  const linear = channels.map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(foreground, background) {
  const [light, dark] = [luminance(foreground), luminance(background)].sort((left, right) => right - left);
  return (light + 0.05) / (dark + 0.05);
}

function colorToken(name) {
  const match = themeSource.match(new RegExp(`--${name}:\\s*(#[0-9a-f]{6})\\s*;`, "i"));
  assert.ok(match, `missing --${name} color token`);
  return match[1];
}

function rulesFor(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return [...themeSource.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "g"))].map((match) => match[1]);
}

test("hero emphasis uses the theme accent with readable contrast and mobile body text stays 16px", () => {
  const emphasisRule = themeSource.match(/\.portal-landing-title-emphasis\s*\{(?<body>[^}]*)\}/);
  assert.ok(emphasisRule, "landing hero emphasis rule must exist");
  assert.match(emphasisRule.groups.body, /color:\s*var\(--portal-accent-deep\)/);
  assert.match(emphasisRule.groups.body, /font-weight:\s*(?:700|800|900)/);

  const light = contrast(colorToken("portal-action"), colorToken("portal-app-canvas"));
  const dark = contrast(colorToken("portal-dark-action"), colorToken("portal-dark-app-canvas"));
  assert.ok(light >= 3, `large light-theme headline contrast ${light.toFixed(2)} must be at least 3:1`);
  assert.ok(dark >= 3, `large dark-theme headline contrast ${dark.toFixed(2)} must be at least 3:1`);

  const mediaBlocks = [...themeSource.matchAll(/@media\s*\([^\n]+\)\s*\{([\s\S]*?)^\}/gm)].map((match) => match[1]);
  assert.ok(mediaBlocks.some((block) => block.includes(".portal-landing-hero p,") && /font-size:\s*16px/.test(block)));
});

test("landing explanatory paragraphs use 16px text and readable line height", () => {
  const selectors = [
    ".portal-landing-feature-strip p",
    ".portal-landing-spotlight-copy > p",
    ".portal-landing-studio > span:not(.portal-landing-studio-icon):not(.portal-landing-studio-index)",
    ".portal-landing-workflow li p",
    ".portal-landing-trust-grid p",
  ];
  for (const selector of selectors) {
    const rules = rulesFor(selector);
    assert.ok(rules.length, `${selector} must have an explicit type rule`);
    const readable = rules.some((body) => {
      const size = body.match(/font-size:\s*(\d+(?:\.\d+)?)px/);
      const line = body.match(/line-height:\s*(\d+(?:\.\d+)?)/);
      return size && Number(size[1]) >= 16 && line && Number(line[1]) >= 1.625;
    });
    assert.ok(readable, `${selector} must use 16px+ text and line-height >=1.625`);
  }
});

test("landing groups secondary, control, and card-title text into its type roles", () => {
  const roles = [
    [
      ".portal-landing :is(.portal-landing-brand small, .portal-landing-hero-stage-label, .portal-landing-kicker, .portal-landing-section-heading > span, .portal-landing-trust-copy > span, .portal-landing-preview-steps small, .portal-landing-studio-index)",
      12,
    ],
    [
      ".portal-landing :is(.portal-landing-nav-links a, .portal-landing-locale-link, .portal-landing-nav-actions .portal-button, .portal-landing-hero-actions .portal-button, .portal-landing-theme-switch button, .portal-landing-preview-bar strong, .portal-landing-preview-heading b, .portal-landing-preview-callout p, .portal-landing-preview-callout strong, .portal-landing-studio em, .portal-landing-spotlight .portal-button, .portal-landing-final .portal-button, .portal-landing-footer)",
      14,
    ],
    [
      ".portal-landing :is(.portal-landing-preview-heading > span, .portal-landing-studio strong, .portal-landing-workflow li strong, .portal-landing-trust-grid strong)",
      20,
    ],
    [".portal-landing .portal-landing-feature-strip strong", 16],
    [".portal-landing .portal-landing-product-surface-copy", 12],
  ];

  for (const [selector, size] of roles) {
    const roleRules = rulesFor(selector);
    assert.ok(roleRules.some((body) => new RegExp(`font-size:\\s*${size}px;`).test(body)), `${selector} must use ${size}px`);
  }
});

test("landing H2 headings use one 28px mobile and 32px wider-screen role", () => {
  const roleSelector = String.raw`\.portal-landing :is\(\.portal-landing-section h2, \.portal-landing-workflow h2, \.portal-landing-trust h2, \.portal-landing-final h2, \.portal-landing-spotlight h2\)`;
  assert.ok(new RegExp(`${roleSelector}\\s*\\{[^}]*font-size:\\s*32px;`).test(themeSource), "Landing H2 should share a 32px desktop rule");
  assert.ok(new RegExp(`@media\\s*\\(max-width:\\s*767px\\)[\\s\\S]*?${roleSelector}\\s*\\{[^}]*font-size:\\s*28px;`).test(themeSource), "Landing H2 should share a 28px mobile rule");
});

test("landing editorial headings use the checklist line-height without changing the type scale", () => {
  for (const selector of [".portal-landing-hero h1", ".portal-landing-spotlight h2"]) {
    const rules = rulesFor(selector);
    const declaredLineHeights = rules.flatMap((body) => [...body.matchAll(/line-height:\s*(\d+(?:\.\d+)?)/g)].map((match) => Number(match[1])));
    assert.equal(declaredLineHeights.at(-1), 1.25, `${selector} effective line-height must meet the checklist`);
  }

  assert.match(
    themeSource,
    /\.portal-landing-section h2,\s*\.portal-landing-workflow h2,\s*\.portal-landing-trust h2,\s*\.portal-landing-final h2\s*\{[^}]*line-height:\s*1\.25;/
  );
});
