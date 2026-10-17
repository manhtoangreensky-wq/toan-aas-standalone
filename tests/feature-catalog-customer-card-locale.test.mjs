import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const registrySource = fs.readFileSync(path.join(root, "copyfast_registry.py"), "utf8");
const featureSource = fs.readFileSync(path.join(root, "static/portal/portal-features.js"), "utf8");
const copyPath = path.join(root, "static/portal/portal-feature-catalog-copy.js");
const copySource = fs.existsSync(copyPath) ? fs.readFileSync(copyPath, "utf8") : "";
const pageSource = fs.readFileSync(path.join(root, "copyfast_pages.py"), "utf8");
const workerSource = fs.readFileSync(path.join(root, "static/portal/service-worker.js"), "utf8");
const messagesSource = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8");

const excludedRoutes = new Set([
  "/", "/welcome", "/login", "/register", "/password-recovery", "/status",
  "/legal", "/privacy", "/features",
]);
const familyRoutes = new Set([
  "/features/content", "/features/image", "/features/video", "/features/voice",
  "/features/music", "/features/subtitle", "/features/documents", "/features/support",
]);
const supportedGroups = new Set([
  "free_tools", "account", "wallet", "jobs", "content", "image", "video",
  "voice", "music", "subtitle", "documents", "support", "other",
]);

function visibleRegistryFeatures() {
  const seenKeys = new Set();
  const seenRoutes = new Set();
  const features = [];
  const pattern = /WebFeature\(\s*"([^"]+)"\s*,\s*"[^"]*"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"/g;
  for (const match of registrySource.matchAll(pattern)) {
    const [, key, sourceGroup, route] = match;
    if (sourceGroup === "admin" || route.startsWith("/admin") || excludedRoutes.has(route) || familyRoutes.has(route)) continue;
    if (seenKeys.has(key) || seenRoutes.has(route)) continue;
    const group = supportedGroups.has(sourceGroup) ? sourceGroup : "other";
    seenKeys.add(key);
    seenRoutes.add(route);
    features.push({ key, group, route });
  }
  return features;
}

function loadCopy() {
  assert.ok(copySource, "standalone feature-card locale copy bundle must exist");
  const window = {};
  vm.runInNewContext(copySource, { window, Object, Array, String });
  return window.TOANAASFeatureCatalogCopy;
}

const features = visibleRegistryFeatures();
const customerNonVideo = features.filter((feature) => feature.group !== "video");
const copy = copySource ? loadCopy() : null;

test("registry inventory is exactly 135 visible cards and keeps Video as a separate later wave", () => {
  assert.equal(features.length, 135);
  assert.equal(customerNonVideo.length, 108);
  assert.equal(features.filter((feature) => feature.group === "video").length, 27);
});

test("standalone catalogue has reviewed title and description for every non-Video card in vi/en/zh", () => {
  assert.ok(copy, "standalone feature-card locale copy bundle must exist");
  const expected = customerNonVideo.map((feature) => feature.key).sort();
  for (const locale of ["vi", "en", "zh"]) {
    const rows = copy[locale] || {};
    assert.deepEqual(Object.keys(rows).sort(), expected, `${locale} must cover all 108 non-Video cards, without hidden or duplicate keys`);
    for (const key of expected) {
      assert.ok(rows[key].title?.trim(), `${locale}.${key}.title must be nonempty`);
      assert.ok(rows[key].description?.trim(), `${locale}.${key}.description must be nonempty`);
    }
  }
});

test("Vietnamese and English card copy do not leak the other language", () => {
  assert.ok(copy, "standalone feature-card locale copy bundle must exist");
  const mixedVietnameseTerms = /\b(?:workflow|web-native|workspace|content|chat|prompt|caption|script|planning|canonical|core bridge|portal|catalogue|catalog|route|dashboard|metadata|delivery|ticket|provider|worker|backup|callback|execution|output|signed session|capability|readiness|engine|payment|brief|preview|export|voice studio|voice vault|clone|music|sfx|documents|image studio|studio|asset|library|reference|directory|registry|customer|system state|map route|audit|guarded|compatibility|job|tag|web app|account|checkout|tier|trial|receipt|self-review|incident|deploy)\b/i;
  for (const [key, row] of Object.entries(copy.vi)) {
    assert.doesNotMatch(`${row.title} ${row.description}`, mixedVietnameseTerms, `vi.${key} contains untranslated interface wording`);
  }
  for (const [key, row] of Object.entries(copy.en)) {
    assert.doesNotMatch(`${row.title} ${row.description}`, /[\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u024F]/u, `en.${key} contains Vietnamese text`);
  }
});

