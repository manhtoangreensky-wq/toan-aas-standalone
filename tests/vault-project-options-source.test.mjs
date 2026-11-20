import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {vaultProjectOptionsHistoricalSource as inverse} from "./helpers/vault-project-options-snapshot.mjs";
import {mediaCollectionHistoricalSource} from "./helpers/media-collection-locale-snapshot.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const raw = fs.readFileSync(new URL("./fixtures/vault-project-options-reviewed.json", import.meta.url));
const fixture = JSON.parse(raw), edit = fixture.canonicalChanges[0], file = edit.file;
const hash = value => createHash("sha256").update(value).digest("hex");
const lf = value => value.replace(/\r\n/g, "\n");
const base = lf(execFileSync("git", ["show", fixture.base + ":" + file], {cwd: ROOT, encoding: "utf8", maxBuffer: 12e6}));
const physical = lf(fs.readFileSync(path.join(ROOT, file), "utf8"));
const candidate = base.replace(edit.old, () => edit.new), fail = /Unreviewed Vault project options/;

test("one immutable worker proposal maps complete Git BASE to current physical integration", () => {
  assert.equal(hash(raw), "9faedb1fe8c1aff3d456a658f82dd107a4d4fab7690c51eb071b1d93dc53edee");
  assert.equal(fixture.task, "VAULT-PROJECT-OPTIONS-20261120");
  assert.equal(fixture.canonicalChanges.length, 1);
  assert.equal(fixture.worker.proposalRawSha256, "7dcd963350d0db1ffcedba2920dac17275938947fcfaaacfd4abf272bd91e172");
  assert.equal(fixture.worker.proposalDecodedExact, true);
  assert.equal(fixture.worker.workerCodeFailures, 0); assert.equal(fixture.worker.applicationTakeover, false);
  assert.equal(base.split(edit.old).length - 1, 1);
  assert.equal(physical, candidate); assert.equal(inverse(physical, file), base);
  assert.notEqual(physical, base);
});

test("all151 current physical sources equal immutable candidate pins with150 protected BASE files", () => {
  assert.equal(fixture.applicationBaseline.length, 151);
  assert.equal(new Set(fixture.applicationBaseline.map(row => row.file)).size, 151);
  assert.deepEqual(fixture.applicationBaseline.filter(row => row.changed).map(row => row.file), [file]);
  for (const pin of fixture.applicationBaseline) {
    const actual = mediaCollectionHistoricalSource(lf(fs.readFileSync(path.join(ROOT, pin.file), "utf8")), pin.file);
    assert.equal(hash(actual), pin.candidateLfSha256, pin.file);
    assert.equal(hash(inverse(actual, pin.file)), pin.baseLfSha256, pin.file);
    if (!pin.changed) assert.equal(pin.baseLfSha256, pin.candidateLfSha256, pin.file);
  }
});

test("finite historical projection is idempotent and preserves all outside customer bytes", () => {
  const prefix = '/* Customer media studio Facebook TikTok <img>& */\n', suffix = '\nconst customer="unchanged";';
  assert.equal(inverse(base, file), base);
  assert.equal(inverse(inverse(physical, file), file), base);
  assert.equal(inverse(prefix + physical + suffix, file), prefix + base + suffix);
  assert.equal(inverse(physical, "customer/unrelated.txt"), physical);
  assert.equal(inverse(prefix + suffix, file), prefix + suffix);
});

for (const [name, mutate] of [
  ["changed", value => value.replace(edit.new, edit.new.replace("assetVaultEnabled &&", "true &&"))],
  ["duplicate", value => value + "\n" + edit.new],
  ["detached", value => value.replace(edit.new, "") + "\n" + edit.new],
  ["wrong route", value => value.replace(edit.new, edit.new.replace('"/asset-vault"', '"/asset-vault/unknown"'))],
  ["wrong owner", value => value.replace("  async function hydrate() {", "  async function UNKNOWN_HYDRATE() {")],
  ["missing owner boundary", value => value.replace("  async function hydrateCampaignCalendar(", "  async function UNKNOWN_NEXT(")]
]) test("historical projection rejects " + name + " proposal fragment", () => {
  assert.throws(() => inverse(mutate(physical), file), fail);
});

test("historical projection retains strict input types", () => {
  for (const value of [undefined, null, 1, {}, []]) assert.throws(() => inverse(value, file), fail);
});
