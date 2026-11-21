import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {ROOT, IDS, CUSTOMER, hash, plain, physicalSources, collectionFields, runtime} from "./helpers/media-fixed-feedback-runtime.mjs";

const fixture = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/media-fixed-feedback-contract.json"), "utf8"));
const base = physicalSources();
for (const [key, file] of [["integration", "static/portal/integration.js"], ["i18n", "static/portal/portal-i18n.js"]]) {
  base.sources[key] = execFileSync("git", ["show", fixture.base + ":" + file],
    {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true});
  base.hashes[key] = hash(base.sources[key]);
}
for (const locale of ["vi", "en", "zh"]) {
  for (const message of [fixture.errors[0].old, CUSTOMER]) {
    test(`${locale}/${message === CUSTOMER ? "unknown" : "exact-known"}: real API rejection preserves raw payload message at the allowed-action outer catch`, async () => {
      const app = runtime(locale), before = app.observe().state;
      app.controlledMetadataHTTP(entry => {
        assert.equal(entry.method, "POST"); assert.equal(entry.path, "/media-workspace/collections");
        assert.equal(entry.body.title, CUSTOMER); assert.deepEqual(plain(entry.body.tags), ["Keep", "TikTok"]);
        assert.match(entry.body.idempotency_key, /^[A-Za-z0-9:_-]+$/);
        return {ok: false, status: 422, payload: {ok: false, status: "error", message, data: {}, error_code: "SYNTHETIC_REJECTION"}};
      });
      const actual = await app.dispatch("media-collection-create", collectionFields()), observed = app.observe();
      assert.equal(observed.network.length, 1);
      assert.deepEqual(observed.network.map(row => row.method), ["POST"]);
      assert.deepEqual(observed.navigation, []); assert.deepEqual(observed.forbidden, []);
      assert.deepEqual(observed.state, before, "Rejected API response cannot fabricate a success projection");
      assert.equal(actual, message);
      assert.equal(observed.toasts.at(-1).attributes.role, "alert");
    });
  }
  test(`${locale}: nonallowed physical catch adds no helper has-traps or payload/message/status getter reads versus complete BASE`, async () => {
    async function observe(source) {
      const app = runtime(locale, source ? {source} : {});
      const reads = {payload: 0, message: 0, status: 0, has: 0};
      const error = new Proxy({}, {
        has(target, key) { reads.has++; return Reflect.has(target, key); },
        get(target, key) {
          if (key === "payload") { reads.payload++; return {message: CUSTOMER}; }
          if (key === "message") { reads.message++; return "DO_NOT_PREFER_ERROR_MESSAGE"; }
          if (key === "status") { reads.status++; return 422; }
          return Reflect.get(target, key);
        }
      });
      const fields = Object.freeze(Object.defineProperty({}, "__mediaAudioOffset", {
        enumerable: true, get() { throw error; }
      }));
      const detail = Object.freeze({action: "media-audio-page", route: "/media-workspace/" + IDS[0], fields});
      await app.probe.handleAction(Object.freeze({detail}));
      const result = app.observe();
      assert.deepEqual(result.network, []); assert.deepEqual(result.forbidden, []);
      assert.equal(result.toasts.at(-1).text, CUSTOMER);
      return reads;
    }
    const baseline = await observe(base), candidate = await observe();
    assert.deepEqual(baseline, {payload: 2, message: 0, status: 0, has: 0});
    assert.deepEqual(candidate, baseline);
  });
}
