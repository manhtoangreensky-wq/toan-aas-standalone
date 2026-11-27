// Exact finite Gallery readability inverse for historical QA, never runtime code.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {FAMILY_READABILITY_ADDITION} from "./feature-family-readability-historical.mjs";

const fail = "Unreviewed Gallery readability";
const raw = fs.readFileSync(new URL("../fixtures/gallery-readability.json", import.meta.url), "utf8").replace(/\r\n/g, "\n");
assert.equal(createHash("sha256").update(raw).digest("hex"), "3cfbd7b2618e05a11d91179d0b12d6be37d911e2d85ad495738defb0e00ab68f", fail);
const fixture = JSON.parse(raw);
assert.equal(fixture.base_sha, "bf95e4017717622d694cbef02fde07799a823a8a", fail);
assert.equal(fixture.cssRules.length, 11, fail);
const cssFile = "static/portal/portal-theme.css";
const addition = "\n" + fixture.cssMarker + "\n" + fixture.cssRules.join("\n") + "\n";
const selectors = fixture.cssRules.map(rule => rule.slice(0, rule.indexOf(" {")));
const record = fixture.portalRecord;
assert.equal(record.file, "static/portal/portal.js", fail);
assert.equal(record.owner, "renderFreePromptGallery", fail);
assert.equal(record.new, "${canBrowse ? `" + record.old + '` : ""}', fail);
const count = (source, part) => source.split(part).length - 1;
const conditionalOwners = ['${canBrowse ? `', "`" + record.old, record.old + "`"];

export function galleryReadabilityHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  if (file === cssFile) {
    if (!source.includes(fixture.cssMarker) && !selectors.some(selector => source.includes(selector))) return source;
    assert.equal(count(source, fixture.cssMarker), 1, fail + " marker");
    for (let index = 0; index < selectors.length; index++) {
      assert.equal(count(source, selectors[index]), 1, fail + " selector owner");
      assert.equal(count(source, fixture.cssRules[index]), 1, fail + " exact rule");
    }
    assert.equal(count(source, FAMILY_READABILITY_ADDITION), 1, fail + " prior FCR anchor");
    assert.equal(count(source, addition), 1, fail + " exact eleven-rule addition");
    assert.equal(count(source, FAMILY_READABILITY_ADDITION + addition), 1, fail + " placement/order");
    return source.replace(addition, () => "");
  }
  if (file !== record.file) return source;
  if (!source.includes(record.new)) {
    assert(!conditionalOwners.some(part => source.includes(part)), fail + " changed conditional");
    return source;
  }
  const owner = "  function " + record.owner + "(";
  const start = source.indexOf(owner);
  const end = source.indexOf("\n  }\n", start);
  const at = source.indexOf(record.new);
  assert(start >= 0 && end > start && count(source, owner) === 1, fail + " function owner");
  assert.equal(count(source, record.new), 1, fail + " exact conditional");
  assert.equal(count(source, record.old), 1, fail + " unique metrics structure");
  assert(at >= start + owner.length && at + record.new.length <= end, fail + " conditional placement");
  const intro = source.indexOf('<section class="portal-content-prompt-pack-intro">', start);
  const introEnd = source.indexOf("</section>", intro);
  assert(intro >= start && introEnd < end && at > intro &&
    at + record.new.length === introEnd && source.slice(at - 10, at) === "</p></div>",
  fail + " intro metrics slot");
  for (const part of conditionalOwners) assert.equal(count(source, part), 1, fail + " conditional owner");
  return source.replace(record.new, () => record.old);
}
