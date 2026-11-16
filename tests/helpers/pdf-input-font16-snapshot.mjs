import fs from "node:fs";
import assert from "node:assert/strict";
import {pdfMergeContrastHistoricalCss} from "./pdf-merge-contrast-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-input-font16-reviewed.json",import.meta.url),"utf8"));
const old='/* Keep PDF compression field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-optimize .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-optimize .portal-field-help {\n  color: var(--portal-muted);\n}';
const rule='/* Keep PDF text controls readable on small screens. */\n@media (max-width: 767px) {\n  .portal-page.portal-pdf-split .portal-document-operation-form :is(input, select, textarea),\n  .portal-page.portal-pdf-merge .portal-document-operation-form :is(input, select, textarea),\n  .portal-page.portal-pdf-optimize .portal-document-operation-form :is(input, select, textarea) {\n    font-size: 16px;\n  }\n}';
const reviewed={file:"static/portal/portal-theme.css",old,new:old+"\n\n"+rule,count:1};
assert.deepEqual(fixture.changes,[reviewed],"Unreviewed PDF input font16 fixture");
const count=(source,part)=>source.split(part).length-1;
const hasFontMarker=source=>/Keep PDF text controls|\.portal-page\.portal-pdf-(?:split|merge|optimize)\s+\.portal-document-operation-form\s+:is\(/.test(source);
export function pdfInputFont16HistoricalCss(source){
  assert.equal(typeof source,"string","Unreviewed PDF input font16 CSS source");
  source=pdfMergeContrastHistoricalCss(source);
  if(!hasFontMarker(source))return source; // Older sources and every unknown outside byte stay untouched.
  assert.equal(count(source,reviewed.new),1,"Unreviewed PDF input font16 CSS partial/changed/duplicate/misplaced rule");
  assert.equal(count(source,reviewed.old),1,"Unreviewed PDF input font16 CSS duplicate anchor");
  const result=source.replace(reviewed.new,()=>reviewed.old);
  assert.equal(hasFontMarker(result),false,"Unreviewed PDF input font16 CSS residual/duplicate marker");
  return result; // No newline conversion, broad prefix filtering or CSS normalization.
}
