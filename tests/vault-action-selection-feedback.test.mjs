import test from "node:test";
import assert from "node:assert/strict";
import {physicalSources, vaultRuntime, IDS, lifecycle} from "./helpers/vault-action-read-runtime.mjs";

// Amendment requested by Root before the grouped RED run. This supplements,
// without editing, the frozen primary test/helper contract.
const source = physicalSources();
const snapshot = value => JSON.parse(JSON.stringify(value));
for (const locale of ["vi", "en", "zh"]) {
  for (const selectionReady of [false, true]) {
    for (const listFailed of [false, true]) {
      test(`${locale}/refresh selection amendment: initially unselected then new ${selectionReady ? "ready" : "loading"} lifecycle suppresses ${listFailed ? "failed" : "ready"} list feedback`, async () => {
        const runtime = vaultRuntime(locale, {source, selected: false});
        const refresh = runtime.run("refresh");
        assert.equal(runtime.pending.length, 1, "Original refresh captures no selected lifecycle");
        const selected = runtime.readLifecycle(IDS[0]);
        assert.equal(runtime.pending.length, 2, "New selection performs its own real lifecycle GET");
        if (selectionReady) {
          runtime.settle(1);
          assert.deepEqual(snapshot(await selected), lifecycle());
        }
        runtime.settle(0, {failed: listFailed});
        await refresh;
        assert.deepEqual(runtime.observe().toasts, [], "No feedback belongs to an obsolete selection snapshot");
        assert.equal(runtime.state.assetVaultReadState, listFailed ? "failed" : "ready");
        assert.equal(runtime.state.assetVaultLifecycle.asset_id, IDS[0]);
        assert.equal(runtime.state.assetVaultLifecycle.readState, selectionReady ? "ready" : "loading");
        if (!selectionReady) {
          runtime.settle(1);
          assert.deepEqual(snapshot(await selected), lifecycle());
        }
        const seen = runtime.observe();
        assert.deepEqual(seen.toasts, []);
        assert.deepEqual(seen.network.map(row => ({path: row.path, method: row.method})), [
          {path: "/api/v1/asset-vault", method: "GET"},
          {path: `/api/v1/asset-vault/${IDS[0]}/lifecycle`, method: "GET"}
        ]);
        assert.deepEqual(seen.storageWrites, []);
        assert.deepEqual(seen.navigations, []);
      });
    }
  }
}
