import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {File} from "node:buffer";
import {writeSources, writeRuntime, ACTION, ASSET_ID, HOSTILE, publicAsset, publicLifecycle} from "./helpers/vault-action-write-runtime.mjs";
import {LOCALES, OPERATIONS, FIXED, COPY, drain, snapshot, postState, beforeState,
  expectToast, expectBusy, expectIsolated, expectTransport, finish} from "./helpers/vault-action-write-support.mjs";

const source = writeSources();
const create = (locale, operation) => writeRuntime(locale, {operation, source});
function expectFinished(runtime) {
  expectBusy(runtime, false);
  assert.ok(runtime.submissions().every(entry => entry.inFlight === false));
  expectIsolated(runtime);
}
function expectSuccessState(runtime) {
  const state = postState(runtime.operation);
  assert.deepEqual(snapshot(runtime.state.vaultItems), [publicAsset(state)]);
  assert.equal(runtime.state.assetVaultReadState, "ready");
  assert.equal(runtime.state.pageStates["/asset-vault"], "ready");
  assert.deepEqual(snapshot(runtime.state.assetVaultListing), {
    filters: {q: "SYNTHETIC_QUERY", state: "all"},
    pagination: {limit: 50, offset: 50, returned: 1, has_more: false, next_offset: null, previous_offset: 0}
  });
  if (runtime.operation !== "upload") assert.deepEqual(snapshot(runtime.state.assetVaultLifecycle), {
    asset_id: ASSET_ID, readState: "ready", lifecycle: {
      state, state_reason: state === "archived" ? "owner_archived" : "available", lifecycle_revision: 8,
      created_at: "2026-11-19T00:00:00Z", updated_at: "2026-11-20T00:00:00Z",
      archived_at: state === "archived" ? "2026-11-20T00:00:00Z" : "", restore_available: state === "archived",
      reference_summary: {total_count: 3, hard_blocker_count: 1, references: [
        {reason: "support_evidence_retention", count: 1, hard_blocker: true},
        {reason: "media_library_reference", count: 2, hard_blocker: false}
      ]}
    }
  });
}

test("WRITE physical source binding keeps full dispatcher/api/helpers and one read-only exposure", () => {
  const runtime = create("en", "upload");
  for (const key of ["integration", "i18n"]) {
    const raw = fs.readFileSync(runtime.binding.paths[key], "utf8");
    assert.equal(runtime.source.raw[key], raw);
    assert.equal(runtime.binding.hashes[key], createHash("sha256").update(raw).digest("hex"));
  }
  assert.equal(runtime.binding.executedBytes, runtime.binding.physicalBytes + runtime.binding.exposureBytes);
  assert.notEqual(runtime.binding.executedHash, runtime.binding.hashes.integration);
  assert.deepEqual(runtime.submissions(), []);
  assert.equal(runtime.network.length, 0);
  expectIsolated(runtime);
});

