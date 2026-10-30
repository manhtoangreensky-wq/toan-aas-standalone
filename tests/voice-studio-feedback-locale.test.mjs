import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const integrationSource = fs.readFileSync(
  path.resolve("static/portal/integration.js"),
  "utf8"
);
const i18nSource = fs.readFileSync(
  path.resolve("static/portal/portal-i18n.js"),
  "utf8"
);

function extractProductionHandler(source) {
  const startMarker =
    'if (action === "voice-studio-filter" || action === "voice-studio-filter-clear")';
  const endMarker = 'if (action === "voice-vault-create")';
  const startIndex = source.indexOf(startMarker);
  const endIndex = source.indexOf(endMarker);
  assert.ok(startIndex !== -1, "startMarker found in integration.js");
  assert.ok(endIndex !== -1, "endMarker found in integration.js");
  assert.ok(startIndex < endIndex, "handler slice order is valid");
  return source.slice(startIndex, endIndex);
}

function extractFeedbackHelper(source) {
  const startMarker = "  function voiceStudioFeedbackText(";
  const endMarker = "  function validVoiceStudioVaultId";
  const startIndex = source.indexOf(startMarker);
  const endIndex = source.indexOf(endMarker);
  assert.ok(startIndex !== -1, "helper startMarker found in integration.js");
  assert.ok(endIndex !== -1, "helper endMarker found in integration.js");
  assert.ok(startIndex < endIndex, "helper slice order is valid");
  return source.slice(startIndex, endIndex);
}

const handlerBlock = extractProductionHandler(integrationSource);
const helperBlock = extractFeedbackHelper(integrationSource);

const EXPECTED_MESSAGES = {
  vi: {
    filtered: "Đã áp dụng bộ lọc.",
    all: "Đã hiển thị tất cả hồ sơ.",
    page: "Đã tải trang hồ sơ.",
    refreshed: "Đã làm mới hồ sơ.",
  },
  en: {
    filtered: "Filters applied.",
    all: "Showing all profiles.",
    page: "Profile page loaded.",
    refreshed: "Profiles refreshed.",
  },
  zh: {
    filtered: "已应用筛选条件。",
    all: "已显示全部档案。",
    page: "档案页已加载。",
    refreshed: "档案已刷新。",
  },
};

