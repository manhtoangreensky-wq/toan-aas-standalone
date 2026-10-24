import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const i18nCode = fs.readFileSync(path.join(root, "static/portal/portal-i18n.js"), "utf8").replace(/\r\n/g, "\n");
const intCode = fs.readFileSync(path.join(root, "static/portal/integration.js"), "utf8").replace(/\r\n/g, "\n");

// The real catalogue and its export are immutable. Bridge the locale at the
// dependency boundary instead of overwriting either frozen API object.
const catalogueContext = vm.createContext({});
vm.runInContext(i18nCode, catalogueContext);
const realI18n = catalogueContext.TOANAASI18n;
assert(realI18n && typeof realI18n.t === "function", "realI18n must load");
let currentLocale = "vi";
const sandbox = { window: { TOANAASI18n: {
  t: (key, params) => realI18n.t(key, params, currentLocale)
} }, document: { querySelector: () => null }, console };
vm.createContext(sandbox);
function setLocale(locale) {
  currentLocale = locale;
}

const helperMatch = intCode.match(/function musicSfxEditorialFeedbackText[\s\S]*?\n  \}/);
const helperSrc = helperMatch ? helperMatch[0] : "";

const musicMarker = '      if (action === "music-direction-preset-compose") {';
const sfxMarker = '      if (action === "sfx-cue-sheet-compose") {';
const promptMarker = '      if (action === "music-prompt-compose") {';

const musicBlock = intCode.slice(intCode.indexOf(musicMarker), intCode.indexOf(sfxMarker));
const sfxBlock = intCode.slice(intCode.indexOf(sfxMarker), intCode.indexOf(promptMarker));

const runnerScript = `
let musicDirectionPresetComposeRequestEpoch = 0;
let musicDirectionPresetComposePendingRequestEpoch = 0;
let sfxCueSheetComposeRequestEpoch = 0;
let sfxCueSheetComposePendingRequestEpoch = 0;

${helperSrc}

async function runTest(opts) {
  const {
    action, route, fields, currentPortalPath, base, api, merge, toast,
    setActionBusy, setMusicDirectionPresetSubmissionStatus, setSfxCueSheetSubmissionStatus,
    musicDirectionPresetPayload, musicDirectionPresetBoundaryIsSafe, musicDirectionPresetGuardBoundaryIsSafe, musicDirectionPresetResultMatchesSource,
    sfxCueSheetPayload, sfxCueSheetBoundaryIsSafe, sfxCueSheetResultMatchesSource
  } = opts;
  ${musicBlock}
  ${sfxBlock}
}

({
  runTest,
  getHelper: () => (typeof musicSfxEditorialFeedbackText === "function" ? musicSfxEditorialFeedbackText : null),
  bumpEpoch: () => {
    musicDirectionPresetComposeRequestEpoch++;
    sfxCueSheetComposeRequestEpoch++;
  }
})
`;
const harness = vm.runInContext(runnerScript, sandbox);

const COPY = {
  vi: {
    music: { pending: "Đang lập ba hướng âm nhạc…", success: "Đã lập ba hướng âm nhạc.", guarded: "Điều chỉnh nội dung trước khi lập hướng âm nhạc.", copyright: "Hãy mô tả phong cách riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền." },
    sfx: { pending: "Đang lập ba vị trí hiệu ứng…", success: "Đã lập ba vị trí hiệu ứng.", guarded: "Điều chỉnh nội dung trước khi lập bảng hiệu ứng.", copyright: "Hãy mô tả hiệu ứng riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền." },
  },
  en: {
    music: { pending: "Creating three music directions…", success: "Three music directions created.", guarded: "Adjust the brief before creating music directions.", copyright: "Describe an original style instead of asking to imitate an artist or copyrighted work." },
    sfx: { pending: "Creating three SFX cues…", success: "Three SFX cues created.", guarded: "Adjust the brief before creating the SFX cue sheet.", copyright: "Describe original effects instead of asking to imitate an artist or copyrighted work." },
  },
  zh: {
    music: { pending: "正在创建三个音乐方向…", success: "已创建三个音乐方向。", guarded: "请调整摘要后再创建音乐方向。", copyright: "请描述原创风格，不要要求模仿艺术家或受版权保护的作品。" },
    sfx: { pending: "正在创建三个音效提示…", success: "已创建三个音效提示。", guarded: "请调整摘要后再创建音效提示表。", copyright: "请描述原创音效，不要要求模仿艺术家或受版权保护的作品。" },
  },
};