for (const locale of LOCALES) {
  for (const operation of OPERATIONS) {
    const representative = locale === "vi" && operation === "upload";
    test(`${representative ? "WRITE_REP" : "WRITE"} fixed ${locale} ${operation}`, async () => {
      const runtime = create(locale, operation), work = runtime.run();
      expectBusy(runtime, true);
      await finish(runtime, work, {message: FIXED[operation]});
      await expectTransport(runtime);
      assert.equal(runtime.network.length, operation === "upload" ? 2 : 4);
      expectSuccessState(runtime);
      expectFinished(runtime);
      expectToast(runtime, COPY[locale][operation]);
    });
    for (const [kind, message] of [["absent", undefined], ["null", null], ["empty", ""]]) {
      test(`WRITE falsy ${kind} ${locale} ${operation}`, async () => {
        const runtime = create(locale, operation), work = runtime.run();
        await finish(runtime, work, {message});
        await expectTransport(runtime);
        expectFinished(runtime);
        expectToast(runtime, COPY[locale][operation]);
      });
    }
    test(`WRITE duplicate pending ${locale} ${operation} preserves lock and stops second transport`, async () => {
      const runtime = create(locale, operation), work = runtime.run();
      const firstKey = runtime.submissions()[0].key;
      assert.equal(runtime.pending.length, 1);
      await runtime.run();
      assert.equal(runtime.pending.length, 1, "Duplicate never sends another GET/POST");
      expectBusy(runtime, true);
      assert.equal(runtime.submissions()[0].key, firstKey);
      expectToast(runtime, COPY[locale][operation + "Pending"], true);
      runtime.clearToasts();
      await finish(runtime, work);
      await expectTransport(runtime);
      expectFinished(runtime);
      expectToast(runtime, COPY[locale][operation]);
    });
    test(`WRITE invalid local input ${locale} ${operation} blocks before request/submission`, async () => {
      const runtime = create(locale, operation);
      const fields = operation === "upload" ? {file: new File([], "EMPTY.png", {type: "image/png"})} : {};
      const detail = operation === "upload" ? {} : {vaultAssetId: "NOT_A_UUID"};
      await runtime.run(operation, fields, detail);
      assert.equal(runtime.network.length, 0);
      assert.deepEqual(runtime.submissions(), []);
      expectFinished(runtime);
      expectToast(runtime, COPY[locale][operation + "Invalid"], true);
    });
  }
  for (const [kind, fields, key] of [
    ["display length", {display_name: "x".repeat(121)}, "uploadDisplay"],
    ["project ID", {project_id: "NOT_A_UUID"}, "uploadProject"]
  ]) {
    test(`WRITE upload invalid ${kind} ${locale} preserves validation`, async () => {
      const runtime = create(locale, "upload");
      await runtime.run("upload", fields);
      assert.equal(runtime.network.length, 0);
      assert.deepEqual(runtime.submissions(), []);
      expectFinished(runtime);
      expectToast(runtime, COPY[locale][key], true);
    });
  }
  test(`WRITE upload malformed success asset ${locale} remains error and releases busy`, async () => {
    const runtime = create(locale, "upload"), work = runtime.run();
    await finish(runtime, work, {mutationData: {asset: {...publicAsset(), id: "NOT_A_UUID"}}});
    await expectTransport(runtime);
    assert.equal(runtime.network.length, 1, "Invalid asset receipt cannot trigger post-success hydration");
    expectFinished(runtime);
    expectToast(runtime, COPY[locale].uploadResponse, true);
  });
  for (const operation of ["archive", "restore"]) {
    for (const guard of ["route", "permission"]) {
      test(`WRITE ${operation} ${guard} guard ${locale} blocks before request/submission`, async () => {
        const runtime = create(locale, operation);
        if (guard === "route") runtime.mutate("route", "/dashboard");
        else runtime.mutate("capability", "asset-vault-" + operation);
        await runtime.run();
        assert.equal(runtime.network.length, 0);
        assert.deepEqual(runtime.submissions(), []);
        expectFinished(runtime);
        expectToast(runtime, COPY[locale][operation + (guard === "route" ? "Route" : "Permission")], true);
      });
    }
    for (const malformed of [false, true]) {
      test(`WRITE ${operation} ${malformed ? "malformed" : "wrong-state"} preflight ${locale} never writes`, async () => {
        const runtime = create(locale, operation), work = runtime.run();
        const lifecycle = malformed
          ? {...publicLifecycle(beforeState(operation)), lifecycle_revision: 0}
          : publicLifecycle(operation === "archive" ? "archived" : "active");
        await finish(runtime, work, {lifecycleData: {lifecycle}});
        assert.equal(runtime.network.length, 1);
        assert.equal(runtime.network[0].method, "GET");
        assert.equal(runtime.network[0].path, `/api/v1/asset-vault/${ASSET_ID}/lifecycle`);
        if (malformed) {
          assert.equal(runtime.state.assetVaultLifecycle.readState, "guarded");
          assert.equal(runtime.state.assetVaultLifecycle.lifecycle, null);
        }
        assert.equal(runtime.submissions().length, 1, "Unacknowledged local failure retains retry intent");
        expectFinished(runtime);
        expectToast(runtime, COPY[locale][operation + "State"], true);
      });
    }
  }
}

