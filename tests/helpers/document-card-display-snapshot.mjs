import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {documentCardMetricsHistoricalSnapshot,documentCardMetricsHistoricalPortalSource,documentCardMetricsHistoricalI18nSource} from "./document-card-metrics-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/document-card-display-reviewed.json",import.meta.url),"utf8"));
const keys=new Set(Object.keys(fixture.vi)),hash=v=>createHash("sha256").update(v).digest("hex");
assert.equal(keys.size,19);
export function documentCardDisplayHistoricalSnapshot(entries,locale){
  entries=documentCardMetricsHistoricalSnapshot(entries,locale);
  const scoped=entries.filter(([key])=>/^(?:docCardNameUi|docSelectedUi)/.test(key));
  if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,"Unreviewed document display: unknown key");
  assert.equal(added.length,19,"Unreviewed document display: missing key");
  assert.equal(hash(JSON.stringify(added)),fixture.binding.catalogHashes[locale],"Unreviewed document display: value/order");
  return entries.filter(([key])=>!keys.has(key));
}
const catalogEdits=fixture.changes.filter(edit=>edit.file.endsWith("portal-i18n.js"));
export function documentCardDisplayHistoricalI18nSource(value){
  let source=documentCardMetricsHistoricalI18nSource(value);
  if(!/(?:docCardNameUi|docSelectedUi)/.test(source))return source;
  for(const edit of [...catalogEdits].reverse()){
    assert.equal(source.split(edit.new).length-1,1,"Unreviewed document display i18n");
    source=source.replace(edit.new,()=>edit.old);
  }
  return source;
}
export function documentCardDisplayHistoricalPortalSource(value){
  const source=documentCardMetricsHistoricalPortalSource(value);
  if(!/docCardNameUi|docSelectedUi|safeText\(chatWorkspaceDateLabel\(item\.completed_at/.test(source))return source;
  const start="  function renderDocumentOperationCards(",end="\n  function renderMediaHubPage(";
  assert.equal(source.split(start).length-1,1,"Unreviewed document display boundary");
  const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a);
  assert.equal(source.slice(a,b),fixture.binding.newCard,"Unreviewed document display card");
  return source.slice(0,a)+fixture.binding.oldCard+source.slice(b);
}
