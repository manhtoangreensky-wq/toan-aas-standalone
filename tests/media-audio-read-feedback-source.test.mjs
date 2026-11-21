import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mediaAudioReadFeedbackHistoricalSource as historical} from "./helpers/media-audio-read-feedback-snapshot.mjs";
import {mediaReadFeedbackHistoricalSource as prior} from "./helpers/media-read-feedback-snapshot.mjs";
import {mediaDetailCustomerCopyHistoricalSource} from "./helpers/media-detail-customer-copy-snapshot.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const raw = fs.readFileSync(new URL("./fixtures/media-audio-read-feedback-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), hash = value => createHash("sha256").update(value).digest("hex");
const lf = value => value.replace(/\r\n/g, "\n"), fail = /Unreviewed media audio read feedback/;
const files = ["static/portal/integration.js", "static/portal/portal-i18n.js"];
const bases = Object.fromEntries(files.map(file => [file, lf(execFileSync("git",
  ["show", fixture.base + ":" + file], {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true}))]));
// PR784 is historical after the narrowly reviewed detail/pager/label change.
// Its exact old authority is unchanged. Current raw52-record/151-source
// acceptance lives in media-detail-customer-copy-source.test.mjs.
const physical = Object.fromEntries(files.map(file => [file,
  mediaDetailCustomerCopyHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file)]));
// This historical candidate still uses its original four-record forward replay.
const candidates = {...bases};
for (const edit of fixture.canonicalChanges) {
  assert.equal(edit.count, 1);
  assert.equal(candidates[edit.file].split(edit.old).length - 1, 1);
  candidates[edit.file] = candidates[edit.file].replace(edit.old, () => edit.new);
}

test("historical PR784: three actual worker results bind four exact records and reviewed LF-only transport repair", () => {
  assert.equal(hash(raw), "8d54a2e60594277fd952e7323f5518bed6eb2dfc2e2e42faa81100fadb515cd8");
  assert.equal(fixture.base, "c8b14ade33ed62f2fefb34fe0d14aca198e03a8e");
  assert.equal(fixture.canonicalChanges.length, 4);
  assert.equal(fixture.copyRows.length, 6);
  assert.equal(fixture.workers.length, 3);
  assert.deepEqual(fixture.workers.map(row => row.records), [1, 2, 1]);
  assert.deepEqual(fixture.workers.map(row => row.proposalRawSha256), [
    "2aaa90d614f9d70e722ef95420917e96994b05b733442f47d27bcf9f3537b8fd",
    "10e2849deac4505326d3061fa55971051fb762f13b387e2b2a62da34546e5958",
    "d0670e72d98a367e6a5bc0fa3bb8533f14b7548f908cbd787c7d231141da3c70"
  ]);
  assert.deepEqual(fixture.workers.map(row => row.transportBoundary), [
    "R1A_EXISTING_SINGLE_BASE_FINAL_LF_RESTORED_BOTH_FIELDS_NO_CODE_CHANGE", "NONE", "NONE"
  ]);
  for (const worker of fixture.workers) {
    assert.equal(worker.proposalExact, true);
    assert.equal(worker.fullMapExact, true);
    assert.equal(worker.publicSourcesExact, 3);
    assert.equal(worker.workerCodeFailures, 0);
    assert.equal(worker.applicationTakeover, false);
  }
  for (const name of ["providerCalls", "walletMutations", "productionDataMutations", "workerCodeFailures"]) {
    assert.equal(fixture[name], 0);
  }
  assert.equal(fixture.applicationTakeover, false);
  assert.equal(fixture.campaignStateOpened, false);
  const reader = fixture.canonicalChanges[0];
  assert.ok(reader.old.endsWith("  }\n") && reader.new.endsWith("  }\n"));
  assert.equal(reader.new.replace(", failed: true", ""), reader.old, "Only additive failed flag; final BASE LF retained");
  for (const file of files) {
    assert.equal(physical[file], candidates[file], "Exact complete forward-built LF-portable candidate: " + file);
    assert.notEqual(physical[file], bases[file]);
  }
});

