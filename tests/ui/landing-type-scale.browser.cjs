// Measure rendered Landing typography in an isolated local QA browser.
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const assert = require("node:assert/strict");
const { chromium } = require(process.env.R189_PLAYWRIGHT_MODULE || "playwright");

const origin = process.env.R158_ORIGIN || "http://127.0.0.1:4178";
const outputDir = process.env.R189_OUT || process.env.R158_OUT || path.join(os.tmpdir(), "toanaas-r189a");
const phase = process.env.R189_PHASE || "before";
const viewports = [
  { id: "phone-360", width: 360, height: 800, deviceScaleFactor: 1 },
  { id: "tablet-768", width: 768, height: 1024, deviceScaleFactor: 1 },
  { id: "desktop-1440", width: 1440, height: 900, deviceScaleFactor: 1 },
  { id: "zoom-equivalent-720", width: 720, height: 450, deviceScaleFactor: 2 },
];
const locales = ["vi", "en", "zh"];
const themes = ["light", "dark"];
const cases = locales.flatMap((locale) => themes.flatMap((theme) => viewports.map((viewport) => ({ locale, theme, ...viewport }))));
const result = { run: "R189A_LANDING_RENDERED_TYPE_SCALE", phase, origin, cases: [], interaction: null, errors: [] };

