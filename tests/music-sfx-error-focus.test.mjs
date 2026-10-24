import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const integrationSrc = readFileSync(new URL("../static/portal/integration.js", import.meta.url), "utf8");
const extract = (s, e) => integrationSrc.slice(integrationSrc.indexOf(s), integrationSrc.indexOf(e));
const mCode = extract('if (action === "music-direction-preset-compose") {', 'if (action === "sfx-cue-sheet-compose") {');
const sCode = extract('if (action === "sfx-cue-sheet-compose") {', 'if (action === "music-prompt-compose") {');

function makeRunner(code) {
  const clean = code.split(String.fromCharCode(13)).join("");
  const fn = new Function("env", `return async function(action, route, fields) {\nlet musicDirectionPresetComposeRequestEpoch = 0, musicDirectionPresetComposePendingRequestEpoch = 0;\nlet sfxCueSheetComposeRequestEpoch = 0, sfxCueSheetComposePendingRequestEpoch = 0;\nenv.bumpEpoch = () => { ++musicDirectionPresetComposeRequestEpoch; ++sfxCueSheetComposeRequestEpoch; };\nconst { window, currentPortalPath, base, musicDirectionPresetPayload, sfxCueSheetPayload, setActionBusy, setMusicDirectionPresetSubmissionStatus, setSfxCueSheetSubmissionStatus, musicSfxEditorialFeedbackText, api, musicDirectionPresetGuardBoundaryIsSafe, sfxCueSheetBoundaryIsSafe, musicDirectionPresetResultMatchesSource, sfxCueSheetResultMatchesSource, merge, toast } = env;\n${clean}\n};`);
  return fn;
}

const runners = { music: makeRunner(mCode), sfx: makeRunner(sCode) };

function setup(cfg = {}) {
  let curPath = cfg.path;
  const calls = { focus: [], api: 0, merge: 0, toast: 0, busy: [] };
  const btn = { isConnected: cfg.connected ?? true, matches: sel => sel === cfg.sel, focus: opts => { calls.focus.push(opts); doc.activeElement = btn; } };
  const doc = { body: {}, activeElement: cfg.initialFocus ?? btn };
  const env = {
    window: { document: doc },
    currentPortalPath: () => curPath,
    base: () => ({ capabilities: { [cfg.action]: true } }),
    musicDirectionPresetPayload: f => f,
    sfxCueSheetPayload: f => f,
    setActionBusy: (a, r, b) => { calls.busy.push(b); if (b && doc.activeElement === btn) doc.activeElement = doc.body; },
    setMusicDirectionPresetSubmissionStatus: () => {},
    setSfxCueSheetSubmissionStatus: () => {},
    musicSfxEditorialFeedbackText: (t, k, d) => d,
    musicDirectionPresetGuardBoundaryIsSafe: () => cfg.guardSafe ?? false,
    sfxCueSheetBoundaryIsSafe: () => cfg.guardSafe ?? false,
    musicDirectionPresetResultMatchesSource: () => true,
    sfxCueSheetResultMatchesSource: () => true,
    merge: () => calls.merge++,
    toast: () => calls.toast++,
    api: async () => {
      calls.api++;
      if (cfg.onApi) cfg.onApi(env, () => { curPath = "/other"; });
      if (cfg.apiError) throw cfg.apiError;
      return cfg.apiRes || { status: "draft", data: {} };
    }
  };
  return { run: runners[cfg.tool](env), env, calls, btn, doc };
}

const TOOLS = [
  { tool: "music", action: "music-direction-preset-compose", path: "/media-workspace/music-directions", sel: 'form[data-portal-action="music-direction-preset-compose"][data-portal-route="/media-workspace/music-directions"] [data-music-direction-submit]' },
  { tool: "sfx", action: "sfx-cue-sheet-compose", path: "/media-workspace/sfx-cue-sheet", sel: 'form[data-portal-action="sfx-cue-sheet-compose"][data-portal-route="/media-workspace/sfx-cue-sheet"] [data-sfx-cue-sheet-submit]' }
];

for (const t of TOOLS) {
  test(`${t.tool} F01: restore focus on error when prior button exact, connected, active is body`, async () => {
    const { run, calls } = setup({ ...t, apiError: new Error("POST abort") });
    await assert.rejects(() => run(t.action, t.path, {}), /POST abort/);
    assert.equal(calls.focus.length, 1);
    assert.deepEqual(calls.focus[0], { preventScroll: true });
  });

  test(`${t.tool} F02: no focus on wrong route before request (rejects immediately, 0 API calls)`, async () => {
    const { run, calls } = setup({ ...t, path: "/wrong" });
    await assert.rejects(() => run(t.action, "/wrong", {}), /chỉ nhận thao tác/);
    assert.equal(calls.api, 0);
    assert.equal(calls.focus.length, 0);
  });

  test(`${t.tool} F02: no focus when route changes after request begins (stale response ignored)`, async () => {
    const { run, calls } = setup({ ...t, apiError: new Error("late error"), onApi: (env, setWrongRoute) => setWrongRoute() });
    await assert.doesNotReject(() => run(t.action, t.path, {}));
    assert.equal(calls.api, 1);
    assert.equal(calls.focus.length, 0);
    assert.equal(calls.merge, 0);
  });

  test(`${t.tool} F02: no focus when request epoch stales during inflight request`, async () => {
    const { run, env, calls } = setup({ ...t, apiError: new Error("stale error"), onApi: () => env.bumpEpoch() });
    await assert.doesNotReject(() => run(t.action, t.path, {}));
    assert.equal(calls.api, 1);
    assert.equal(calls.focus.length, 0);
    assert.equal(calls.merge, 0);
  });

  test(`${t.tool} F02: non-steal controls (other input focused, selector mismatch, disconnected, success, valid guard)`, async () => {
    const cases = [
      { initialFocus: { tag: "input" }, apiError: new Error("err") },
      { sel: "wrong-selector", apiError: new Error("err") },
      { connected: false, apiError: new Error("err") },
      { onApi: env => { env.window.document.activeElement = { tag: "user-focused-input" }; }, apiError: new Error("err") },
      { apiRes: { status: "draft", data: {} } },
      { apiRes: { status: "guarded", data: {} }, guardSafe: true },
      { apiError: Object.assign(new Error("guard"), { payload: { status: "guarded", data: {} } }), guardSafe: true }
    ];
    for (const c of cases) {
      const { run, calls } = setup({ ...t, ...c });
      if (c.apiError && !c.guardSafe) {
        await assert.rejects(() => run(t.action, t.path, {}));
      } else {
        await assert.doesNotReject(() => run(t.action, t.path, {}));
      }
      assert.equal(calls.focus.length, 0);
    }
  });
}
