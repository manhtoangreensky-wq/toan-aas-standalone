import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mediaReadFeedbackHistoricalSource as historical} from "./helpers/media-read-feedback-snapshot.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const raw = fs.readFileSync(new URL("./fixtures/media-read-feedback-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), hash = value => createHash("sha256").update(value).digest("hex");
const lf = value => value.replace(/\r\n/g, "\n"), fail = /Unreviewed media read feedback/;
const files = ["static/portal/integration.js", "static/portal/portal-i18n.js"];
const bases = Object.fromEntries(files.map(file => [file, execFileSync("git",
  ["show", fixture.base + ":" + file], {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true})]).map(([file, value]) => [file, lf(value)]));
const physical = Object.fromEntries(files.map(file => [file, lf(fs.readFileSync(path.join(ROOT, file), "utf8"))]));
// Forward construction from immutable git BASE, not a historical inverse used
// to bless current application source.
const candidates = {...bases};
for (const edit of fixture.canonicalChanges) {
  assert.equal(edit.count, 1);
  assert.equal(candidates[edit.file].split(edit.old).length - 1, 1);
  candidates[edit.file] = candidates[edit.file].replace(edit.old, () => edit.new);
}

test("current physical source: four reviewed worker proposals produce exactly five records on BASE files", () => {
  assert.equal(hash(raw), "5b924e5e0882a8ca649b64203a1d2af7360c63cd53c311a2b56f520c09feeac6");
  assert.equal(fixture.base, "fb1bbcf1fa7d36ba0745082229d9d1237d488364");
  assert.equal(fixture.canonicalChanges.length, 5);
  assert.equal(fixture.copyRows.length, 8);
  assert.equal(fixture.workers.length, 4);
  assert.deepEqual(fixture.workers.map(row => row.records), [1, 2, 1, 1]);
  assert.deepEqual(fixture.workers.map(row => row.proposalRawSha256), [
    "c81b259949bdb3ec1c080a76e5cce4ceb212f944902dee1cb603c96009a39671",
    "9ed963fe4a115588160a1791dabd7296f755952318cae0ba0edafa9c49325c75",
    "c4f90e3a45343aafed4361aa9242c1b49f3b05a63b7335b22e29506dac671dbb",
    "fd9510c2c8b74e08f9b343dd0cd76d01c338967d2de812a042337c2403b5957f"
  ]);
  for (const worker of fixture.workers) {
    assert.equal(worker.proposalExact, true);
    assert.equal(worker.fullMapExact, true);
    assert.equal(worker.workerCodeFailures, 0);
    assert.equal(worker.applicationTakeover, false);
  }
  for (const file of files) {
    assert.equal(physical[file], candidates[file], "Exact complete forward-built LF-portable candidate: " + file);
    assert.notEqual(physical[file], bases[file]);
  }
});

test("current physical sources: all151 LF pins and exact checkout encodings retain149 protected application files", () => {
  assert.equal(fixture.applicationBaseline.length, 151);
  assert.equal(new Set(fixture.applicationBaseline.map(row => row.file)).size, 151);
  assert.deepEqual(fixture.applicationBaseline.filter(row => row.changed).map(row => row.file).sort(), files.toSorted());
  assert.equal(fixture.applicationBaseline.filter(row => !row.changed).length, 149);
  for (const pin of fixture.applicationBaseline) {
    const actual = fs.readFileSync(path.join(ROOT, pin.file));
    const normalized = lf(actual.toString("utf8"));
    assert.equal(hash(normalized), pin.candidateLfSha256, "Unprojected LF: " + pin.file);
    // Preserve measured local raw pins, while accepting Git's canonical LF or
    // uniform CRLF checkout only. No source, fixture or native raw pin is rewritten.
    assert.ok([pin.candidateRawSha256, pin.candidateLfSha256, hash(normalized.replace(/\n/g, "\r\n"))]
      .includes(hash(actual)), "Unreviewed checkout encoding: " + pin.file);
    if (!pin.changed) {
      assert.equal(pin.baseRawSha256, pin.candidateRawSha256, pin.file);
      assert.equal(pin.baseLfSha256, pin.candidateLfSha256, pin.file);
    } else {
      assert.equal(hash(bases[pin.file]), pin.baseLfSha256, pin.file);
    }
  }
});