test("historical PR784: all151 LF pins retain149 protected files after finite newest projection", () => {
  assert.equal(fixture.applicationBaseline.length, 151);
  assert.equal(new Set(fixture.applicationBaseline.map(row => row.file)).size, 151);
  assert.deepEqual(fixture.applicationBaseline.filter(row => row.changed).map(row => row.file).sort(), files.toSorted());
  assert.equal(fixture.applicationBaseline.filter(row => !row.changed).length, 149);
  for (const pin of fixture.applicationBaseline) {
    const physicalRaw = fs.readFileSync(path.join(ROOT, pin.file));
    const normalized = mediaDetailCustomerCopyHistoricalSource(lf(physicalRaw.toString("utf8")), pin.file);
    const actual = Buffer.from(normalized);
    assert.equal(hash(normalized), pin.candidateLfSha256, "Unprojected LF: " + pin.file);
    assert.ok([pin.candidateRawSha256, pin.candidateLfSha256, hash(normalized.replace(/\n/g, "\r\n"))]
      .includes(hash(actual)), "Only frozen measured/LF/uniformCRLF checkout: " + pin.file);
    if (!pin.changed) {
      assert.equal(pin.baseRawSha256, pin.candidateRawSha256, pin.file);
      assert.equal(pin.baseLfSha256, pin.candidateLfSha256, pin.file);
    } else assert.equal(hash(bases[pin.file]), pin.baseLfSha256, pin.file);
  }
});

test("historical projection only: exact audio records restore BASE while old namespace/customer/unrelated bytes survive", () => {
  const prefix = '/* CUSTOMER Facebook TikTok <img>& audio */\n';
  const suffix = '\nconst customer="untouched";';
  for (const file of files) {
    assert.equal(historical(bases[file], file), bases[file]);
    assert.equal(historical(physical[file], file), bases[file]);
    assert.equal(historical(historical(physical[file], file), file), bases[file]);
    assert.equal(historical(prefix + physical[file] + suffix, file), prefix + bases[file] + suffix);
    assert.equal(historical(physical[file], "customer/unrelated.txt"), physical[file]);
    assert.equal(historical(prefix + suffix, file), prefix + suffix);
    assert.ok(historical(physical[file], file).includes("mediaReadFeedback"), "PR783 namespace is not removed");
  }
});

for (const [index, edit] of fixture.canonicalChanges.entries()) {
  for (const [kind, mutate] of [
    ["changed", source => source.replace(edit.new, () => index === 0
      ? edit.new.replace("failed: true", "failed: false")
      : edit.new.replace("audioFiltered", "audioUNKNOWN").replace("audioPage", "audioUNKNOWN"))],
    ["duplicate", source => source + "\n" + edit.new],
    ["displaced", source => source.replace(edit.new, "") + "\n" + edit.new],
    ["partial/mixed", source => source.replace(edit.new, () => edit.old)]
  ]) test(`finite audio source record${index + 1}: rejects ${kind}`, () => {
    const candidate = index === 3 && kind === "partial/mixed"
      ? physical[edit.file].replace('"mediaReadFeedback.audioFiltered":"Đã lọc danh sách tệp âm thanh.",', "")
      : mutate(physical[edit.file]);
    assert.throws(() => historical(candidate, edit.file), fail);
  });
}

test("source detects isolated reader failed flag even without audio namespace, and isolated actions without changed reader", () => {
  const [reader, filter, page] = fixture.canonicalChanges;
  assert.throws(() => historical(bases[reader.file].replace(reader.old, () => reader.new), reader.file), fail);
  const actionOnly = bases[reader.file].replace(filter.old, () => filter.new).replace(page.old, () => page.new);
  assert.throws(() => historical(actionOnly, reader.file), fail);
  const modifiedFlagOnly = bases[reader.file].replace(reader.old, () => reader.new.replace("failed: true", "failed: false"));
  assert.throws(() => historical(modifiedFlagOnly, reader.file), fail);
});

