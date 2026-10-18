import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const catalogue = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const theme = fs.readFileSync("static/portal/portal-theme.css", "utf8");

function functionSource(name) {
  const start = portal.indexOf(`  function ${name}(`);
  const end = portal.indexOf("\n  }", start) + 4;
  assert.ok(start >= 0 && end > start, `missing production function ${name}`);
  return portal.slice(start, end);
}

function createHarness(locale = "vi") {
  const context = {
    MUSIC_PRODUCT_ROUTES: Object.freeze(["/music/create", "/music/song"]),
    normalizePath: (value) => String(value || "/").split("?")[0].replace(/\/$/, "") || "/",
    safeText: (value) => String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;"),
    uiText: null
  };
  vm.createContext(context);
  vm.runInContext(catalogue, context);
  context.TOANAASI18n.setLocale(locale, { emit: false });
  context.uiText = (key, fallback, params) => context.TOANAASI18n.has(key)
    ? context.TOANAASI18n.t(key, params)
    : fallback;
  vm.runInContext([
    functionSource("musicProductText"),
    functionSource("musicProductOptionLabel"),
    functionSource("musicProductRouteMode"),
    functionSource("musicProductFields"),
    functionSource("renderMusicProductGuidance"),
    functionSource("flowQuoteExpiry"),
    functionSource("flowHasFreshEstimate")
  ].join("\n"), context);
  return context;
}

test("Music tiers: exactly three canonical tiers with unique labels and valid selection", () => {
  const context = createHarness("vi");
  const musicFields = [
    { name: "tier", label: "Gói chất lượng", control: "select", options: [{ value: "basic", label: "Cơ bản" }, { value: "standard", label: "Tiêu chuẩn" }, { value: "premium", label: "Cao cấp" }] }
  ];
  const processed = context.musicProductFields(musicFields, "/music/create");
  const tierField = processed.find((f) => f.name === "tier");
  assert.ok(tierField, "tier field must exist");
  assert.equal(tierField.options.length, 3, "must have exactly 3 canonical tiers");
  const values = tierField.options.map((o) => o.value);
  assert.deepEqual(values, ["basic", "standard", "premium"]);
  const labels = tierField.options.map((o) => o.label);
  assert.equal(new Set(labels).size, 3, "tier labels must be distinct");
  assert.doesNotMatch(labels.join(" "), /Xu|\d/, "tier labels must not have hardcoded prices");
});

test("Song vs Instrumental mode: song-only controls isolated from background music", () => {
  const context = createHarness("vi");
  const allFields = [
    { name: "brief", control: "textarea" },
    { name: "tier", control: "select", options: ["basic", "standard", "premium"] },
    { name: "mode", control: "select", options: ["lyrics", "melody", "custom"] },
    { name: "vocal_mode", control: "select", options: ["auto", "male", "female", "duet"] },
    { name: "lyrics", control: "textarea" },
    { name: "song_length_mode", control: "select", options: ["seconds", "half", "full"] },
    { name: "duration_seconds", control: "input" }
  ];
  const bg = context.musicProductFields(allFields, "/music/create");
  const song = context.musicProductFields(allFields, "/music/song");

  assert.equal(context.musicProductRouteMode("/music/create"), "background");
  assert.equal(context.musicProductRouteMode("/music/song"), "song");

  for (const name of ["lyrics", "vocal_mode", "song_length_mode"]) {
    assert.equal(bg.find((f) => f.name === name).disabled, true, `background must disable ${name}`);
    assert.notEqual(song.find((f) => f.name === name).disabled, true, `song must enable ${name}`);
  }
});

test("Prompt and Suggestions: prompt input is required and suggestions board is guarded", () => {
  assert.match(portal, /name: "brief"[\s\S]*?required: true/);
  assert.match(portal, /name: "brief"[\s\S]*?minLength: 1/);
  const context = createHarness("vi");
  const html = context.renderMusicProductGuidance({ path: "/music/song", routePath: "/music/song" }, {});
  assert.match(html, /data-music-suggestion-board="guarded"/);
  assert.equal((html.match(/data-music-suggestion-card=/g) || []).length, 3);
  assert.match(html, /status\.pending|Chưa có dữ liệu/);
});