function createTestContext(overrides = {}) {
  const ctx = {
    console,
    ...overrides,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(i18nSource, ctx);
  assert.ok(ctx.TOANAASI18n, "ctx.TOANAASI18n must be initialized by portal-i18n.js");
  vm.runInContext(helperBlock, ctx);
  assert.ok(
    typeof ctx.voiceStudioFeedbackText === "function",
    "voiceStudioFeedbackText must be defined in the same context"
  );
  return ctx;
}

function runInContextProductionBlock(ctx, env) {
  Object.assign(ctx, {
    action: env.action,
    fields: env.fields || {},
    route: env.route || "/voice-studio",
    base:
      env.base ||
      (() => ({
        voiceStudioReadState: "ready",
        capabilities: { "voice-studio-page": true },
      })),
    currentPortalPath: env.currentPortalPath || (() => "/voice-studio"),
    voiceStudioFilterPayload:
      env.voiceStudioFilterPayload ||
      ((f) => ({ q: f.q || "", tag: f.tag || "", state: f.state || "all" })),
    voiceStudioListOffset:
      env.voiceStudioListOffset || ((v) => (v === 0 || v === "0" ? 0 : 50)),
    voiceVaultIdFromPath:
      env.voiceVaultIdFromPath ||
      ((r) => (r.startsWith("/voice-studio/vault-") ? "vault-uuid-1234" : null)),
    hydrateVoiceStudio:
      env.hydrateVoiceStudio ||
      (async () => ({ vaults: [], events: [], listing: {} })),
    hydrateVoiceVault:
      env.hydrateVoiceVault ||
      (async () => ({ vault: { id: "vault-uuid-1234" }, scripts: [], versions: [] })),
    toast: env.toast || (() => {}),
  });

  return vm.runInContext(`(async () => {\n${handlerBlock}\n})()`, ctx);
}

test("TaskA: actual catalogue keys match literal expected strings in vi, en, zh", () => {
  const ctx = createTestContext();
  const keys = ["filtered", "all", "page", "refreshed"];

  for (const locale of ["vi", "en", "zh"]) {
    ctx.TOANAASI18n.setLocale(locale, { emit: false });
    for (const key of keys) {
      const fullKey = `customerVoiceStudio.feedback.${key}`;
      const translated = ctx.TOANAASI18n.t(fullKey);
      assert.strictEqual(
        translated,
        EXPECTED_MESSAGES[locale][key],
        `Catalogue mismatch for ${fullKey} in ${locale}`
      );
    }
  }
});

test("TaskA: voiceStudioFeedbackText helper fallback handling within the same context", () => {
  const ctx = createTestContext();
  const realI18n = ctx.TOANAASI18n;

  realI18n.setLocale("vi", { emit: false });
  assert.strictEqual(
    ctx.voiceStudioFeedbackText("filtered", "Fallback"),
    "Đã áp dụng bộ lọc."
  );

  // 1. Missing / invalid key returns fallback
  assert.strictEqual(
    ctx.voiceStudioFeedbackText("nonexistent_key", "Fallback"),
    "Fallback"
  );

  // The real catalogue export is read-only. Exercise optional dependency
  // failures in fresh helper contexts rather than modifying that export.
  for (const optionalApi of [undefined, null, {}, { t: key => key }, { t: () => "" }, { t: () => null }, { t: () => 7 }]) {
    const helperContext = vm.createContext({ window: { TOANAASI18n: optionalApi } });
    vm.runInContext(helperBlock, helperContext);
    assert.strictEqual(helperContext.voiceStudioFeedbackText("filtered", "Fallback"), "Fallback");
  }
  assert.strictEqual(
    ctx.voiceStudioFeedbackText("filtered", "Fallback"),
    "Đã áp dụng bộ lọc."
  );
});

test("TaskA: ready filter query/clear/page/listrefresh/detailrefresh in 3 locales, exact messages", async () => {
  const testMatrix = [
    {
      action: "voice-studio-filter",
      fields: { q: "tiếng Việt có dấu 🔤", tag: "audio", state: "active" },
      expectedKey: "filtered",
      isFilter: true,
    },
    {
      action: "voice-studio-filter-clear",
      fields: {},
      expectedKey: "all",
      isClear: true,
    },
    {
      action: "voice-studio-page",
      fields: { __voiceStudioOffset: 50 },
      expectedKey: "page",
      isPage: true,
    },
    {
      action: "voice-studio-refresh",
      route: "/voice-studio",
      expectedKey: "refreshed",
      isRefreshList: true,
    },
    {
      action: "voice-studio-refresh",
      route: "/voice-studio/vault-1234",
      expectedKey: "refreshed",
      isRefreshDetail: true,
    },
  ];

  const ctx = createTestContext();

  for (const locale of ["vi", "en", "zh"]) {
    ctx.TOANAASI18n.setLocale(locale, { emit: false });
    for (const item of testMatrix) {
      const toasts = [];
      let capturedFilter = null;
      let capturedOffset = null;
      let detailCalledWith = null;

      await runInContextProductionBlock(ctx, {
        action: item.action,
        fields: item.fields,
        route: item.route || "/voice-studio",
        base: () => ({
          voiceStudioReadState: "ready",
          capabilities: { "voice-studio-page": true },
        }),
        currentPortalPath: () => item.route || "/voice-studio",
        hydrateVoiceStudio: async (f, o) => {
          capturedFilter = f;
          capturedOffset = o;
          return { vaults: [], events: [], listing: {} };
        },
        hydrateVoiceVault: async (id) => {
          detailCalledWith = id;
          return { vault: { id }, scripts: [], versions: [] };
        },
        toast: (msg) => toasts.push(msg),
      });

      const expectedText = EXPECTED_MESSAGES[locale][item.expectedKey];
      assert.deepStrictEqual(
        toasts,
        [expectedText],
        `Failed toast for ${item.action} in ${locale}`
      );

      if (item.isClear) {
        assert.strictEqual(
          JSON.stringify(capturedFilter),
          JSON.stringify({ q: "", tag: "", state: "all" })
        );
        assert.strictEqual(capturedOffset, 0);
      } else if (item.isFilter) {
        assert.strictEqual(
          JSON.stringify(capturedFilter),
          JSON.stringify({ q: "tiếng Việt có dấu 🔤", tag: "audio", state: "active" })
        );
        assert.strictEqual(capturedOffset, 0);
      } else if (item.isPage) {
        assert.strictEqual(capturedFilter, undefined);
        assert.strictEqual(capturedOffset, 50);
      } else if (item.isRefreshDetail) {
        assert.strictEqual(detailCalledWith, "vault-uuid-1234");
      }
    }
  }
});

test("TaskA: strict ready gate rejects failed, undefined, null, empty readState; stale, null, route departure yield 0 toast", async () => {
  const ctx = createTestContext();
  ctx.TOANAASI18n.setLocale("vi", { emit: false });

  // 1. Non-ready read states
  for (const nonReady of ["failed", undefined, null, "", "loading", "idle"]) {
    for (const action of [
      "voice-studio-filter",
      "voice-studio-page",
      "voice-studio-refresh",
    ]) {
      const toasts = [];
      await runInContextProductionBlock(ctx, {
        action,
        fields: action === "voice-studio-page" ? { __voiceStudioOffset: 0 } : {},
        base: () => ({
          voiceStudioReadState: nonReady,
          capabilities: { "voice-studio-page": true },
        }),
        toast: (msg) => toasts.push(msg),
      });
      assert.deepStrictEqual(
        toasts,
        [],
        `Expected 0 toast for ${action} when readState is ${nonReady}`
      );
    }
  }

  // 2. Hydrate returns stale: true
  {
    const toasts = [];
    await runInContextProductionBlock(ctx, {
      action: "voice-studio-filter",
      fields: { q: "query", tag: "", state: "all" },
      hydrateVoiceStudio: async () => ({ stale: true }),
      toast: (msg) => toasts.push(msg),
    });
    assert.deepStrictEqual(toasts, [], "No toast when result.stale is true");
  }

  // 3. Hydrate returns null or undefined
  {
    const toasts = [];
    await runInContextProductionBlock(ctx, {
      action: "voice-studio-refresh",
      hydrateVoiceStudio: async () => null,
      toast: (msg) => toasts.push(msg),
    });
    assert.deepStrictEqual(toasts, [], "No toast when result is null");
  }

  // 4. Destination path changed during await
  {
    const toasts = [];
    let path = "/voice-studio";
    await runInContextProductionBlock(ctx, {
      action: "voice-studio-refresh",
      currentPortalPath: () => path,
      hydrateVoiceStudio: async () => {
        path = "/dashboard";
        return { vaults: [] };
      },
      toast: (msg) => toasts.push(msg),
    });
    assert.deepStrictEqual(toasts, [], "No toast if path changed during await");
  }
});

test("TaskA: route alias /voice-studio/new with form route /voice-studio still shows toast if path unchanged", async () => {
  const toasts = [];
  const ctx = createTestContext();
  ctx.TOANAASI18n.setLocale("vi", { emit: false });

  await runInContextProductionBlock(ctx, {
    action: "voice-studio-refresh",
    route: "/voice-studio",
    currentPortalPath: () => "/voice-studio/new",
    hydrateVoiceStudio: async () => ({ vaults: [] }),
    toast: (msg) => toasts.push(msg),
  });

  assert.deepStrictEqual(toasts, ["Đã làm mới hồ sơ."]);
});

test("TaskA: page offsets 0 and 50 preserved; capability false throws before GET", async () => {
  const ctx = createTestContext();
  ctx.TOANAASI18n.setLocale("vi", { emit: false });

  // Offset 0 preserved
  {
    const toasts = [];
    let capturedOffset = null;
    let capturedFilter = "uncalled";
    await runInContextProductionBlock(ctx, {
      action: "voice-studio-page",
      fields: { __voiceStudioOffset: 0 },
      hydrateVoiceStudio: async (f, o) => {
        capturedFilter = f;
        capturedOffset = o;
        return { vaults: [] };
      },
      toast: (msg) => toasts.push(msg),
    });
    assert.strictEqual(capturedFilter, undefined);
    assert.strictEqual(capturedOffset, 0);
    assert.deepStrictEqual(toasts, ["Đã tải trang hồ sơ."]);
  }

  // Offset 50 preserved
  {
    const toasts = [];
    let capturedOffset = null;
    await runInContextProductionBlock(ctx, {
      action: "voice-studio-page",
      fields: { __voiceStudioOffset: 50 },
      hydrateVoiceStudio: async (f, o) => {
        capturedOffset = o;
        return { vaults: [] };
      },
      toast: (msg) => toasts.push(msg),
    });
    assert.strictEqual(capturedOffset, 50);
    assert.deepStrictEqual(toasts, ["Đã tải trang hồ sơ."]);
  }

  // Capability false throws before calling hydrate
  {
    let hydrateCalled = false;
    const toasts = [];
    await assert.rejects(
      async () => {
        await runInContextProductionBlock(ctx, {
          action: "voice-studio-page",
          base: () => ({ capabilities: { "voice-studio-page": false } }),
          hydrateVoiceStudio: async () => {
            hydrateCalled = true;
            return {};
          },
          toast: (msg) => toasts.push(msg),
        });
      },
      { message: "Cần signed Web session để xem Voice Vault riêng tư." }
    );
    assert.strictEqual(hydrateCalled, false);
    assert.deepStrictEqual(toasts, []);
  }
});

test("TaskA: rejections propagate directly and produce zero toast", async () => {
  const ctx = createTestContext();
  const toasts = [];

  await assert.rejects(
    async () => {
      await runInContextProductionBlock(ctx, {
        action: "voice-studio-refresh",
        hydrateVoiceStudio: async () => {
          throw new Error("Network timeout during hydration");
        },
        toast: (msg) => toasts.push(msg),
      });
    },
    { message: "Network timeout during hydration" }
  );

  assert.deepStrictEqual(toasts, []);
});

test("Every Voice read branch suppresses failed, stale and departed feedback in every locale", async () => {
  const id = "00000000-0000-4000-8000-000000000001";
  const cases = [
    { action: "voice-studio-filter", fields: { q: "Hồ sơ – 声音", tag: "", state: "all" }, route: "/voice-studio" },
    { action: "voice-studio-filter-clear", fields: {}, route: "/voice-studio" },
    { action: "voice-studio-page", fields: { __voiceStudioOffset: 50 }, route: "/voice-studio" },
    { action: "voice-studio-refresh", fields: {}, route: "/voice-studio" },
    { action: "voice-studio-refresh", fields: {}, route: `/voice-studio/${id}`, detail: true }
  ];
  const modes = ["failed", "stale", "null-result", "undefined-result", "departed", "missing-state", "rejected"];
  let checked = 0;
  for (const locale of ["vi", "en", "zh"]) {
    const ctx = createTestContext();
    ctx.TOANAASI18n.setLocale(locale, { emit: false });
    for (const item of cases) for (const mode of modes) {
      let path = item.route;
      let readState = "ready";
      const toasts = [], calls = [];
      const fail = new Error("controlled hydration failure");
      const hydrate = async (...args) => {
        calls.push(args);
        if (mode === "failed") readState = "failed";
        if (mode === "missing-state") readState = undefined;
        if (mode === "departed") path = "/dashboard";
        if (mode === "rejected") throw fail;
        if (mode === "null-result") return null;
        if (mode === "undefined-result") return undefined;
        if (mode === "stale") return item.detail ? null : { stale: true };
        return item.detail ? { vault: { id }, scripts: [], versions: [] } : { vaults: [], events: [], listing: {} };
      };
      const invoke = () => runInContextProductionBlock(ctx, {
        ...item,
        base: () => ({ voiceStudioReadState: readState, capabilities: { "voice-studio-page": true } }),
        currentPortalPath: () => path,
        voiceVaultIdFromPath: route => route === `/voice-studio/${id}` ? id : null,
        hydrateVoiceStudio: item.detail ? async () => { throw new Error("wrong list hydrator"); } : hydrate,
        hydrateVoiceVault: item.detail ? hydrate : async () => { throw new Error("wrong detail hydrator"); },
        toast: message => toasts.push(message)
      });
      if (mode === "rejected") await assert.rejects(invoke, error => error === fail);
      else await invoke();
      assert.deepEqual(toasts, [], `${locale}/${item.action}/${item.detail ? "detail" : "list"}/${mode}`);
      assert.equal(calls.length, 1);
      if (item.detail) assert.equal(calls[0][0], id);
      checked++;
    }
  }
  assert.equal(checked, 105);
});

test("New-profile route keeps filter and refresh feedback in all three locales", async () => {
  for (const locale of ["vi", "en", "zh"]) {
    const ctx = createTestContext();
    ctx.TOANAASI18n.setLocale(locale, { emit: false });
    for (const [action, key] of [["voice-studio-filter", "filtered"], ["voice-studio-refresh", "refreshed"]]) {
      const toasts = [];
      await runInContextProductionBlock(ctx, { action, route: "/voice-studio", fields: { q: "Giữ nguyên – 声音", tag: "", state: "all" }, currentPortalPath: () => "/voice-studio/new", toast: message => toasts.push(message) });
      assert.deepEqual(toasts, [EXPECTED_MESSAGES[locale][key]]);
    }
  }
});
