import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import fs from "node:fs";

const NL = String.fromCharCode(10);
const portalJsSrc = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r/g, "");
const portalI18nSrc = fs.readFileSync("static/portal/portal-i18n.js", "utf8").replace(/\r/g, "");

function extractFunction(src, name) {
  const needle = `function ${name}(`;
  const startIdx = src.indexOf(needle);
  if (startIdx === -1) throw new Error(`Function ${name} not found`);
  const endMarker = `${NL}  }`;
  const endIdx = src.indexOf(endMarker, startIdx);
  if (endIdx === -1) throw new Error(`Closing brace for ${name} not found`);
  return src.slice(startIdx, endIdx + endMarker.length);
}

function loadI18n() {
  const context = {};
  vm.createContext(context);
  vm.runInContext(portalI18nSrc, context);
  return context.TOANAASI18n;
}

const EXPECTED_9_ROWS = [
  { ns: "musicDirectionUi", key: "field.briefPlaceholder", vi: "Ví dụ: nhạc nhẹ, hiện đại cho video giới thiệu ứng dụng.", en: "Example: calm, modern music for an app introduction video.", zh: "例如：为应用介绍视频配上轻柔、现代的音乐。" },
  { ns: "musicDirectionUi", key: "field.briefHelp", vi: "Nêu bối cảnh, người nghe và cảm xúc. Chỉ nhập mô tả, không kèm liên kết hay thông tin riêng tư.", en: "Describe the scene, audience and mood. Enter a description without links or private information.", zh: "描述场景、受众和情绪。只输入文字说明，不要包含链接或私人信息。" },
  { ns: "sfxCueSheetUi", key: "field.briefPlaceholder", vi: "Ví dụ: hiệu ứng nhẹ khi chuyển cảnh và khi hiện lời kêu gọi cuối video.", en: "Example: subtle effects for scene changes and the final video call to action.", zh: "例如：在转场和视频末尾的行动提示处加入轻柔音效。" },
  { ns: "sfxCueSheetUi", key: "field.briefHelp", vi: "Nêu vị trí, hành động và cảm giác cần nhấn. Chỉ nhập mô tả, không kèm liên kết hay thông tin riêng tư.", en: "Describe the placement, action and feeling to emphasize. Enter a description without links or private information.", zh: "描述需要强调的位置、动作和感受。只输入文字说明，不要包含链接或私人信息。" },
  { ns: "sfxCueSheetUi", key: "result.directionLabel", vi: "Hướng hiệu ứng", en: "SFX direction", zh: "音效方向" },
  { ns: "sfxCueSheetUi", key: "result.mixLabel", vi: "Gợi ý hòa âm", en: "Mix guidance", zh: "混音建议" },
  { ns: "sfxCueSheetUi", key: "result.avoidLabel", vi: "Cần tránh", en: "Avoid", zh: "避免事项" },
  { ns: "sfxCueSheetUi", key: "result.cautionFallback", vi: "Kiểm tra quyền sử dụng và bối cảnh trước khi dùng.", en: "Check usage rights and context before use.", zh: "使用前请核对使用权与场景。" },
  { ns: "sfxCueSheetUi", key: "result.reviewFallback", vi: "Rà soát cùng người biên tập trước khi chọn âm thanh.", en: "Review with the editor before choosing audio.", zh: "选择音频前请与剪辑人员共同审核。" }
];

function setupEnv(locale) {
  const realI18n = loadI18n();
  const sandbox = {
    uiText: (k, fallback, params) => realI18n.t(k, params, locale) || fallback,
    badge: (kind) => `<badge>${kind}</badge>`,
    normalizeSfxCueSheetState: (r) => r,
    SFX_CUE_SHEET_PRESETS: [],
    SFX_CUE_SHEET_ROUTE: "/media-workspace/sfx-cue-sheet",
    transientFormDrafts: new Map(),
    transientFormValues: () => ({}),
    sfxCueSheetTransientFormValues: (v) => v,
    sfxCueSheetPlacementLabel: (id, name) => `${id}:${name}`,
    sfxCueSheetPresetText: (p, k) => p[k] || ""
  };
  const code = [
    extractFunction(portalJsSrc, "safeText"),
    extractFunction(portalJsSrc, "musicDirectionUiText"),
    extractFunction(portalJsSrc, "musicDirectionPresetFields"),
    extractFunction(portalJsSrc, "sfxCueSheetUiText"),
    extractFunction(portalJsSrc, "sfxCueSheetFields"),
    extractFunction(portalJsSrc, "renderSfxCueSheetResult")
  ].join(NL);
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return sandbox;
}

test("9 copy rows are present across VI, EN, ZH in i18n catalogue", () => {
  const i18n = loadI18n();
  for (const row of EXPECTED_9_ROWS) {
    assert.equal(i18n.t(`${row.ns}.${row.key}`, undefined, "vi"), row.vi);
    assert.equal(i18n.t(`${row.ns}.${row.key}`, undefined, "en"), row.en);
    assert.equal(i18n.t(`${row.ns}.${row.key}`, undefined, "zh"), row.zh);
  }
});