function visibleTextMetrics() {
  const root = document.querySelector(".portal-landing");
  const rows = [];
  if (!root) return rows;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const text = (node.textContent || "").trim();
    const element = node.parentElement;
    if (!text || !element) continue;
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    const rects = [...range.getClientRects()].filter((rect) => rect.width > 0 && rect.height > 0);
    if (!rects.length) continue;
    const classes = typeof element.className === "string" ? element.className : "";
    rows.push({ text, tag: element.tagName.toLowerCase(), classes, size: Number.parseFloat(style.fontSize), lineHeight: style.lineHeight });
  }
  return rows;
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  process.env.TEMP = outputDir;
  process.env.TMP = outputDir;
  process.env.TMPDIR = outputDir;
  console.log(`R189_TMPDIR ${os.tmpdir()}`);
  const browser = await chromium.launch({ headless: true,
    ...(process.env.R189_CHROME_PATH ? { executablePath: process.env.R189_CHROME_PATH } : {}),
    args: ["--disable-background-networking", "--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=127.0.0.1;localhost"],
  });
  try {
    for (const fixture of cases) {
      const context = await browser.newContext({
        viewport: { width: fixture.width, height: fixture.height },
        deviceScaleFactor: fixture.deviceScaleFactor,
        reducedMotion: "reduce",
        serviceWorkers: "block",
      });
      await context.route("**/*", (route) => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
      const page = await context.newPage();
      page.on("pageerror", (error) => result.errors.push(`${fixture.locale}/${fixture.theme}/${fixture.id}: ${error.message}`));
      page.on("response", (response) => {
        if (response.url().startsWith(origin) && response.status() >= 500) result.errors.push(`${response.status()} ${response.url()}`);
      });
      await page.goto(`${origin}/welcome?lang=${fixture.locale}`, { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.locator(".portal-landing").waitFor({ state: "visible", timeout: 10000 });
      await page.evaluate(() => document.fonts && document.fonts.ready);
      await page.locator(`[data-portal-theme-set="${fixture.theme}"]`).click();
      await page.waitForFunction((theme) => document.documentElement.getAttribute("data-portal-theme") === theme, fixture.theme, { timeout: 5000 });
      const measured = await page.evaluate(visibleTextMetrics);
      const sizes = [...new Set(measured.map((row) => row.size))].sort((left, right) => left - right);
      const minSize = sizes[0] ?? 0;
      const h2Sizes = await page.locator(".portal-landing h2").evaluateAll((nodes) => nodes.filter((node) => node.getClientRects().length).map((node) => Number.parseFloat(getComputedStyle(node).fontSize)));
      const heroBodySizes = await page.locator(".portal-landing-hero-copy > p").evaluateAll((nodes) => nodes.filter((node) => node.getClientRects().length).map((node) => Number.parseFloat(getComputedStyle(node).fontSize)));
      const stepMetrics = await page.locator(".portal-landing-preview-steps span").evaluateAll((nodes) => nodes.map((node) => ({
        size: Number.parseFloat(getComputedStyle(node).fontSize),
        text: node.textContent.trim(),
        overflowX: node.scrollWidth > node.clientWidth + 1,
        overflowY: node.scrollHeight > node.clientHeight + 1,
      })));
      const pageMetrics = await page.evaluate(() => ({
        lang: document.documentElement.lang,
        theme: document.documentElement.getAttribute("data-portal-theme"),
        pageWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        landingTextLength: document.querySelector(".portal-landing")?.innerText.trim().length || 0,
      }));
      const expectedH2 = fixture.width <= 767 ? 28 : 32;
      const expectedDocumentLocale = fixture.locale === "zh" ? "zh-CN" : fixture.locale;
      const roleSpecifications = [
        { role: "secondary-label", selector: ".portal-landing-brand small, .portal-landing-hero-stage-label, .portal-landing-kicker, .portal-landing-section-heading > span, .portal-landing-trust-copy > span, .portal-landing-preview-steps small, .portal-landing-studio-index", expected: 12 },
        { role: "control", selector: ".portal-landing-nav-links a, .portal-landing-locale-link, .portal-landing-nav-actions .portal-button, .portal-landing-hero-actions .portal-button, .portal-landing-theme-switch button, .portal-landing-preview-bar strong, .portal-landing-preview-heading b, .portal-landing-preview-callout p, .portal-landing-preview-callout strong, .portal-landing-studio em, .portal-landing-spotlight .portal-button, .portal-landing-discovery-cta, .portal-landing-final .portal-button, .portal-landing-final .portal-pwa-fab-trigger", expected: 14 },
        { role: "body", selector: ".portal-landing-hero-copy > p, .portal-landing-feature-strip p, .portal-landing-spotlight-copy > p, .portal-landing-studio > span:not(.portal-landing-studio-icon):not(.portal-landing-studio-index), .portal-landing-workflow li p, .portal-landing-trust-grid p, .portal-landing-final p", expected: 16 },
        { role: "card-title", selector: ".portal-landing-preview-heading > span, .portal-landing-studio strong, .portal-landing-workflow li strong, .portal-landing-trust-grid strong", expected: 20 },
        { role: "feature-title", selector: ".portal-landing-feature-strip strong", expected: 16 },
        { role: "preview-copy", selector: ".portal-landing-product-surface-copy", expected: 12 },
        { role: "footer-copy", selector: ".portal-landing-footer > span, .portal-landing-footer > div a", expected: 14 },
      ];
      const roleMetrics = await page.evaluate((specifications) => specifications.map((specification) => {
        const sizes = [...document.querySelectorAll(specification.selector)]
          .filter((node) => node.getClientRects().length)
          .map((node) => Number.parseFloat(getComputedStyle(node).fontSize));
        return { role: specification.role, expected: specification.expected, sizes };
      }), roleSpecifications);
      const failures = [];
      if (sizes.length > 6) failures.push(`unique visible type sizes ${sizes.length} > 6`);
      if (minSize < 12) failures.push(`smallest visible type size ${minSize}px < 12px`);
      if (!h2Sizes.length || h2Sizes.some((size) => size !== expectedH2)) failures.push(`H2 sizes ${h2Sizes.join(",")} expected ${expectedH2}px`);
      for (const role of roleMetrics) {
        if (!role.sizes.length || role.sizes.some((size) => size !== role.expected)) failures.push(`${role.role} sizes ${role.sizes.join(",")} expected ${role.expected}px`);
      }
      if (!heroBodySizes.length || heroBodySizes.some((size) => size !== 16)) failures.push(`hero body sizes ${heroBodySizes.join(",")} expected 16px`);
      if (stepMetrics.length !== 4) failures.push(`preview step count ${stepMetrics.length} expected 4`);
      if (stepMetrics.some((step) => step.size < 12 || step.overflowX || step.overflowY)) failures.push("preview step label is too small or clipped");
      if (pageMetrics.lang !== expectedDocumentLocale) failures.push(`document locale ${pageMetrics.lang} expected ${expectedDocumentLocale}`);
      if (pageMetrics.theme !== fixture.theme) failures.push(`theme ${pageMetrics.theme} expected ${fixture.theme}`);
      if (pageMetrics.pageWidth > pageMetrics.viewportWidth + 1) failures.push("document has horizontal overflow");
      if (pageMetrics.landingTextLength < 100) failures.push("Landing is blank or missing meaningful content");
      const row = { locale: fixture.locale, theme: fixture.theme, viewport: fixture.id, dpr: fixture.deviceScaleFactor, sizes, minSize, h2Sizes, roleMetrics, heroBodySizes, stepMetrics, ...pageMetrics, failures };
      result.cases.push(row);
      if (fixture.locale === "vi" && fixture.theme === "dark" && fixture.id === "phone-360") await page.screenshot({ path: path.join(outputDir, `r189a-${phase}-vi-dark-360.png`), fullPage: false });
      if (fixture.locale === "en" && fixture.theme === "light" && fixture.id === "desktop-1440") await page.screenshot({ path: path.join(outputDir, `r189a-${phase}-en-light-1440.png`), fullPage: false });
      await context.close();
    }

    const interactionContext = await browser.newContext({ viewport: { width: 360, height: 800 }, reducedMotion: "reduce", serviceWorkers: "block" });
    await interactionContext.route("**/*", (route) => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const interactionPage = await interactionContext.newPage();
    await interactionPage.goto(`${origin}/welcome?lang=vi`, { waitUntil: "domcontentloaded", timeout: 20000 });
    await interactionPage.locator(".portal-landing").waitFor({ state: "visible", timeout: 10000 });
    await interactionPage.locator('[data-portal-theme-set="dark"]').click();
    await interactionPage.waitForFunction(() => document.documentElement.getAttribute("data-portal-theme") === "dark", null, { timeout: 5000 });
    await interactionPage.locator('.portal-landing a[href="/welcome?lang=en"]').click();
    await interactionPage.waitForFunction(() => document.documentElement.lang === "en", null, { timeout: 10000 });
    result.interaction = {
      path: "Landing VI sáng → chọn tối → chọn English",
      locale: await interactionPage.locator("html").getAttribute("lang"),
      theme: await interactionPage.locator("html").getAttribute("data-portal-theme"),
    };
    if (result.interaction.locale !== "en" || result.interaction.theme !== "dark") result.errors.push("Locale/theme interaction did not preserve the selected state");
    await interactionContext.close();

    result.failedCases = result.cases.filter((row) => row.failures.length);
    result.failedCount = result.failedCases.length;
    fs.writeFileSync(path.join(outputDir, `r189a-${phase}-matrix.json`), JSON.stringify(result, null, 2));
    for (const row of result.cases) console.log(`R189A_CASE ${JSON.stringify({ locale: row.locale, theme: row.theme, viewport: row.viewport, sizes: row.sizes, minSize: row.minSize, h2Sizes: row.h2Sizes, failures: row.failures })}`);
    console.log(`R189A_MATRIX cases=${result.cases.length} failed=${result.failedCount} errors=${result.errors.length} interaction=${JSON.stringify(result.interaction)}`);
    assert.equal(result.cases.length, 24, "The full locale/theme/viewport matrix must complete");
    assert.equal(result.errors.length, 0, "Rendered UI must not produce page errors or local server 5xx responses");
    assert.equal(result.failedCount, 0, "Landing type roles must meet the R189A contract in every browser state");
    console.log("R189A_LANDING_TYPE_SCALE_PASS24");
  } finally {
    await browser.close();
  }
})().catch((error) => {
  result.fatal = error.stack;
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, `r189a-${phase}-matrix.json`), JSON.stringify(result, null, 2));
  console.error(error.stack);
  process.exitCode = 1;
});