for (const operation of OPERATIONS) {
  for (const [kind, text] of [
    ["hostile", HOSTILE], ["customer", "客户原文：SYNTHETIC CUSTOMER REQUEST — giữ nguyên 100%"]
  ]) {
    const representative = operation === "archive" && kind === "hostile";
    test(`${representative ? "WRITE_REP" : "WRITE"} raw en ${operation} ${kind}`, async () => {
      const runtime = create("en", operation), work = runtime.run();
      await finish(runtime, work, {message: text});
      await expectTransport(runtime);
      expectFinished(runtime);
      expectToast(runtime, text);
    });
  }
  const other = operation === "upload" ? FIXED.archive : FIXED.upload;
  for (const [kind, input, displayed] of [
    ["outer whitespace", " " + FIXED[operation] + " ", FIXED[operation]],
    ["internal whitespace", FIXED[operation].replace(" ", "  "), FIXED[operation].replace(" ", "  ")],
    ["substring only", "PREFIX " + FIXED[operation] + " SUFFIX", "PREFIX " + FIXED[operation] + " SUFFIX"],
    ["other action fixed literal", other, other]
  ]) {
    test(`WRITE finite-match ${operation} ${kind} stays raw under existing toast normalization`, async () => {
      const runtime = create("zh", operation), work = runtime.run();
      await finish(runtime, work, {message: input});
      await expectTransport(runtime);
      expectFinished(runtime);
      expectToast(runtime, displayed);
    });
  }
  for (const [kind, message] of [["zero", 0], ["false", false]]) {
    test(`WRITE falsy ${kind} en ${operation} preserves existing fallback truthiness`, async () => {
      const runtime = create("en", operation), work = runtime.run();
      await finish(runtime, work, {message});
      expectFinished(runtime);
      expectToast(runtime, COPY.en[operation]);
    });
  }
  for (const mode of ["payload-false-http200", "http422-payload-true"]) {
    test(`WRITE api gate ${operation} ${mode} preserves arbitrary nonempty error text`, async () => {
      const runtime = create("en", operation), work = runtime.run();
      const message = HOSTILE + " RAW_SERVER_ERROR";
      await finish(runtime, work, {message, payloadOk: mode !== "payload-false-http200",
        responseOk: mode !== "http422-payload-true", status: mode === "http422-payload-true" ? 422 : 200});
      await expectTransport(runtime);
      assert.equal(runtime.pending.filter(row => row.kind === "mutation").length, 1, "No mutation retry");
      assert.equal(runtime.network.length, operation === "upload" ? 1 : 4, "Acknowledged archive/restore error re-reads selected projections");
      expectFinished(runtime);
      expectToast(runtime, message, true);
    });
  }
  for (const failed of [false, true]) {
    test(`WRITE cleanup ${operation} after ${failed ? "acknowledged error" : "success"} preserves followup intent rules`, async () => {
      const runtime = create("en", operation), first = runtime.run();
      await finish(runtime, first, {message: "FIRST_RAW_RECEIPT", payloadOk: !failed,
        responseOk: !failed, status: failed ? 422 : 200});
      const firstKey = await expectTransport(runtime);
      expectFinished(runtime);
      expectToast(runtime, "FIRST_RAW_RECEIPT", failed);
      if (operation === "upload") {
        assert.equal(runtime.submissions().length, 1);
        assert.equal(runtime.submissions()[0].key, firstKey);
      } else assert.deepEqual(runtime.submissions(), [], "Acknowledged archive/restore intent is discarded");
      runtime.clearToasts();
      const followup = runtime.run();
      expectBusy(runtime, true);
      assert.equal(runtime.submissions()[0].inFlight, true);
      await finish(runtime, followup, {message: "FOLLOWUP_RAW_RECEIPT", revision: 9});
      const nextKey = await expectTransport(runtime, {revision: 9, postIndex: 1});
      if (operation === "upload") assert.equal(nextKey, firstKey, "Unchanged upload fingerprint reuses preserved intent");
      else assert.notEqual(nextKey, firstKey, "New deliberate archive/restore gets a fresh key");
      expectFinished(runtime);
      expectToast(runtime, "FOLLOWUP_RAW_RECEIPT");
      assert.equal(runtime.pending.filter(row => row.kind === "mutation").length, 2);
    });
  }
}
