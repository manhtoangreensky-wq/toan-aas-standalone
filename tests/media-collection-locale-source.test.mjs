import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {mediaCollectionHistoricalSource as inverse} from "./helpers/media-collection-locale-snapshot.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const raw = fs.readFileSync(new URL("./fixtures/media-collection-locale-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), hash = value => createHash("sha256").update(value).digest("hex");
const lf = value => value.replace(/\r\n/g, "\n"), fail = /Unreviewed media collection locale/;
const files = ["static/portal/portal.js", "static/portal/portal-i18n.js"];
const bases = Object.fromEntries(files.map(file => [file, lf(execFileSync("git",
  ["show", fixture.base + ":" + file], {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6}))]));
const physical = Object.fromEntries(files.map(file => [file, lf(fs.readFileSync(path.join(ROOT, file), "utf8"))]));
const candidates = {...bases};
for (const edit of fixture.canonicalChanges) {
  assert.equal(edit.count, 1); assert.equal(candidates[edit.file].split(edit.old).length - 1, 1);
  candidates[edit.file] = candidates[edit.file].replace(edit.old, () => edit.new);
}

test("four immutable worker proposals are exactly eight records on two complete physical application files", () => {
  assert.equal(hash(raw), "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515");
  assert.equal(fixture.task, "MEDIA-COLLECTION-LOCALE-20261120");
  assert.equal(fixture.canonicalChanges.length, 8); assert.equal(fixture.workers.length, 4);
  assert.deepEqual(fixture.workers.map(row => row.records), [4, 1, 2, 1]);
  assert.deepEqual(fixture.workers.map(row => row.proposalRawSha256), [
    "0a7c9944814a85497ce9dfd45bf1be3b20c9270cb579fada7a9b7b22c63e79d1",
    "b5b1b1b07166cc04bc64bf50b78d965e33d52f85d52f495cccb27d5ccaa0a426",
    "bd1af315e0e6b270863af3a2027cad11854dc952b623a40b037b89dfb716ab03",
    "2e2fff85a5f747ee144260f9e86b5c32adff08ea82267844e008ce0bc2b68a42"]);
  for (const worker of fixture.workers) {
    assert.equal(worker.proposalDecodedExact, true); assert.equal(worker.workerCodeFailures, 0);
    assert.equal(worker.applicationTakeover, false);
  }
  for (const file of files) {
    assert.equal(physical[file], candidates[file], file);
    assert.equal(inverse(physical[file], file), bases[file], file);
    assert.notEqual(physical[file], bases[file], file);
  }
});

test("all151 current physical application sources are pinned with149 protected BASE files", () => {
  assert.equal(fixture.applicationBaseline.length, 151);
  assert.equal(new Set(fixture.applicationBaseline.map(row => row.file)).size, 151);
  assert.deepEqual(fixture.applicationBaseline.filter(row => row.changed).map(row => row.file).sort(), files.toSorted());
  for (const pin of fixture.applicationBaseline) {
    const actual = lf(fs.readFileSync(path.join(ROOT, pin.file), "utf8"));
    assert.equal(hash(actual), pin.candidateLfSha256, pin.file);
    assert.equal(hash(inverse(actual, pin.file)), pin.baseLfSha256, pin.file);
    if (!pin.changed) assert.equal(pin.baseLfSha256, pin.candidateLfSha256, pin.file);
  }
});

test("finite historical projection is idempotent, preserves outside customer bytes and unrelated files", () => {
  const prefix = "/* customer media studio Facebook TikTok <img>& */\n", suffix = '\nconst customer="unchanged";';
  for (const file of files) {
    assert.equal(inverse(bases[file], file), bases[file]);
    assert.equal(inverse(inverse(physical[file], file), file), bases[file]);
    assert.equal(inverse(prefix + physical[file] + suffix, file), prefix + bases[file] + suffix);
    assert.equal(inverse(physical[file], "customer/unrelated.txt"), physical[file]);
    assert.equal(inverse(prefix + suffix, file), prefix + suffix);
  }
});

for (const [index, group] of fixture.historicalFragments.entries()) {
  for (const [kind, mutate] of [
    ["changed", source => source.replace(group.new, () => group.new.replace("audioWorkspace", "UNKNOWN_WORKSPACE"))],
    ["duplicate", source => source + "\n" + group.new],
    ["detached", source => source.replace(group.new, "") + "\n" + group.new],
    ["wrong owner", source => source.replace(group.owner, group.owner.replace("function ", "function UNKNOWN_"))],
    ["missing next boundary", source => source.replace(group.next, group.next.replace("function ", "function UNKNOWN_"))]
  ]) test(`historical fragment${index + 1} rejects ${kind}`, () => {
    assert.throws(() => inverse(mutate(physical[group.file]), group.file), fail);
  });
}
test("finite historical projection retains strict input types", () => {
  for (const value of [undefined, null, 1, {}, []]) assert.throws(() => inverse(value, files[0]), fail);
});
