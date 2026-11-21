import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import vm from "node:vm";
import {mediaAudioReadFeedbackHistoricalSnapshot as historical} from "./helpers/media-audio-read-feedback-snapshot.mjs";
import {mediaReadFeedbackHistoricalSnapshot as prior} from "./helpers/media-read-feedback-snapshot.mjs";
import {mediaDetailCustomerCopyHistoricalSnapshot} from "./helpers/media-detail-customer-copy-snapshot.mjs";

const raw = fs.readFileSync(new URL("./fixtures/media-audio-read-feedback-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), fail = /Unreviewed media audio read feedback/;
const old = JSON.parse(fs.readFileSync(new URL("./fixtures/media-read-feedback-reviewed.json", import.meta.url)));
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
test("physical frozen catalogue contains exactly six new ordered audio keys and eight unchanged old feedback keys", () => {
  assert.equal(createHash("sha256").update(raw).digest("hex"),
    "8d54a2e60594277fd952e7323f5518bed6eb2dfc2e2e42faa81100fadb515cd8");
  assert.ok(Object.isFrozen(messages));
  for (const [index, locale] of ["vi", "en", "zh"].entries()) {
    assert.ok(Object.isFrozen(messages[locale]));
    const entries = Object.entries(messages[locale]);
    assert.deepEqual(entries.filter(([key]) => key.startsWith("mediaReadFeedback.audio")),
      fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]));
    assert.deepEqual(historical(entries, locale).filter(([key]) => key.startsWith("mediaReadFeedback")),
      old.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]));
  }
});
for (const [index, locale] of ["vi", "en", "zh"].entries()) {
  const rows = fixture.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]);
  test(`${locale}: only six audio keys removed; old namespace, unrelated references and frozen caller bytes retained`, () => {
    const oldRows = old.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]);
    const first = ["customer.mediaReadFeedback.audioName", {literal: 'Facebook <img>& "TikTok"'}];
    const last = [42, {raw: "customer unchanged"}];
    const input = freeze([first, ...oldRows, ...rows.map(row => [...row]), last]), saved = JSON.stringify(input);
    const want = [first, ...oldRows, last], actual = historical(input, locale);
    assert.deepEqual(actual, want);
    want.forEach((entry, at) => assert.equal(actual[at], entry));
    assert.equal(JSON.stringify(input), saved);
    assert.equal(historical(actual, locale), actual);
    assert.deepEqual(historical(freeze([rows[0], first, ...rows.slice(1), last]), locale), [first, last]);
    const base = freeze(mediaDetailCustomerCopyHistoricalSnapshot(Object.entries(messages[locale]), locale)
      .filter(([key]) => !key.startsWith("mediaReadFeedback.audio")));
    assert.equal(historical(base, locale), base);
    assert.deepEqual(historical(freeze(Object.entries(messages[locale])), locale), base);
  });
  for (const [kind, mutate] of [
    ["missing", rows => rows.slice(1)],
    ["changed", rows => rows.map((entry, at) => at === 0 ? [entry[0], "UNKNOWN"] : entry)],
    ["duplicate", rows => [...rows, rows[0]]],
    ["reordered", rows => rows.toReversed()],
    ["unknown", rows => [...rows, ["mediaReadFeedback.audioUnknown", "UNKNOWN"]]],
    ["malformed prefix", rows => [...rows, ["mediaReadFeedbackaudioUnknown", "UNKNOWN"]]],
    ["bare audio prefix", rows => [...rows, ["mediaReadFeedback.audio", "UNKNOWN"]]],
    ["wrong value type", rows => [[rows[0][0], {literal: rows[0][1]}], ...rows.slice(1)]]
  ]) test(`${locale}: audio snapshot rejects ${kind} owned rows`, () => {
    assert.throws(() => historical(freeze(mutate(rows)), locale), fail);
  });
  test(`${locale}: prior snapshot keeps input/locale/shape errors and old-key failures before/after newest leaf`, () => {
    const priorFail = /Unreviewed media read feedback/;
    for (const value of [null, undefined, 1, {}, ["bad"], [["key"]], [["key", "value", "extra"]]]) {
      assert.throws(() => prior(value, locale), priorFail);
    }
    assert.throws(() => prior([], "unknown"), priorFail);
    const oldRows = old.copyRows.map(row => ["mediaReadFeedback." + row[0], row[index + 1]]);
    const changed = oldRows.map((entry, at) => at === 0 ? [entry[0], "UNKNOWN"] : entry);
    assert.deepEqual(historical(freeze([...changed, ...rows]), locale), changed, "Newest leaf cannot rewrite/validate old keys");
    assert.throws(() => prior(freeze([...changed, ...rows]), locale), priorFail);
    assert.throws(() => prior(freeze([...oldRows, ...rows.slice(1)]), locale), fail, "Actual newest namespace fault has its own Error");
  });
}
test("audio snapshot enforces strict locale/array/pair shapes without accepting wrappers", () => {
  for (const value of [null, undefined, 1, {}, ["bad"], [["key"]], [["key", "value", "extra"]]]) {
    assert.throws(() => historical(value, "vi"), fail);
  }
  for (const locale of [null, undefined, "", "unknown", {}, ["vi"], new String("vi")]) {
    assert.throws(() => historical([], locale), fail);
  }
});
