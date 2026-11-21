import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import vm from "node:vm";
import {mediaReadFeedbackHistoricalSnapshot as historical} from "./helpers/media-read-feedback-snapshot.mjs";
import {mediaCollectionHistoricalSource, mediaCollectionHistoricalSnapshot} from "./helpers/media-collection-locale-snapshot.mjs";
import {mediaAudioReadFeedbackHistoricalSnapshot} from "./helpers/media-audio-read-feedback-snapshot.mjs";

const raw = fs.readFileSync(new URL("./fixtures/media-read-feedback-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), fail = /Unreviewed media read feedback/;
const source = fs.readFileSync(new URL("../static/portal/portal-i18n.js", import.meta.url), "utf8");
const document = {documentElement: {lang: "vi", setAttribute() {}, getAttribute: () => null}};
const window = {document, navigator: {language: "vi"}};
vm.runInNewContext(source, {window, document, Intl, console}, {timeout: 10000});
const messages = window.TOANAASI18n.messages;
const freeze = value => {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
};
test("historical PR783 snapshot authority is pinned and frozen catalogue retains eight exact ordered keys perlocale", () => {
  assert.equal(createHash("sha256").update(raw).digest("hex"),
    "5b924e5e0882a8ca649b64203a1d2af7360c63cd53c311a2b56f520c09feeac6");
  assert.ok(Object.isFrozen(messages));
  for (const [index, locale] of ["vi", "en", "zh"].entries()) {
    assert.ok(Object.isFrozen(messages[locale]));
    const actual = mediaAudioReadFeedbackHistoricalSnapshot(Object.entries(messages[locale]), locale)
      .filter(([key]) => key.startsWith("mediaReadFeedback"));
    assert.deepEqual(actual, fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]));
  }
});

for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  const rows = fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]);
  test(`${locale}: finite snapshot strips only the eight reviewed ordered unique keys; unrelated references/input preserved`, () => {
    const first = ["customer.mediaReadFeedback.name", {literal: 'Facebook <img>& "TikTok"'}];
    const last = ["unknown.unrelated", {raw: ["audio", "media"]}];
    const input = freeze([first, ...rows.map(row => [...row]), last]), before = JSON.stringify(input);
    const result = historical(input, locale);
    assert.deepEqual(result, [first, last]);
    assert.equal(result[0], first); assert.equal(result[1], last);
    assert.equal(JSON.stringify(input), before);
    assert.equal(historical(result, locale), result);
    const interleaved = freeze([rows[0], first, ...rows.slice(1), last]);
    assert.deepEqual(historical(interleaved, locale), [first, last], "Arbitrary unrelated entries are not removed");
    const base = freeze(Object.entries(messages[locale]).filter(([key]) => !key.startsWith("mediaReadFeedback")));
    assert.equal(historical(base, locale), base);
    assert.deepEqual(historical(freeze(Object.entries(messages[locale])), locale), base);
  });
  for (const [kind, mutate] of [
    ["missing", rows => rows.slice(1)],
    ["changed", rows => rows.map((entry, index) => index === 0 ? [entry[0], "UNKNOWN"] : entry)],
    ["duplicate", rows => [...rows, rows[0]]],
    ["reordered", rows => rows.toReversed()],
    ["unknown", rows => [...rows, ["mediaReadFeedback.unknown", "UNKNOWN"]]],
    ["malformed prefix", rows => [...rows, ["mediaReadFeedbackUnknown", "UNKNOWN"]]],
    ["bare prefix", rows => [...rows, ["mediaReadFeedback", "UNKNOWN"]]],
    ["wrong value type", rows => [[rows[0][0], {literal: rows[0][1]}], ...rows.slice(1)]]
  ]) test(`${locale}: finite snapshot rejects ${kind} owned rows`, () => {
    assert.throws(() => historical(freeze(mutate(rows)), locale), fail);
  });
  test(`${locale}: old helper retains its own locale/type/shape Error identity before newest leaf`, () => {
    const oldFail = /Unreviewed media collection locale/;
    for (const value of [null, undefined, 1, {}, ["bad"], [["key"]]]) {
      assert.throws(() => mediaCollectionHistoricalSnapshot(value, locale), oldFail);
    }
    assert.throws(() => mediaCollectionHistoricalSnapshot([], "unknown"), oldFail);
    assert.throws(() => mediaCollectionHistoricalSource(null, "static/portal/portal-i18n.js"), oldFail);
  });
}
test("snapshot retains strict locale, array and pair shape without touching inputs", () => {
  for (const value of [null, undefined, 1, {}, ["bad"], [["key"]], [["key", "value", "extra"]]]) {
    assert.throws(() => historical(value, "vi"), fail);
  }
  for (const locale of [null, undefined, "", "unknown", {}, ["vi"]]) {
    assert.throws(() => historical([], locale), fail);
  }
});
