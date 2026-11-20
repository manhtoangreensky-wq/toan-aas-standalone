import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {mediaCollectionHistoricalSource} from "./media-collection-locale-snapshot.mjs";

const raw = fs.readFileSync(new URL("../fixtures/vault-project-options-reviewed.json", import.meta.url));
const fail = "Unreviewed Vault project options";
const hash = value => createHash("sha256").update(value).digest("hex");
const count = (source, part) => source.split(part).length - 1;
assert.equal(hash(raw), "9faedb1fe8c1aff3d456a658f82dd107a4d4fab7690c51eb071b1d93dc53edee", fail);
const fixture = JSON.parse(raw), edit = fixture.canonicalChanges[0];
assert.equal(fixture.task, "VAULT-PROJECT-OPTIONS-20261120", fail);
assert.equal(fixture.base, "4cf8590826846a3f3336a4d7359d53df965c226f", fail);
assert.equal(fixture.canonicalChanges.length, 1, fail);
assert.equal(edit.file, "static/portal/integration.js", fail);
assert.equal(edit.count, 1, fail);
assert.equal(edit.old, "|| isNativeDocumentWorkspacePath(currentPath))) await hydrateProjects();", fail);
assert.equal(edit.new, '|| isNativeDocumentWorkspacePath(currentPath) || (assetVaultEnabled && currentPath === "/asset-vault"))) await hydrateProjects();', fail);
const owner = "  async function hydrate() {", next = "  async function hydrateCampaignCalendar(";

// Historical input projection only. Current acceptance independently reads
// complete physical sources and all151 pins in vault-project-options-source.
export function vaultProjectOptionsHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  source = mediaCollectionHistoricalSource(source, file);
  if (file !== edit.file) return source;
  if (!source.includes(owner) && !source.includes(edit.old) && !source.includes(edit.new)) return source;
  assert.equal(count(source, owner), 1, fail + " owner");
  assert.equal(count(source, next), 1, fail + " next owner");
  const start = source.indexOf(owner), end = source.indexOf(next, start);
  assert.ok(end > start, fail + " owner order");
  if (!source.includes(edit.new)) {
    assert.equal(count(source, edit.old), 1, fail + " old fragment");
    const point = source.indexOf(edit.old);
    assert.ok(point >= start && point + edit.old.length < end, fail + " old placement");
    return source;
  }
  assert.equal(count(source, edit.new), 1, fail + " new fragment");
  const point = source.indexOf(edit.new);
  assert.ok(point >= start && point + edit.new.length < end, fail + " new placement");
  return source.replace(edit.new, () => edit.old);
}
