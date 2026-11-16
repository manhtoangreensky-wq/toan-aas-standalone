import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {pdfUsabilityHistoricalSnapshot,pdfUsabilityHistoricalPortalSource,pdfUsabilityHistoricalI18nSource} from "./pdf-usability-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/document-card-metrics-reviewed.json",import.meta.url),"utf8"));
const keys=new Set(Object.keys(fixture.vi)),hash=value=>createHash("sha256").update(value).digest("hex");
assert.equal(keys.size,13);
export function documentCardMetricsHistoricalSnapshot(entries,locale){
  entries=pdfUsabilityHistoricalSnapshot(entries,locale);
  const scoped=entries.filter(([key])=>key.startsWith("docMetricUi"));
  if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,"Unreviewed document metrics: unknown key");
  assert.equal(added.length,13,"Unreviewed document metrics: missing key");
  assert.equal(hash(JSON.stringify(added)),fixture.binding.catalogHashes[locale],"Unreviewed document metrics: value/order");
  return entries.filter(([key])=>!keys.has(key));
}
function inverse(value,file){
  let source=value.replace(/\r\n/g,"\n");
  source=file==="static/portal/portal.js"?pdfUsabilityHistoricalPortalSource(source):pdfUsabilityHistoricalI18nSource(source);
  if(!source.includes("docMetricUi"))return source;
  for(const edit of fixture.changes.filter(item=>item.file===file).reverse()){
    assert.equal(source.split(edit.new).length-1,1,"Unreviewed document metrics "+file);
    source=source.replace(edit.new,()=>edit.old);
  }
  assert.equal(source.includes("docMetricUi"),false,"Unreviewed document metrics residual key");
  return source;
}
export const documentCardMetricsHistoricalPortalSource=value=>inverse(value,"static/portal/portal.js");
export const documentCardMetricsHistoricalI18nSource=value=>inverse(value,"static/portal/portal-i18n.js");