test("Editor capability: interactive workbench is withheld for music routes", () => {
  const workbenchFn = functionSource("renderInteractiveFeatureWorkbench");
  assert.match(workbenchFn, /if \(path\.startsWith\("\/music"\) \|\| family === "music"\) \{\s*\/\/ Music uses the canonical guarded form/);
  assert.match(portal, /const musicTask = \["\/music\/create", "\/music\/song"\]\.includes/);
  assert.match(portal, /interactiveWorkbench = videoTask \|\| musicTask \? "" :/);
});

test("Quote and Confirm: fresh quote validates receipt, expired quote is rejected", () => {
  const context = createHarness("vi");
  const validQuote = {
    phase: "estimate",
    status: "awaiting_confirm",
    estimateFingerprint: "fingerprint_123456",
    webQuoteReceipt: "R".repeat(48),
    data: {
      estimate: {
        available: true,
        quote_expires_at: new Date(Date.now() + 60_000).toISOString()
      }
    }
  };
  assert.equal(context.flowHasFreshEstimate(validQuote), true, "future expiry is accepted");

  const expiredQuote = {
    ...validQuote,
    data: {
      estimate: {
        available: true,
        quote_expires_at: new Date(Date.now() - 60_000).toISOString()
      }
    }
  };
  assert.equal(context.flowHasFreshEstimate(expiredQuote), false, "expired quote must be rejected");

  const noReceipt = { ...validQuote, webQuoteReceipt: "" };
  assert.equal(context.flowHasFreshEstimate(noReceipt), false, "missing receipt must be rejected");

  const invalidReceipt = { ...validQuote, webQuoteReceipt: "short" };
  assert.equal(context.flowHasFreshEstimate(invalidReceipt), false, "malformed receipt must be rejected");
});

test("Browser authority: client never computes authoritative price, balance or allows double-confirm", () => {
  assert.doesNotMatch(portal, /function calculateMusicPrice/i);
  assert.doesNotMatch(portal, /function mutateMusicBalance/i);
  assert.match(portal, /giá và khả năng chỉ lấy từ báo giá máy chủ/i);
  assert.match(portal, /Browser không tính Xu/i);
});

test("Progress, Result, Retry: canonical flow tracking with zero fake output or audio", () => {
  assert.match(portal, /function safeFeatureTracking\(flow\)/);
  assert.match(portal, /FEATURE_TRACKING_JOB_STATES/);
  assert.match(portal, /function renderCanonicalFlow\(flow, route\)/);
  assert.match(portal, /Nguồn: \$\{safeText\(payload\.source \|\| "canonical_bot"\)\} · Chưa gọi provider · Chưa trừ Xu\./);
  assert.doesNotMatch(portal, /<audio[^>]*src="[^"]*toanaas_lofi/);
  assert.doesNotMatch(portal, /Suno AI Music Generator/);
});

test("Two-track delivery: UI renders zero claims of two-track delivery", () => {
  assert.doesNotMatch(portal, /2 track|hai track|hai bản nhạc|two track/i);
});

test("Player and Download: player and download controls strictly require verified canonical assets", () => {
  assert.doesNotMatch(portal, /<audio\b[^>]*autoplay/);
  assert.match(portal, /Output chỉ được cấp qua asset đã xác minh/);
  assert.match(portal, /Tài sản gần đây \(tối đa 100\)/);
  assert.match(portal, /Không hiển thị URL provider, file path hoặc preview không được ký/);
});

test("Save and Reuse: Asset Vault audio operations scoped to signed Web account", () => {
  assert.match(portal, /customerPage\("\/audio\/assets"/);
  assert.match(portal, /featurePage\("\/music\/upload"/);
  assert.match(portal, /customerPage\("\/music\/library"/);
  assert.match(portal, /customerPage\("\/music\/sfx-library"/);
  assert.match(portal, /Chỉ metadata audio active của Asset Vault thuộc signed Web account/);
});

test("Responsive and Accessibility: steps, tiers and suggestion cards keep mobile wrapping and ARIA labels", () => {
  assert.match(theme, /\.portal-music-product-steps\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(theme, /\.portal-music-product-tier-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/);
  assert.match(theme, /@media \(max-width: 640px\)[\s\S]*?\.portal-music-product-steps\s*\{[^}]*grid-template-columns:\s*1fr/);
  assert.match(theme, /@media \(max-width: 640px\)[\s\S]*?\.portal-music-product-tier-grid\s*\{[^}]*grid-template-columns:\s*1fr/);

  const context = createHarness("vi");
  const html = context.renderMusicProductGuidance({ path: "/music/song", routePath: "/music/song" }, {});
  assert.match(html, /aria-labelledby="music-product-flow-title"/);
  assert.match(html, /aria-label="Trình tự tạo âm nhạc"/);
  assert.match(html, /aria-label="Các gói chất lượng"/);
  assert.match(html, /aria-labelledby="music-product-suggestion-title"/);
});

test("Locale: VI, EN and ZH catalogues maintain balanced musicProduct keys without raw fallbacks", () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(catalogue, context);
  const locales = ["vi", "en", "zh"];
  const sets = locales.map((loc) => Object.keys(context.TOANAASI18n.messages[loc]).filter((k) => k.startsWith("musicProduct.")).sort());
  assert.ok(sets[0].length >= 50);
  assert.deepEqual(sets[1], sets[0]);
  assert.deepEqual(sets[2], sets[0]);

  for (const loc of locales) {
    const harness = createHarness(loc);
    const html = harness.renderMusicProductGuidance({ path: "/music/song", routePath: "/music/song" }, {});
    assert.doesNotMatch(html, /musicProduct\.[a-zA-Z0-9_.]+/);
    if (loc === "en") assert.doesNotMatch(html.replace(/<[^>]*>/g, " "), /[À-ỹĐđ]/);
  }
});