const FIXTURES = {
  music: { action: "music-direction-preset-compose", route: "/media-workspace/music-directions", payload: { description: "Original product introduction", language: "en", web_preset_id: "commercial_bright" }, knownCode: "WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD", resultKey: "musicDirectionPresetResult" },
  sfx: { action: "sfx-cue-sheet-compose", route: "/media-workspace/sfx-cue-sheet", payload: { description: "Original product introduction", language: "en", web_sfx_preset_id: "motion_transition" }, knownCode: "WEB_SFX_CUE_COPYRIGHT_GUARD", resultKey: "sfxCueSheetResult" },
};

const receipt = { id: "rcpt_123", status: "ok" };

async function execute(toolName, apiHandler, overrides = {}) {
  const fix = FIXTURES[toolName];
  let curPath = overrides.portalPath !== undefined ? overrides.portalPath : fix.route;
  const statusCalls = [];
  const toastCalls = [];
  const merges = [];
  let apiCalls = 0;
  let apiBody = null;

  const ctx = {
    action: fix.action,
    route: overrides.route !== undefined ? overrides.route : fix.route,
    fields: { ...fix.payload },
    currentPortalPath: () => curPath,
    base: () => ({
      capabilities: overrides.capabilities !== undefined ? overrides.capabilities : { [fix.action]: true },
      pageStates: {},
    }),
    api: async (url, options) => {
      assert.equal(options.method, "POST");
      assert.equal(url, `/media-workspace/tools/${toolName === "music" ? "music-directions" : "sfx-cue-sheet"}/compose`);
      apiCalls++;
      apiBody = JSON.parse(options.body);
      if (overrides.onApi) overrides.onApi({ bumpEpoch: harness.bumpEpoch, setPath: (p) => { curPath = p; } });
      return apiHandler(url, options);
    },
    merge: (data) => merges.push(data),
    toast: (msg) => toastCalls.push(msg),
    setActionBusy: () => {},
    setMusicDirectionPresetSubmissionStatus: (msg) => statusCalls.push(msg),
    setSfxCueSheetSubmissionStatus: (msg) => statusCalls.push(msg),
    musicDirectionPresetPayload: (f) => f,
    musicDirectionPresetBoundaryIsSafe: () => overrides.boundarySafe !== false,
    musicDirectionPresetGuardBoundaryIsSafe: () => overrides.boundarySafe !== false,
    musicDirectionPresetResultMatchesSource: () => overrides.matchesSource !== false,
    sfxCueSheetPayload: (f) => f,
    sfxCueSheetBoundaryIsSafe: () => overrides.boundarySafe !== false,
    sfxCueSheetResultMatchesSource: () => overrides.matchesSource !== false,
  };

  const promise = harness.runTest(ctx);
  return { promise, statusCalls, toastCalls, merges, getApiCalls: () => apiCalls, getApiBody: () => apiBody };
}

test("helper function exists and falls back gracefully", () => {
  const helper = harness.getHelper();
  assert.equal(typeof helper, "function");
  assert.equal(helper("music", "unknown_key", "Fallback text"), "Fallback text");
  assert.equal(helper("unknown_tool", "pending", "Fallback text"), "Fallback text");
  const prevI18n = sandbox.window.TOANAASI18n;
  sandbox.window.TOANAASI18n = null;
  assert.equal(helper("music", "pending", "Fallback text"), "Fallback text");
  sandbox.window.TOANAASI18n = prevI18n;
});

