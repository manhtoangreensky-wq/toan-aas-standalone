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

function plainText(html) {
  return String(html).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function createHarness(locale) {
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
    functionSource("renderMusicProductGuidance")
  ].join("\n"), context);
  return context;
}

const sourceFields = [
  { name: "brief", label: "Brief âm nhạc", placeholder: "brief", help: "help" },
  { name: "tier", label: "Gói chất lượng", options: [{ value: "basic", label: "Cơ bản — 130 Xu" }, { value: "standard", label: "Tiêu chuẩn — 150 Xu" }, { value: "premium", label: "Cao cấp — 200 Xu" }] },
  { name: "mode", label: "Kiểu sáng tác", options: [{ value: "lyrics", label: "Bài hát có lời gốc" }, { value: "melody", label: "Giai điệu không lời" }, { value: "custom", label: "Tùy biến theo mô tả" }] },
  { name: "vocal_mode", label: "Kiểu giọng hát", options: [{ value: "auto", label: "Tự động" }, { value: "male", label: "Giọng nam" }, { value: "female", label: "Giọng nữ" }, { value: "duet", label: "Song ca nam và nữ" }] },
  { name: "lyrics", label: "Lời bài hát", placeholder: "lyrics", help: "help" },
  { name: "song_length_mode", label: "Dạng bài hát", options: [{ value: "seconds", label: "Theo số giây" }, { value: "half", label: "Bản nửa" }, { value: "full", label: "Bản đầy đủ" }] },
  { name: "duration_seconds", label: "Thời lượng", placeholder: "30" }
];

for (const locale of ["vi", "en", "zh"]) {
  test(`Music product catalogue is balanced and renders the guarded flow in ${locale}`, () => {
    const context = createHarness(locale);
    const html = context.renderMusicProductGuidance({ path: "/music/song", routePath: "/music/song" }, {});
    const text = plainText(html);
    assert.match(html, /data-music-product-mode="song"/);
    assert.equal((html.match(/data-music-product-step=/g) || []).length, 4);
    assert.equal((html.match(/data-music-tier-card=/g) || []).length, 3);
    assert.equal((html.match(/data-music-suggestion-card=/g) || []).length, 3);
    assert.doesNotMatch(html, /\{number\}|<audio\b|toanaas_lofi|Suno AI Music Generator|onclick="alert/i);
    assert.doesNotMatch(text, /130 Xu|150 Xu|200 Xu|250 Xu|300 Xu/);
    if (locale === "en") assert.doesNotMatch(text, /[À-ỹĐđ]/);
    if (locale === "zh") assert.doesNotMatch(text.replace(/TOAN AAS|Video|SFX/g, ""), /[A-Za-z]{3,}/);
  });
}

test("Music product fields keep contracts, remove prices and isolate song controls", () => {
  const context = createHarness("vi");
  const background = context.musicProductFields(sourceFields, "/music/create");
  const song = context.musicProductFields(sourceFields, "/music/song");
  assert.deepEqual(background.map((field) => field.name), sourceFields.map((field) => field.name));
  assert.deepEqual(song.map((field) => field.name), sourceFields.map((field) => field.name));
  assert.ok(background.filter((field) => ["lyrics", "vocal_mode", "song_length_mode"].includes(field.name)).every((field) => field.disabled === true));
  assert.ok(song.filter((field) => ["lyrics", "vocal_mode", "song_length_mode"].includes(field.name)).every((field) => field.disabled !== true));
  assert.ok(song.find((field) => field.name === "tier").options.every((option) => !/Xu|\d/.test(option.label)));
  assert.equal(song.find((field) => field.name === "vocal_mode").options.length, 4);
  assert.equal(song.find((field) => field.name === "song_length_mode").options.length, 3);
});

test("Music product locale keys are balanced", () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(catalogue, context);
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(context.TOANAASI18n.messages[locale])
    .filter((key) => key.startsWith("musicProduct.")).sort());
  assert.ok(keysets[0].length >= 50);
  assert.deepEqual(keysets[1], keysets[0]);
  assert.deepEqual(keysets[2], keysets[0]);
});

test("Music workspace styles keep cards readable and responsive in both themes", () => {
  assert.match(theme, /\.portal-music-product-guidance\s*\{/);
  assert.match(theme, /\.portal-music-product-steps\s*\{[^}]*grid-template-columns:\s*repeat\(4/s);
  assert.match(theme, /\.portal-music-product-tier-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3/s);
  assert.match(theme, /html\[data-portal-theme="dark"\] \.portal-music-product-guidance/);
  assert.match(theme, /@media \(max-width: 640px\)[\s\S]*\.portal-music-product-steps/);
  assert.doesNotMatch(theme, /portal-music-product[^}]*transition:\s*all/);
});

test("Music fake provider/player presentation is removed from the production source", () => {
  assert.doesNotMatch(portal, /Suno AI Music Generator|toanaas_lofi_chill_beats_master\.mp3|TẠO NHẠC AI KHÔNG BẢN QUYỀN/i);
});