test("musicDirectionPresetFields structure and translations across VI, EN, ZH", () => {
  for (const loc of ["vi", "en", "zh"]) {
    const env = setupEnv(loc);
    const fields = env.musicDirectionPresetFields();
    const desc = fields.find((f) => f.name === "description");
    const lang = fields.find((f) => f.name === "language");
    assert.ok(desc && lang);
    assert.equal(desc.control, "textarea");
    assert.equal(desc.required, true);
    assert.equal(desc.minLength, 2);
    assert.equal(desc.maxLength, 500);
    assert.equal(desc.wide, true);
    assert.equal(lang.control, "select");
    assert.equal(lang.required, true);
    assert.deepEqual(JSON.parse(JSON.stringify(lang.options.map((o) => o[0]))), ["vi", "en"]);

    const expectedPlaceholder = EXPECTED_9_ROWS.find((r) => r.ns === "musicDirectionUi" && r.key === "field.briefPlaceholder")[loc];
    const expectedHelp = EXPECTED_9_ROWS.find((r) => r.ns === "musicDirectionUi" && r.key === "field.briefHelp")[loc];
    assert.equal(desc.placeholder, expectedPlaceholder);
    assert.equal(desc.help, expectedHelp);
  }
});

test("sfxCueSheetFields structure and translations across VI, EN, ZH", () => {
  for (const loc of ["vi", "en", "zh"]) {
    const env = setupEnv(loc);
    const fields = env.sfxCueSheetFields();
    const desc = fields.find((f) => f.name === "description");
    const lang = fields.find((f) => f.name === "language");
    assert.ok(desc && lang);
    assert.equal(desc.control, "textarea");
    assert.equal(desc.required, true);
    assert.equal(desc.minLength, 2);
    assert.equal(desc.maxLength, 500);
    assert.equal(desc.wide, true);
    assert.equal(lang.control, "select");
    assert.equal(lang.required, true);
    assert.deepEqual(JSON.parse(JSON.stringify(lang.options.map((o) => o[0]))), ["vi", "en"]);

    const expectedPlaceholder = EXPECTED_9_ROWS.find((r) => r.ns === "sfxCueSheetUi" && r.key === "field.briefPlaceholder")[loc];
    const expectedHelp = EXPECTED_9_ROWS.find((r) => r.ns === "sfxCueSheetUi" && r.key === "field.briefHelp")[loc];
    assert.equal(desc.placeholder, expectedPlaceholder);
    assert.equal(desc.help, expectedHelp);
  }
});

test("renderSfxCueSheetResult renders dt labels and preserves server values", () => {
  for (const loc of ["vi", "en", "zh"]) {
    const env = setupEnv(loc);
    const fixture = {
      source: { description: "desc1", language: "vi", web_sfx_preset_id: "p1" },
      receipt: {
        cue_sheet: {
          title: "Test Title & Co",
          cues: [
            { ordinal: 1, placement_id: "intro", placement: "Intro", cue_role: "lead", editorial_note: "note1", direction: "dir1 <raw>", mix_note: "mix1 & more", avoid_note: "avoid1 'quote'" },
            { ordinal: 2, placement_id: "body", placement: "Body", cue_role: "support", editorial_note: "note2", direction: "dir2", mix_note: "mix2", avoid_note: "avoid2" },
            { ordinal: 3, placement_id: "outro", placement: "Outro", cue_role: "tail", editorial_note: "note3", direction: "dir3", mix_note: "mix3", avoid_note: "avoid3" }
          ],
          cautions: ["Real caution 1"],
          review_before_use: ["Real review 1"]
        }
      }
    };
    const html = env.renderSfxCueSheetResult(fixture);
    const dirLabel = EXPECTED_9_ROWS.find((r) => r.key === "result.directionLabel")[loc];
    const mixLabel = EXPECTED_9_ROWS.find((r) => r.key === "result.mixLabel")[loc];
    const avoidLabel = EXPECTED_9_ROWS.find((r) => r.key === "result.avoidLabel")[loc];

    assert.equal((html.match(new RegExp(`<dt>${dirLabel}</dt>`, "g")) || []).length, 3);
    assert.equal((html.match(new RegExp(`<dt>${mixLabel}</dt>`, "g")) || []).length, 3);
    assert.equal((html.match(new RegExp(`<dt>${avoidLabel}</dt>`, "g")) || []).length, 3);

    assert.ok(html.includes("dir1 &lt;raw&gt;"));
    assert.ok(html.includes("mix1 &amp; more"));
    assert.ok(html.includes("avoid1 &#39;quote&#39;"));
    assert.ok(html.includes("Real caution 1"));
    assert.ok(html.includes("Real review 1"));
  }
});

test("renderSfxCueSheetResult renders caution and review defensive fallbacks", () => {
  for (const loc of ["vi", "en", "zh"]) {
    const env = setupEnv(loc);
    const fixture = {
      source: { description: "desc1", language: "vi", web_sfx_preset_id: "p1" },
      receipt: {
        cue_sheet: {
          cues: [],
          cautions: [],
          review_before_use: []
        }
      }
    };
    const html = env.renderSfxCueSheetResult(fixture);
    const cautionFallback = EXPECTED_9_ROWS.find((r) => r.key === "result.cautionFallback")[loc];
    const reviewFallback = EXPECTED_9_ROWS.find((r) => r.key === "result.reviewFallback")[loc];
    assert.ok(html.includes(`<li>${cautionFallback}</li>`));
    assert.ok(html.includes(`<li>${reviewFallback}</li>`));
  }
});
