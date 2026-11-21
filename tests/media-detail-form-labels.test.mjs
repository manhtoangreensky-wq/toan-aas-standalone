import assert from "node:assert/strict";
import test from "node:test";
import {sources, runtime, collection, context, hash} from "./helpers/media-collection-locale-runtime.mjs";

const physical = sources();
const expectedNames = ["asset_id", "role", "title_override", "attribution", "license_note",
  "tags", "user_declared_duration_seconds"];
for (const locale of ["vi", "en", "zh"]) for (const root of ["/media-workspace", "/audio-hub"]) {
  test(`${locale} ${root}: attach labels and help refer only to their own uniquely named controls`, () => {
    const r = runtime(physical, locale), row = collection(), route = root + "/" + row.id;
    const html = r.call("renderMediaWorkspaceDetail", r.page(route), context({row, overrides: {path: route}}));
    const forms = [...html.matchAll(/<form\b([^>]*)>([\s\S]*?)<\/form>/g)];
    const form = forms.filter(([, attrs]) => attrs.includes('data-portal-action="media-item-attach"'));
    assert.equal(form.length, 1, "The actual attach form must exist exactly once");
    const markup = form[0][2], observedNames = [...markup.matchAll(/<(?:input|select)\b[^>]*\bname="([^"]+)"/g)]
      .map(match => match[1]);
    assert.deepEqual(observedNames, expectedNames, "No field is removed or renamed to hide a duplicate");
    for (const name of expectedNames) {
      const id = "portal-field-media-item-attach-" + name;
      assert.ok(markup.includes(`id="${id}" name="${name}"`), "Give only the attach form its existing factory namespace");
      assert.ok(markup.includes(`for="${id}"`), "The visible label must name its own actual control");
      assert.equal([...html.matchAll(/\bid="([^"]+)"/g)].filter(match => match[1] === id).length, 1,
        "The control ID is unique in the complete detail page");
    }
    for (const [, references] of markup.matchAll(/\baria-describedby="([^"]+)"/g))
      for (const id of references.split(/\s+/)) {
        assert.ok(id.startsWith("portal-field-media-item-attach-"));
        assert.equal([...markup.matchAll(/\bid="([^"]+)"/g)].filter(match => match[1] === id).length, 1);
      }
    assert.equal([...html.matchAll(/\bid="portal-field-tags"/g)].length, 1, "The collection's existing tags ID stays unchanged");
    assert.equal(r.binding.exposureCount, 1); assert.equal(r.binding.replacedProductionFunctions, 0);
    assert.equal(r.binding.hashes.portal, hash(physical.raw.portal)); assert.deepEqual(r.attempts(), []);
  });
}
