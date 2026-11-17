import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/image-resize-control-height-reviewed.json",import.meta.url),"utf8"));
const [edit]=fixture.changes,fail="Unreviewed Resize control height";
const marker="/* Keep Resize controls at their natural height beside the source picker. */";
const selector='.portal-page.portal-image-resize form[data-portal-action="image-operation-resize"] > .portal-fields > .portal-field';
const count=(value,part)=>value.split(part).length-1;
const addition=edit.new.slice(edit.old.length);
assert.equal(fixture.changes.length,1);assert.equal(edit.file,"static/portal/portal-theme.css");assert.equal(edit.count,1);
assert.equal(edit.new,edit.old+"\n\n"+marker+"\n"+selector+" {\n  align-content: start;\n}");
export function resizeControlHeightHistoricalThemeSource(source){
  assert.equal(typeof source,"string",fail);
  if(!source.includes(marker)){assert.equal(count(source,selector),0,fail+" partial/unknown rule");return source;}
  assert.equal(count(source,marker),1,fail+" duplicate marker");
  assert.equal(count(source,selector),1,fail+" duplicate selector");
  assert.equal(count(source,addition),1,fail+" changed/partial addition");
  const owners=[...source.matchAll(/html:not\(\[data-portal-theme="dark"\]\) \.portal-page\.portal-image-resize \.portal-field-help \{[^}]*\}/g)];
  const point=source.indexOf(addition);
  assert.equal(owners.filter(owner=>owner.index+owner[0].length===point).length,1,fail+" moved addition");
  return source.replace(addition,"");
}
