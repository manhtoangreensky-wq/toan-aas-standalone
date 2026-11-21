import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {audioReviewVisualHistoricalSource, audioReviewVisualHistoricalSnapshot} from "./audio-review-visual-snapshot.mjs";
import {audioReviewPendingHistoricalSource, audioReviewPendingHistoricalSnapshot} from "./audio-review-pending-snapshot.mjs";

const sha = value => createHash("sha256").update(value).digest("hex");
const raw = fs.readFileSync(new URL("../fixtures/audio-review-reviewed.json", import.meta.url));
const rootRaw = fs.readFileSync(new URL("../fixtures/audio-review-contract.json", import.meta.url));
const fail = "Unreviewed audio review";
const count = (source, text) => source.split(text).length - 1;
assert.equal(sha(raw), "195a9af197e2a30c971eb9df061413368d42fd9af9139c3bb57d18195de9bb8d", fail + " reviewed authority");
assert.equal(sha(rootRaw), "6528de3a693e4b89cf8e33c4f900723b4f02e506e78526012c808ece44f35163", fail + " Root authority");
const reviewed = JSON.parse(raw), contract = JSON.parse(rootRaw);
const I = "static/portal/integration.js", P = "static/portal/portal.js", L = "static/portal/portal-i18n.js";
const files = [I, P, L], fragments = reviewed.historicalFragments;
assert.equal(reviewed.schema, "AUDIO_REVIEW_REVIEWED_PROVENANCE_V1", fail);
assert.equal(contract.schema, "AUDIO_REVIEW_EXPECTED_CONTRACT_V1", fail);
assert.equal(reviewed.task, "AUDIO-REVIEW-FEEDBACK-20261121", fail);
assert.equal(contract.task, reviewed.task, fail);
assert.equal(reviewed.base, "7cb8cb10486f5c175dca5db2c286a9f93a133c23", fail);
assert.equal(contract.base, reviewed.base, fail);
assert.equal(reviewed.rootContractFile, "tests/fixtures/audio-review-contract.json", fail);
assert.equal(reviewed.rootContractRawSha256, sha(rootRaw), fail);
assert.equal(reviewed.canonicalRecords, 11, fail); assert.equal(contract.canonicalChanges.length, 11, fail);
assert.deepEqual(reviewed.allowedFiles, files, fail); assert.deepEqual(contract.allowedFiles, files, fail);
assert.deepEqual(files.map(file => contract.canonicalChanges.filter(row => row.file === file).length), [8, 2, 1], fail);
assert.equal(fragments.length, 5, fail); assert.deepEqual(fragments.map(row => row.file), [I, I, I, P, L], fail);
for (const row of fragments) {
  assert.ok(["owner", "oldOwner", "next", "old", "new"].every(key => typeof row[key] === "string" && row[key]), fail);
  assert.equal(sha(row.old), row.oldSha256, fail); assert.equal(sha(row.new), row.newSha256, fail);
}
assert.equal(reviewed.copyRows.length, 31, fail); assert.deepEqual(reviewed.copyRows, contract.copyRows, fail);
assert.equal(new Set(contract.copyRows.map(row => row.key)).size, 31, fail);
assert.deepEqual(reviewed.workers.map(row => [row.part, row.records]),
  [["feedback", 8], ["renderer", 2], ["catalogue", 1]], fail);
assert.ok(reviewed.workers.every(row => row.codeFailures === 0 && row.fullMapExact === true
  && row.publicSourcesExact === 4 && /^[a-f0-9]{64}$/.test(row.proposalRawSha256)
  && /^[a-f0-9]{64}$/.test(row.packetRawSha256)), fail);
assert.equal(reviewed.applicationBaseline.length, 151, fail);
assert.equal(new Set(reviewed.applicationBaseline.map(row => row.file)).size, 151, fail);
const added = [...contract.feedback, ...contract.resultRows], overrides = contract.staticRows;
assert.equal(added.length, 20, fail); assert.equal(overrides.length, 11, fail);
const newKeys = new Set(added.map(row => row.key)), overrideMap = new Map(overrides.map(row => [row.key, row]));
const newNamespace = key => typeof key === "string" &&
  (key.startsWith("audioWorkspace.feedback.review.") || key.startsWith("audioWorkspace.review.result."));