test("historical projection only: BASE/no namespace unchanged; exact current records restore BASE idempotently", () => {
  const prefix = '/* CUSTOMER Facebook TikTok media audio <img>& */\n';
  const suffix = '\nconst customer="literal remains unchanged";';
  for (const file of files) {
    assert.equal(historical(bases[file], file), bases[file]);
    assert.equal(historical(physical[file], file), bases[file]);
    assert.equal(historical(historical(physical[file], file), file), bases[file]);
    assert.equal(historical(prefix + physical[file] + suffix, file), prefix + bases[file] + suffix);
    assert.equal(historical(physical[file], "customer/unrelated.txt"), physical[file]);
    assert.equal(historical(prefix + suffix, file), prefix + suffix);
  }
});

for (const [index, edit] of fixture.canonicalChanges.entries()) {
  for (const [kind, mutate] of [
    ["changed", source => source.replace(edit.new, () => edit.new.replace("mediaReadFeedback", "mediaReadFeedbackUNKNOWN"))],
    ["duplicate", source => source + "\n" + edit.new],
    ["displaced", source => source.replace(edit.new, "") + "\n" + edit.new],
    ["partial/mixed", source => source.replace(edit.new, () => edit.old)]
  ]) test(`finite source record${index + 1}: rejects ${kind} new records`, () => {
    // A whole-file catalogue rollback is genuine BASE and must remain allowed.
    // A partial catalogue removal, unlike BASE, retains owned namespace.
    const candidate = index === 4 && kind === "partial/mixed"
      ? physical[edit.file].replace('"mediaReadFeedback.filtered":"Đã lọc bộ sưu tập âm thanh.",', "")
      : mutate(physical[edit.file]);
    assert.throws(() => historical(candidate, edit.file), fail);
  });
}
for (const file of files) {
  test(`${file}: unknown/malformed namespace and wrong owner/boundary cannot be stripped`, () => {
    const source = physical[file];
    for (const extra of [
      '\nconst unknown="mediaReadFeedback.unknown";',
      '\nfunction mediaReadFeedbackUnknown() {}',
      '\nMESSAGES.vi["mediaReadFeedbackUnknown"]="CUSTOMER";'
    ]) assert.throws(() => historical(source + extra, file), fail);
    const markers = file.endsWith("/integration.js") ? [
      "  async function hydratePromptTemplate(templateId) {", "  function musicLibraryRequestIsCurrent(",
      "  async function handleAction(event) {", "  function synchronizeScriptToScreenEpisodeFields(target) {",
      '      if (action === "media-audio-filter" || action === "media-audio-filter-clear") {',
      '      if (action === "media-audio-operation-handoff") {'
    ] : ["  function verifyEqualKeysets() {", "  function deepFreeze(value) {", "  deepFreeze(MESSAGES);"];
    for (const marker of markers) {
      assert.throws(() => historical(source.replace(marker, () => marker.replace(/[A-Za-z_]+/, "UNKNOWN")), file), fail);
      assert.throws(() => historical(source + "\n" + marker, file), fail);
    }
  });
}
test("source projection rejects reordered action records and catalogue after freeze", () => {
  const [helper, filter, page, refresh, catalogue] = fixture.canonicalChanges;
  const swapped = physical[helper.file].replace(filter.new, "__TEMP_RECORD__").replace(page.new, () => filter.new).replace("__TEMP_RECORD__", () => page.new);
  assert.throws(() => historical(swapped, helper.file), fail);
  const afterFreeze = physical[catalogue.file].replace(catalogue.new, () => catalogue.old)
    .replace("  deepFreeze(MESSAGES);", () => "  deepFreeze(MESSAGES);\n" + catalogue.new.slice(0, -catalogue.old.length));
  assert.throws(() => historical(afterFreeze, catalogue.file), fail);
  const detachedHelper = physical[helper.file].replace(helper.new, () => helper.old)
    .replace(refresh.new, () => helper.new.slice(0, -helper.old.length) + refresh.new);
  assert.throws(() => historical(detachedHelper, helper.file), fail);
});
test("source projection preserves strict source/file argument types", () => {
  for (const value of [undefined, null, 1, {}, [], new String("source")]) {
    assert.throws(() => historical(value, files[0]), fail);
    assert.throws(() => historical("BASE", value), fail);
  }
});
