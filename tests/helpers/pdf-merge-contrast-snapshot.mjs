import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-merge-contrast-reviewed.json",import.meta.url),"utf8"));
const addition='\n\n/* Keep PDF merge field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-merge .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-merge .portal-field-help {\n  color: var(--portal-muted);\n}';
assert.equal(fixture.changes.length,1,"Unreviewed Merge contrast fixture");
const edit=fixture.changes[0],count=(value,part)=>value.split(part).length-1;
assert.equal(edit.file,"static/portal/portal-theme.css");assert.equal(edit.count,1);assert.equal(edit.new,edit.old+addition);
const marker=source=>/Keep PDF merge field names and guidance|html:not\(\[data-portal-theme="dark"\]\) \.portal-page\.portal-pdf-merge \.portal-field(?: > label|-help) \{/.test(source);
export function pdfMergeContrastHistoricalCss(source){
  assert.equal(typeof source,"string","Unreviewed Merge contrast CSS");
  if(!marker(source))return source;
  assert.equal(count(source,edit.new),1,"Unreviewed Merge contrast CSS missing/changed/duplicate/misplaced group");
  assert.equal(count(source,edit.old),1,"Unreviewed Merge contrast CSS duplicate old anchor");
  const result=source.replace(edit.new,()=>edit.old);
  assert.equal(marker(result),false,"Unreviewed Merge contrast CSS residual/unknown rule");
  return result;
}