const rendererSignals = overrides.map(row => `audioWorkspaceText("${row.short}", "${row.vi}"`);
function owned(source, file) {
  if (file === I) return /\baudioHubReviewFeedbackText\b|audioWorkspace\.feedback\.review\.|mediaWorkspaceFeedbackText\("review\./.test(source);
  if (file === P) return /\baudioHubReviewSourceText\b/.test(source) || rendererSignals.some(text => source.includes(text));
  return /\bAUDIO_REVIEW_CUSTOMER_COPY\b|audioWorkspace\.feedback\.review\.|audioWorkspace\.review\.result\./.test(source);
}
function boundary(source, text) {
  assert.equal(count(source, text), 1, fail + " unique boundary " + text);
  return source.indexOf(text);
}
function order(...positions) {
  assert.ok(positions.every((value, index) => value >= 0 && (!index || value > positions[index - 1])),
    fail + " structural owner order");
}

// Finite historical-input compatibility only. Current acceptance independently
// compares all151 physical sources to BASE plus11 exact forward records.
export function audioReviewHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source type");
  assert.equal(typeof file, "string", fail + " file type");
  source = audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(source, file), file);
  if (!files.includes(file) || !owned(source, file)) return source;
  const group = fragments.filter(row => row.file === file), points = [];
  for (const row of group) {
    const start = boundary(source, row.owner), end = boundary(source, row.next);
    assert.ok(end > start, fail + " bounded owner order");
    assert.equal(source.slice(start, end), row.new, fail + " complete bounded region");
    assert.equal(count(source, row.new), 1, fail + " unique current region");
    points.push(start);
  }
  if (file === I) {
    const constants = boundary(source, "  const AUDIO_HUB_REVIEW_PACK_CHECK_KEYS = ");
    const action = boundary(source, "  async function handleAction(event) {");
    const actionEnd = boundary(source, "  function synchronizeScriptToScreenEpisodeFields(target) {");
    order(constants, points[0], action, points[1], points[2], actionEnd);
  } else if (file === P) {
    order(boundary(source, "  function mediaAudioOperationHandoffAsset(item, collection) {"), points[0],
      boundary(source, group[0].next));
    boundary(source, group[0].oldOwner);
  } else {
    const verify = boundary(source, "  function verifyEqualKeysets() {");
    const call = boundary(source, "  verifyEqualKeysets();");
    const freezeFunction = boundary(source, "  function deepFreeze(value) {");
    const freezeCall = boundary(source, "  deepFreeze(MESSAGES);");
    order(verify, points[0], call, freezeFunction, freezeCall);
    assert.ok(source.slice(points[0] + group[0].new.length).startsWith(group[0].next),
      fail + " immediate catalogue boundary");
  }
  let result = source;
  for (const row of [...group].reverse()) result = result.replace(row.new, () => row.old);
  assert.equal(owned(result, file), false, fail + " partial or detached owned marker");
  return result;
}

export function audioReviewHistoricalSnapshot(entries, locale) {
  assert.ok(["vi", "en", "zh"].includes(locale), fail + " locale");
  assert.ok(Array.isArray(entries) && entries.every(row => Array.isArray(row) && row.length === 2), fail + " entries");
  entries = audioReviewVisualHistoricalSnapshot(audioReviewPendingHistoricalSnapshot(entries, locale), locale);
  const current = entries.filter(([key]) => newNamespace(key));
  if (!current.length) {
    for (const [key, value] of entries) {
      const row = overrideMap.get(key);
      if (row) assert.notEqual(value, row[locale], fail + " partial override-only catalogue");
    }
    return entries;
  }
  assert.deepEqual(current.map(([key]) => key), added.map(row => row.key), fail + " exact20 owned key order");
  const positions = [];
  for (const row of [...added, ...overrides]) {
    const matches = entries.filter(([key]) => key === row.key);
    assert.equal(matches.length, 1, fail + " unique owned key " + row.key);
    assert.equal(matches[0][1], row[locale], fail + " exact locale value " + row.key);
    if (newKeys.has(row.key)) positions.push(entries.indexOf(matches[0]));
  }
  assert.ok(positions.every((at, index) => !index || at === positions[index - 1] + 1),
    fail + " consecutive20 new rows");
  return entries.filter(([key]) => !newKeys.has(key)).map(entry => {
    const row = overrideMap.get(entry[0]);
    return row ? [entry[0], row.previous[locale]] : entry;
  });
}
