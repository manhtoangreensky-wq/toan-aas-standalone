import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const raw = fs.readFileSync(new URL("../fixtures/media-read-feedback-reviewed.json", import.meta.url));
const fail = "Unreviewed media read feedback";
const count = (source, part) => source.split(part).length - 1;
assert.equal(createHash("sha256").update(raw).digest("hex"),
  "5b924e5e0882a8ca649b64203a1d2af7360c63cd53c311a2b56f520c09feeac6", fail + " authority");
const fixture = JSON.parse(raw), edits = fixture.canonicalChanges;
const integration = "static/portal/integration.js", i18n = "static/portal/portal-i18n.js";
assert.equal(fixture.schema, "MEDIA_READ_FEEDBACK_REVIEWED_V1", fail);
assert.equal(fixture.task, "MEDIA-READ-FEEDBACK-20261121", fail);
assert.equal(fixture.base, "fb1bbcf1fa7d36ba0745082229d9d1237d488364", fail);
assert.equal(edits.length, 5, fail);
assert.deepEqual(edits.map(edit => edit.file), [integration, integration, integration, integration, i18n], fail);
assert.ok(edits.every(edit => edit.count === 1 && typeof edit.old === "string" && edit.old
  && typeof edit.new === "string" && edit.new), fail);
const keys = fixture.copyRows.map(row => "mediaReadFeedback." + row[0]);
assert.deepEqual(keys, ["mediaReadFeedback.filtered", "mediaReadFeedback.all", "mediaReadFeedback.page",
  "mediaReadFeedback.refreshed", "mediaReadFeedback.readFailed", "mediaReadFeedback.detailRefreshed",
  "mediaReadFeedback.detailFailed", "mediaReadFeedback.pageUnavailable"], fail);
assert.ok(fixture.copyRows.every(row => row.length === 4
  && row.every(value => typeof value === "string" && value.length > 0)), fail);
const owned = source => /\bmediaReadFeedback[\w.$]*/.test(source);
function boundary(source, marker) {
  assert.equal(count(source, marker), 1, fail + " unique owner " + marker);
  return source.indexOf(marker);
}

// Finite historical input projection only. New-release acceptance checks raw
// physical files against the forward-built candidate and all151 raw/LF pins.
export function mediaReadFeedbackHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source type");
  assert.equal(typeof file, "string", fail + " file type");
  if (file !== integration && file !== i18n) return source;
  if (!owned(source)) return source;
  const group = edits.filter(edit => edit.file === file);
  for (const edit of group) assert.equal(count(source, edit.new), 1, fail + " exact complete unique records");
  const positions = group.map(edit => source.indexOf(edit.new));
  assert.ok(positions.every((point, index) => index === 0 || point > positions[index - 1]), fail + " record order");
  if (file === integration) {
    const prior = boundary(source, "  async function hydratePromptTemplate(templateId) {");
    const next = boundary(source, "  function musicLibraryRequestIsCurrent(");
    assert.ok(prior < positions[0] && positions[0] < next, fail + " helper owner");
    assert.ok(source.slice(0, positions[0]).endsWith("      return null;\n    }\n  }\n\n"), fail + " helper placement");
    assert.ok(source.slice(positions[0] + group[0].new.length).startsWith("\n    return requestEpoch === currentEpoch"), fail + " helper next body");
    const actionStart = boundary(source, "  async function handleAction(event) {");
    const actionEnd = boundary(source, "  function synchronizeScriptToScreenEpisodeFields(target) {");
    assert.ok(positions.slice(1).every(point => point > actionStart && point < actionEnd), fail + " action owner");
    assert.equal(positions[2], positions[1] + group[1].new.length + 1, fail + " filter/page placement");
    for (const [index, nextOwner] of [
      [2, '      if (action === "media-audio-filter" || action === "media-audio-filter-clear") {'],
      [3, '      if (action === "media-audio-operation-handoff") {']
    ]) {
      boundary(source, nextOwner);
      assert.ok(source.slice(positions[index] + group[index].new.length).startsWith("\n" + nextOwner), fail + " action next boundary");
    }
    for (const edit of group.slice(1)) assert.equal(count(source, edit.old), 0, fail + " mixed old action");
  } else {
    const verify = boundary(source, "  function verifyEqualKeysets() {");
    const call = boundary(source, "  verifyEqualKeysets();");
    const freezeFunction = boundary(source, "  function deepFreeze(value) {");
    const freeze = boundary(source, "  deepFreeze(MESSAGES);");
    assert.ok(verify < positions[0] && positions[0] < call && call < freezeFunction && freezeFunction < freeze,
      fail + " catalogue owner order before freeze");
    assert.ok(source.slice(positions[0] + group[0].new.length).startsWith("\n\n  function deepFreeze(value) {"),
      fail + " catalogue placement");
  }
  let result = source;
  for (const edit of [...group].reverse()) result = result.replace(edit.new, () => edit.old);
  assert.equal(owned(result), false, fail + " unknown or detached namespace");
  return result;
}

export function mediaReadFeedbackHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0, fail + " locale");
  assert.ok(Array.isArray(entries), fail + " entries");
  assert.ok(entries.every(entry => Array.isArray(entry) && entry.length === 2), fail + " entry shape");
  const namespace = entries.filter(([key]) => typeof key === "string" && key.startsWith("mediaReadFeedback"));
  if (!namespace.length) return entries;
  assert.deepEqual(namespace, fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index]]),
    fail + " exact ordered unique namespace");
  return entries.filter(([key]) => !keys.includes(key));
}
