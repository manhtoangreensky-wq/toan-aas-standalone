import assert from "node:assert/strict";
export const PDF_SPLIT_READABILITY_ADDITION='\n/* Keep PDF split field names and guidance readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-split .portal-field > label {\n  color: var(--portal-text);\n}\nhtml:not([data-portal-theme="dark"]) .portal-page.portal-pdf-split .portal-field-help {\n  color: var(--portal-muted);\n}\n';
export function pdfSplitReadabilityHistoricalCss(value){
  const source=value.replace(/\r\n/g,"\n"),count=source.split(PDF_SPLIT_READABILITY_ADDITION).length-1;
  if(!count)return source;
  assert.equal(count,1,"Unreviewed PDF split readability CSS");
  assert.ok(source.endsWith(PDF_SPLIT_READABILITY_ADDITION),"Unreviewed PDF split readability CSS location");
  return source.slice(0,-PDF_SPLIT_READABILITY_ADDITION.length);
}
