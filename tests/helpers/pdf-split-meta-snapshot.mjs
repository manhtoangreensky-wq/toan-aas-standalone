import fs from "node:fs";
import assert from "node:assert/strict";
import {resizePolishHistoricalPortalSource,resizePolishHistoricalI18nSource,resizePolishHistoricalPagesSource,resizePolishHistoricalSnapshot} from "./image-resize-polish-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-split-meta-reviewed.json",import.meta.url),"utf8"));
const prefix="docPdfMetaUi",failure="Unreviewed PDF Split metadata",locales=["vi","en","zh"];
const count=(value,part)=>value.split(part).length-1;
function once(value,old,next){assert.equal(count(value,old),1,failure+" changed/duplicate/missing chunk");return value.replace(old,()=>next);}
export function pdfSplitMetaHistoricalPortalSource(source){
  source=resizePolishHistoricalPortalSource(source);
  assert.equal(typeof source,"string",failure);if(!source.includes(prefix))return source;
  let restored=source;
  const edits=fixture.changes.filter(edit=>edit.file==="static/portal/portal.js");assert.equal(edits.length,2);
  for(const[index,edit]of edits.entries()){
    const signature=index===0?"  function localizedPageTitle(":"  function localizedPageDescription(";
    assert.equal(count(restored,signature),1,failure+" owner");
    const start=restored.indexOf(signature),end=restored.indexOf("\n  function ",start+signature.length);assert.ok(end>start,failure+" boundary");
    assert.equal(count(restored,edit.new),1,failure+" misplaced/duplicate branch");
    const part=once(restored.slice(start,end),edit.new,edit.old);
    restored=restored.slice(0,start)+part+restored.slice(end);
  }
  assert.equal(restored.includes(prefix),false,failure+" partial/unknown branch");
  return restored;
}
export function pdfSplitMetaHistoricalI18nSource(source){
  source=resizePolishHistoricalI18nSource(source);
  assert.equal(typeof source,"string",failure);if(!source.includes(prefix))return source;
  const edit=fixture.changes.find(edit=>edit.file==="static/portal/portal-i18n.js");
  const restored=once(source,edit.new,edit.old);
  assert.equal(restored.includes(prefix),false,failure+" partial/unknown catalogue");
  return restored;
}
export function pdfSplitMetaHistoricalPagesSource(source){
  source=resizePolishHistoricalPagesSource(source);
  assert.equal(typeof source,"string",failure);
  const edits=fixture.changes.filter(edit=>edit.file==="copyfast_pages.py");assert.equal(edits.length,2);
  const found=edits.map(edit=>count(source,edit.new));
  if(found.every(value=>value===0)){
    for(const edit of edits){
      const start=source.indexOf(edit.old),end=source.indexOf("\n}",start);
      assert.ok(start>=0&&end>start,failure+" shell dictionary owner");
      assert.equal(source.slice(start,end).includes('"/documents/split":'),false,failure+" partial/unknown shell entry");
    }
    return source;
  }
  assert.ok(found.every(value=>value===1),failure+" partial/duplicate shell entry");
  let restored=source;
  for(const edit of edits)restored=once(restored,edit.new,edit.old);
  return restored;
}
export function pdfSplitMetaHistoricalSnapshot(entries,locale){
  entries=resizePolishHistoricalSnapshot(entries,locale);
  assert.ok(locales.includes(locale),failure+" locale");
  const added=entries.filter(([key])=>key.startsWith(prefix));if(!added.length)return entries;
  const expected=fixture.rows.map(row=>[row[0],row[locales.indexOf(locale)+1]]);
  assert.deepEqual(added,expected,failure+" key/value/duplicate/order");
  const keys=new Set(expected.map(([key])=>key));
  return entries.filter(([key])=>!keys.has(key)); // Keep every unknown outside key/value and its order.
}