for (const locale of ["vi", "en", "zh"]) {
  for (const tool of ["music", "sfx"]) {
    test(`${tool} submit feedback in ${locale} - pending, success, guard responses and errors`, async () => {
      setLocale(locale);
      const exp = COPY[locale][tool];
      const fix = FIXTURES[tool];

      let resolveApi;
      const res1 = await execute(tool, () => new Promise(resolve => { resolveApi = resolve; }));
      assert.equal(res1.statusCalls[0], exp.pending);
      resolveApi({ status: "draft", message: "RAW VI TECHNICAL", data: receipt });
      await res1.promise;
      assert.equal(res1.toastCalls[0], exp.success);
      assert.deepEqual({ ...res1.merges[0][fix.resultKey] }, { source: fix.payload, receipt });
      assert.equal(res1.merges[0][fix.resultKey].receipt, receipt);
      assert.deepEqual(res1.getApiBody(), fix.payload);
      assert.equal(res1.getApiCalls(), 1);
      if (tool === "sfx") {
        assert.equal(res1.statusCalls[1], exp.success);
      }

      const res2 = await execute(tool, async () => ({
        status: "guarded", error_code: fix.knownCode, message: "RAW VI TECHNICAL", data: {}
      }));
      await res2.promise;
      assert.equal(res2.toastCalls[0], exp.copyright);

      const res3 = await execute(tool, async () => ({
        status: "guarded", error_code: "OTHER_GUARD", message: "RAW VI TECHNICAL", data: {}
      }));
      await res3.promise;
      assert.equal(res3.toastCalls[0], exp.guarded);

      const res4 = await execute(tool, async () => {
        const err = new Error("guarded");
        err.payload = { status: "guarded", error_code: fix.knownCode, message: "RAW VI TECHNICAL", data: {} };
        throw err;
      });
      await res4.promise;
      assert.equal(res4.toastCalls[0], exp.copyright);

      const res5 = await execute(tool, async () => {
        const err = new Error("guarded");
        err.payload = { status: "guarded", error_code: "OTHER_GUARD", message: "RAW VI TECHNICAL", data: {} };
        throw err;
      });
      await res5.promise;
      assert.equal(res5.toastCalls[0], exp.guarded);
    });
  }
}

test("stale responses (epoch bump and route change) do not merge or toast", async () => {
  for (const tool of ["music", "sfx"]) {
    const resEpoch = await execute(tool, async () => ({ status: "draft", data: receipt }), {
      onApi: ({ bumpEpoch }) => bumpEpoch(),
    });
    await resEpoch.promise;
    assert.equal(resEpoch.merges.length, 0);
    assert.equal(resEpoch.toastCalls.length, 0);

    const resRoute = await execute(tool, async () => ({ status: "draft", data: receipt }), {
      onApi: ({ setPath }) => setPath("/other-route"),
    });
    await resRoute.promise;
    assert.equal(resRoute.merges.length, 0);
    assert.equal(resRoute.toastCalls.length, 0);
  }
});

test("capabilities require strict boolean true; false or string true never POST", async () => {
  for (const tool of ["music", "sfx"]) {
    const fix = FIXTURES[tool];
    for (const capVal of [false, "true", undefined]) {
      const res = await execute(tool, async () => ({ status: "draft", data: receipt }), {
        capabilities: { [fix.action]: capVal },
      });
      await assert.rejects(res.promise, /Cần signed Web session/);
      assert.equal(res.getApiCalls(), 0);
    }
  }
});

test("wrong route or boundary mismatch does not produce success merge", async () => {
  for (const tool of ["music", "sfx"]) {
    const resRoute = await execute(tool, async () => ({ status: "draft", data: receipt }), {
      route: "/wrong-route",
    });
    await assert.rejects(resRoute.promise);
    assert.equal(resRoute.getApiCalls(), 0);

    const resMismatch = await execute(tool, async () => ({ status: "draft", data: receipt }), {
      matchesSource: false,
    });
    await assert.rejects(resMismatch.promise);
    assert.equal(resMismatch.merges.length, 0);
    const resUnsafe = await execute(tool, async () => ({ status: "guarded", data: {} }), { boundarySafe: false });
    await assert.rejects(resUnsafe.promise);
    assert.equal(resUnsafe.merges.length, 0);
    assert.equal(resUnsafe.toastCalls.length, 0);
  }
});