for (const file of files) {
  test(`${file}: unknown audio prefixes and invalid/duplicate owner boundaries are rejected`, () => {
    for (const extra of [
      '\nconst unknown="mediaReadFeedback.audioUnknown";',
      '\nMESSAGES.vi["mediaReadFeedbackaudioUnknown"]="CUSTOMER";',
      '\nmediaReadFeedbackText("audioUnknown","CUSTOMER");'
    ]) assert.throws(() => historical(physical[file] + extra, file), fail);
    const markers = file.endsWith("/integration.js") ? [
      "  async function hydrateMediaAudioAssets(filterValue, offsetValue) {",
      '  const AUDIO_CHANGE_REQUEST_OPERATIONS = new Set(["inspect", "convert_mp3", "convert_m4a", "normalize"]);',
      "  async function handleAction(event) {", "  function synchronizeScriptToScreenEpisodeFields(target) {",
      '      if (action === "media-workspace-refresh") {'
    ] : ["  function verifyEqualKeysets() {", "  function deepFreeze(value) {", "  deepFreeze(MESSAGES);"];
    for (const marker of markers) {
      assert.throws(() => historical(physical[file].replace(marker, () => marker.replace(/[A-Za-z_]+/, "UNKNOWN")), file), fail);
      assert.throws(() => historical(physical[file] + "\n" + marker, file), fail);
    }
  });
}

test("source rejects reordered/detached actions, missing reader LF, reordered locales and post-freeze catalogue", () => {
  const [reader, filter, page, catalogue] = fixture.canonicalChanges;
  const swapped = physical[reader.file].replace(filter.new, "__AUDIO_SWAP__")
    .replace(page.new, () => filter.new).replace("__AUDIO_SWAP__", () => page.new);
  assert.throws(() => historical(swapped, reader.file), fail);
  const detachedPair = physical[reader.file].replace(filter.new + "\n" + page.new, "")
    .replace("  function synchronizeScriptToScreenEpisodeFields(target) {",
      () => filter.new + "\n" + page.new + "\n  function synchronizeScriptToScreenEpisodeFields(target) {");
  assert.throws(() => historical(detachedPair, reader.file), fail);
  assert.throws(() => historical(physical[reader.file].replace(reader.new, () => reader.new.slice(0, -1)), reader.file), fail);
  const moved = physical[catalogue.file].replace(catalogue.new, () => catalogue.old)
    .replace("  deepFreeze(MESSAGES);", () => "  deepFreeze(MESSAGES);\n" + catalogue.new.slice(0, -catalogue.old.length));
  assert.throws(() => historical(moved, catalogue.file), fail);
  assert.throws(() => historical(physical[catalogue.file].replace(catalogue.new,
    () => catalogue.new.replace("MESSAGES.vi", "MESSAGES.SWAP").replace("MESSAGES.en", "MESSAGES.vi").replace("MESSAGES.SWAP", "MESSAGES.en")), catalogue.file), fail);
  assert.equal(historical(physical[catalogue.file].replace(catalogue.new, () => catalogue.old), catalogue.file), bases[catalogue.file],
    "Whole absent catalogue is genuine BASE, not a partial addition");
});
test("strict source/file argument guards precede composition and retain prior Error identities", () => {
  for (const value of [undefined, null, 1, {}, [], new String("source")]) {
    assert.throws(() => historical(value, files[0]), fail);
    assert.throws(() => historical("BASE", value), fail);
    assert.throws(() => prior(value, files[0]), /Unreviewed media read feedback/);
    assert.throws(() => prior("BASE", value), /Unreviewed media read feedback/);
  }
});
