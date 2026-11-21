import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
import {mediaFixedFeedbackHistoricalSource} from "./helpers/media-fixed-feedback-snapshot.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const raw = fs.readFileSync(new URL("./fixtures/media-detail-customer-copy-reviewed.json", import.meta.url));
const f = JSON.parse(raw), hash = value => createHash("sha256").update(value).digest("hex");
const lf = value => value.replace(/\r\n/g, "\n");
const original = Object.fromEntries(f.allowedFiles.map(file => [file,
  lf(execFileSync("git", ["show", f.base + ":" + file], {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true}))]));
const expected = {...original}, physical = Object.fromEntries(f.allowedFiles.map(file =>
  [file, mediaFixedFeedbackHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file)]));
for (const edit of f.canonicalChanges) {
  assert.equal(edit.count, 1); assert.equal(expected[edit.file].split(edit.old).length - 1, 1);
  expected[edit.file] = expected[edit.file].replace(edit.old, () => edit.new);
}
test("historical PR785 complete inputs equal BASE plus exactly53 independently reviewed records", () => {
  assert.equal(hash(raw), "a2209d2a371b0323480cadaa01d1726ac330c5fc6c3cc5473b13df8726fd79bd");
  assert.equal(f.base, "051b936695638a5f083396194730861dc7831da1");
  assert.equal(f.canonicalChanges.length, 53); assert.equal(f.copyRows.length, 47);
  assert.equal(f.copyRows.filter(row => row.old === null).length, 2);
  for (const file of f.allowedFiles) {
    assert.equal(physical[file], expected[file], "Historical PR785 input; current MFF acceptance is separate:" + file);
    assert.notEqual(physical[file], original[file]);
  }
});
test("historical PR785 inputs retain151 pins148 protected and the exact measured/LF/CRLF checkout", () => {
  assert.equal(f.applicationBaseline.length, 151);
  assert.equal(new Set(f.applicationBaseline.map(row => row.file)).size, 151);
  assert.equal(f.applicationBaseline.filter(row => !row.changed).length, 148);
  for (const pin of f.applicationBaseline) {
    const raw = fs.readFileSync(path.join(ROOT, pin.file));
    const projected = mediaFixedFeedbackHistoricalSource(lf(raw.toString("utf8")), pin.file);
    const bytes = Buffer.from(projected), text = projected;
    assert.equal(hash(text), pin.candidateLfSha256, "Complete current source:" + pin.file);
    assert.ok([pin.candidateRawSha256, pin.candidateLfSha256, hash(text.replace(/\n/g, "\r\n"))].includes(hash(bytes)),
      "Only measured/LF/uniformCRLF checkout:" + pin.file);
    if (!pin.changed) {
      assert.equal(pin.baseRawSha256, pin.candidateRawSha256);
      assert.equal(pin.baseLfSha256, pin.candidateLfSha256);
    }
  }
});
test("worker provenance fixes all five reviewed outputs without a code failure or application takeover", () => {
  assert.deepEqual(f.workers.map(row => row.records), [3, 43, 4, 2, 1]);
  assert.deepEqual(f.workers.map(row => row.proposalRawSha256), [
    "3fc0a55766e0146dffc9f53b283d02c998ae0110f48a4aab918cafa886d4f843",
    "1888cf4df57ca19327e5a1d1326f98fa47a10c004a5a7932d9facde0e1759d58",
    "df388b54d37b6803db39f586e80271ff770995e2e1ffe8d82e9f5810da1c2281",
    "27a147d438c4b1735730bd578e03146eb332d133a5638cfd30cb534aaf1c6bdc",
    "8d0024abe765b6d7d238c91145c9bf2e1330c6bc00bf3d022adef1b675a8c243"]);
  assert.ok(f.workers.every(row => row.proposalExact && row.workerCodeFailures === 0 && !row.applicationTakeover));
  assert.equal(f.workerCodeFailures, 0); assert.equal(f.applicationTakeover, false);
  assert.equal(f.providerCalls, 0); assert.equal(f.walletMutations, 0);
  assert.equal(f.productionDataMutations, 0); assert.equal(f.campaignStateOpened, false);
});
test("historical projection only restores exact reviewed bounded fragments and preserves outside customer bytes", async () => {
  const {mediaDetailCustomerCopyHistoricalSource: project} = await import("./helpers/media-detail-customer-copy-snapshot.mjs");
  const prefix = "/* CUSTOMER Facebook TikTok media studio <img>& */\n", suffix = '\n/* customer ends */';
  for (const file of f.allowedFiles) {
    assert.equal(project(physical[file], file), original[file]);
    assert.equal(project(original[file], file), original[file]);
    assert.equal(project(project(physical[file], file), file), original[file]);
    assert.equal(project(prefix + physical[file] + suffix, file), prefix + original[file] + suffix);
    assert.equal(project(physical[file], "customer/unrelated.txt"), physical[file]);
  }
});
for (const [index, fragment] of f.historicalFragments.entries()) {
  test(`historical bounded fragment${index + 1} rejects changed or duplicated current records`, async () => {
    const {mediaDetailCustomerCopyHistoricalSource: project} = await import("./helpers/media-detail-customer-copy-snapshot.mjs");
    const changed = fragment.new.replace(/audioWorkspace|media-item-attach|portal-ink/, "UNKNOWN_REVIEWED_FRAGMENT");
    assert.notEqual(changed, fragment.new);
    assert.throws(() => project(physical[fragment.file].replace(fragment.new, () => changed), fragment.file),
      /Unreviewed media detail customer copy/);
    assert.throws(() => project(physical[fragment.file] + "\n" + fragment.new, fragment.file),
      /Unreviewed media detail customer copy/);
  });
}
