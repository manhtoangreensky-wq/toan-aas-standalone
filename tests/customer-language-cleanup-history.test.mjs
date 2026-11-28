import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {
  customerLanguageHistoricalSource as inverse,
  customerLanguageHistoricalSnapshot as snapshot
} from "./helpers/customer-language-cleanup-historical.mjs";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixtures/customer-language-cleanup-history.json", import.meta.url), "utf8"));
const lf = value => value.replace(/\r\n/g, "\n");
const sha = value => createHash("sha256").update(value).digest("hex");
const files = ["static/portal/portal.js", "static/portal/portal-i18n.js"];
const baseline = file => lf(execFileSync("git", ["show", fixture.base_sha + ":" + file], {encoding: "utf8", maxBuffer: 30e6}));
const sources = new Map(files.map(file => [file, {
  before: baseline(file),
  after: lf(fs.readFileSync(new URL("../" + file, import.meta.url), "utf8"))
}]));

for (const file of files) {
  const {before, after} = sources.get(file);
  test(file + ": recovers only the approved epoch, preserving foreign bytes and line endings", () => {
    assert.equal(sha(inverse(after, file)), sha(before));
    assert.equal(sha(inverse(before, file)), sha(before));
    assert.equal(sha(inverse(inverse(after, file), file)), sha(before));
    const foreign = "\n/* Khách giữ QA Studio Facebook TikTok <b>& */\n";
    assert.equal(sha(inverse(after + foreign, file)), sha(before + foreign));
    assert.equal(sha(inverse(after.replace(/\n/g, "\r\n"), file)), sha(before.replace(/\n/g, "\r\n")));
    assert.equal(inverse("foreign source", "static/portal/not-owned.js"), "foreign source");
  });
  test(file + ": every missing, changed or duplicate owned record is rejected", () => {
    for (const [index, row] of fixture.records.entries()) {
      if (row.file !== file) continue;
      assert.equal(after.split(row.after).length - 1, 1, "Unique record " + index);
      for (const replacement of ["", row.after.replace(/\S/, "$&_CHANGED"), row.after + row.after]) {
        const changed = after.replace(row.after, () => replacement);
        assert.throws(() => inverse(changed, file), /Unreviewed customer language/, "Record " + index);
      }
    }
  });
}

const read = (source, locale) => {
  const box = vm.createContext({});
  vm.runInContext(source, box);
  return JSON.parse(JSON.stringify(Object.entries(box.TOANAASI18n.messages[locale])));
};
for (const locale of ["vi", "en", "zh"]) {
  const {before, after} = sources.get("static/portal/portal-i18n.js");
  const old = read(before, locale), current = read(after, locale);
  test(locale + ": whole dictionaries recover exact order without changing customer entries", () => {
    assert.deepEqual(snapshot(current, locale), old);
    assert.deepEqual(snapshot(old, locale), old);
    const foreign = ["CUSTOMER", "QA metadata Studio Facebook TikTok"];
    assert.deepEqual(snapshot([...current, foreign], locale), [...old, foreign]);
    const tiny = [["accountCenter.profile.profileFact", "UNREVIEWED_OLDER_VALUE"]];
    assert.deepEqual(snapshot(tiny, locale), tiny, "Older partial fixtures must reach their own strict checks");
  });
  test(locale + ": every missing, changed or duplicate owned value is rejected", () => {
    for (const {key} of fixture.values) {
      const index = current.findIndex(row => row[0] === key);
      assert(index >= 0);
      assert.throws(() => snapshot(current.filter((_, i) => i !== index), locale), /Unreviewed customer language/);
      assert.throws(() => snapshot([...current, current[index]], locale), /Unreviewed customer language/);
      assert.throws(() => snapshot(current.map((row, i) => i === index ? [row[0], row[1] + "!"] : row), locale), /Unreviewed customer language/);
    }
  });
}