test("Chinese card copy translates generic English while preserving approved product names and acronyms", () => {
  assert.ok(copy, "standalone feature-card locale copy bundle must exist");
  const approved = new Set([
    "TOAN", "AAS", "BOT", "TELEGRAM", "PAYOS", "META", "FACEBOOK", "TIKTOK", "YOUTUBE",
    "ID", "CSRF", "PDF", "XU", "URL", "API", "SFX", "TTS", "ASR", "SRT", "VTT", "OCR",
    "USD", "VND", "QR", "AI", "MP3", "M4A", "CSV", "CRM", "SLA", "OTP", "MIME",
  ]);
  for (const [key, row] of Object.entries(copy.zh)) {
    const words = `${row.title} ${row.description}`.match(/[A-Za-z][A-Za-z0-9]*/g) || [];
    const unexpected = words.filter((word) => !approved.has(word.toUpperCase()));
    assert.deepEqual(unexpected, [], `zh.${key} contains untranslated wording: ${unexpected.join(", ")}`);
  }
});

test("catalog cards consume localized copy but preserve source search terms and route identity", () => {
  assert.ok(copy, "standalone feature-card locale copy bundle must exist");
  const start = featureSource.indexOf("function localizedFeatureCopy(");
  const end = featureSource.indexOf("\n  function featureCard(", start);
  assert.ok(start >= 0 && end > start, "a focused localized-feature projection must exist");
  const resolverSource = featureSource.slice(start, end);
  assert.match(featureSource.slice(end, featureSource.indexOf("\n  function renderGuarded(", end)), /localizedFeatureCopy\(feature, locale\)/);
  const context = vm.createContext({ FEATURE_COPY: copy, Object, String });
  vm.runInContext(`${resolverSource}\nglobalThis.resolveCopy = localizedFeatureCopy;`, context);
  const sourceFeature = { ...customerNonVideo[0], title: "Registry title", description: "Registry description", engine: { mode: "guarded" } };
  for (const locale of ["vi", "en", "zh"]) {
    const result = context.resolveCopy(sourceFeature, locale);
    assert.equal(result.title, copy[locale][sourceFeature.key].title);
    assert.equal(result.description, copy[locale][sourceFeature.key].description);
    assert.equal(result.route, sourceFeature.route);
    assert.equal(result.key, sourceFeature.key);
  }
  assert.match(featureSource, /\[displayFeature\.title,\s*displayFeature\.description,\s*feature\.title,\s*feature\.description,\s*feature\.key,\s*feature\.route/);
  assert.match(featureSource, /displayFeature\.title, displayFeature\.description/);
});

test("the light copy bundle loads before the standalone renderer and participates in fixed-shell caching", () => {
  assert.ok(copySource, "standalone feature-card locale copy bundle must exist");
  assert.ok(pageSource.indexOf("portal-feature-catalog-copy.js") < pageSource.indexOf("portal-features.js"));
  assert.match(workerSource, /"\/static\/portal\/portal-feature-catalog-copy\.js"/);
  const routeStart = pageSource.indexOf('if normalized == "/features":');
  const routeEnd = pageSource.indexOf("\n    build_id = _portal_build_id()", routeStart);
  assert.ok(routeStart >= 0 && routeEnd > routeStart, "the standalone feature route boundary must exist");
  const routeSource = pageSource.slice(routeStart, routeEnd);
  assert.match(routeSource, /"portal-i18n\.js"/, "the standalone route must remove the full workspace locale bundle");
  assert.match(routeSource, /portal-feature-catalog-copy\.js/, "the lightweight localized copy bundle must be injected on the feature route");
  assert.ok(messagesSource.includes('"featureCatalog.entry.wallet.title"'));
  assert.ok(messagesSource.includes('"featureCatalog.entry.asset_vault.title"'));
  assert.ok(messagesSource.includes('"featureCatalog.entry.partner_readiness.title"'));
  assert.ok(messagesSource.includes('"featureCatalog.entry.operations.title"'));
});
