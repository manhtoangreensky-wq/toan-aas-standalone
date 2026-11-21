import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const raw = fs.readFileSync(new URL("../fixtures/media-audio-read-feedback-reviewed.json", import.meta.url));
const fail = "Unreviewed media audio read feedback";
const count = (source, part) => source.split(part).length - 1;
assert.equal(createHash("sha256").update(raw).digest("hex"),
  "8d54a2e60594277fd952e7323f5518bed6eb2dfc2e2e42faa81100fadb515cd8", fail + " authority");
const fixture = JSON.parse(raw), edits = fixture.canonicalChanges;
const integration = "static/portal/integration.js", i18n = "static/portal/portal-i18n.js";
assert.equal(fixture.schema, "MEDIA_AUDIO_READ_FEEDBACK_REVIEWED_V1", fail);
assert.equal(fixture.task, "MEDIA-AUDIO-READ-FEEDBACK-20261121", fail);
assert.equal(fixture.base, "c8b14ade33ed62f2fefb34fe0d14aca198e03a8e", fail);
assert.equal(edits.length, 4, fail);
assert.deepEqual(edits.map(edit => edit.file), [integration, integration, integration, i18n], fail);
assert.ok(edits.every(edit => edit.count === 1 && typeof edit.old === "string" && edit.old
  && typeof edit.new === "string" && edit.new), fail);
const keys = fixture.copyRows.map(row => "mediaReadFeedback." + row[0]);
assert.deepEqual(keys, ["mediaReadFeedback.audioFiltered", "mediaReadFeedback.audioAll",
  "mediaReadFeedback.audioPage", "mediaReadFeedback.audioReadFailed",
  "mediaReadFeedback.audioFilterUnavailable", "mediaReadFeedback.audioPageUnavailable"], fail);
assert.ok(fixture.copyRows.every(row => row.length === 4
  && row.every(value => typeof value === "string" && value.length > 0)), fail);
const readerOwner = "  async function hydrateMediaAudioAssets(filterValue, offsetValue) {";
const readerNext = '  const AUDIO_CHANGE_REQUEST_OPERATIONS = new Set(["inspect", "convert_mp3", "convert_m4a", "normalize"]);';
const audioOwned = source => /\bmediaReadFeedback(?:\.audio[\w.$]*|audio[\w.$]*)/.test(source)
  || /\bmediaReadFeedbackText\s*\(\s*["']audio[^"']*/.test(source);
function boundary(source, marker) {
  assert.equal(count(source, marker), 1, fail + " unique owner " + marker);
  return source.indexOf(marker);
}
function readerFlag(source) {
  const start = source.indexOf(readerOwner), end = source.indexOf(readerNext, start);
  return start >= 0 && end > start && /["']?failed["']?\s*:/.test(source.slice(start, end));
}

// Historical input projection only. Current acceptance separately checks all
// complete physical LF sources against Git BASE + four exact forward records.
export function mediaAudioReadFeedbackHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail + " source type");
  assert.equal(typeof file, "string", fail + " file type");
  if (file !== integration && file !== i18n) return source;
  if (!audioOwned(source) && !(file === integration && readerFlag(source))) return source;
  const group = edits.filter(edit => edit.file === file);
  for (const edit of group) assert.equal(count(source, edit.new), 1, fail + " exact complete unique records");
  const positions = group.map(edit => source.indexOf(edit.new));
  assert.ok(positions.every((point, index) => index === 0 || point > positions[index - 1]), fail + " record order");
  if (file === integration) {
    const readerStart = boundary(source, readerOwner), readerEnd = boundary(source, readerNext);
    assert.ok(readerEnd > readerStart, fail + " reader owner order");
    assert.equal(source.slice(readerStart, readerEnd), group[0].new + "\n", fail + " full bounded reader");
    const actionStart = boundary(source, "  async function handleAction(event) {");
    const actionEnd = boundary(source, "  function synchronizeScriptToScreenEpisodeFields(target) {");
    const next = '      if (action === "media-workspace-refresh") {';
    const nextAt = boundary(source, next);
    assert.ok(actionStart < positions[1] && positions[2] < nextAt && nextAt < actionEnd, fail + " action owner order");
    assert.equal(positions[2], positions[1] + group[1].new.length + 1, fail + " adjacent filter/page");
    assert.ok(source.slice(positions[2] + group[2].new.length).startsWith("\n" + next), fail + " action placement");
    for (const edit of group) assert.equal(count(source, edit.old), 0, fail + " mixed old/new records");
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
  assert.equal(audioOwned(result), false, fail + " unknown/detached audio namespace");
  assert.equal(file === integration && readerFlag(result), false, fail + " leftover reader failed flag");
  return result;
}

export function mediaAudioReadFeedbackHistoricalSnapshot(entries, locale) {
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  assert.ok(index > 0, fail + " locale");
  assert.ok(Array.isArray(entries), fail + " entries");
  assert.ok(entries.every(entry => Array.isArray(entry) && entry.length === 2), fail + " entry shape");
  const owned = entries.filter(([key]) => typeof key === "string"
    && (key.startsWith("mediaReadFeedback.audio") || key.startsWith("mediaReadFeedbackaudio")));
  if (!owned.length) return entries;
  assert.deepEqual(owned, fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index]]),
    fail + " exact ordered unique audio namespace");
  return entries.filter(([key]) => !keys.includes(key));
}
