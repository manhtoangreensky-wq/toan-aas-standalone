// Finite GSC input inverse for historical QA only; never imported by the app.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {documentNaturalHistoricalSource,documentNaturalHistoricalSnapshot} from './document-natural-copy-historical.mjs';
import {galleryNativeRuntimeHistoricalSource} from './gallery-native-runtime-historical.mjs';
import {adminGuardCustomerCopyHistoricalSource,adminGuardCustomerCopyHistoricalSnapshot} from './admin-guard-customer-copy-historical.mjs';

const failure='Unreviewed Gallery native history';
const sha=value=>createHash('sha256').update(value).digest('hex');
const raw=fs.readFileSync(new URL('../fixtures/gallery-native-history.json',import.meta.url),'utf8').replace(/\r\n/g,'\n');
assert.equal(sha(raw),'4b035b41da5204033d8fd6af9a77d64c74523bba33d71ddbd4427f9a9e236435',failure+' fixture');
const fixture=JSON.parse(raw),portal='static/portal/portal.js',i18n='static/portal/portal-i18n.js';
const locales=['vi','en','zh'],files=new Set([portal,i18n]);
assert.equal(fixture.base_sha,'29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef',failure+' base');
assert.equal(fixture.records.length,5,failure+' records');
for(const row of fixture.records){
  assert(files.has(row.file)&&typeof row.before==='string'&&typeof row.after==='string',failure+' record');
  assert.equal(sha(row.after),row.after_lf_sha256,failure+' record hash');
}
const snapshots=new Map(locales.map(locale=>[locale,new Map(fixture.snapshots[locale])]));
const keys=fixture.snapshots.vi.map(([key])=>key),keySet=new Set(keys);
assert.equal(keys.length,40,failure+' forty keys');assert.equal(keySet.size,40,failure+' unique keys');
for(const locale of locales){
  assert.deepEqual(fixture.snapshots[locale].map(([key])=>key),keys,failure+' locale order');
  assert(fixture.snapshots[locale].every(row=>row.length===2&&typeof row[1]==='string'),failure+' locale values');
}
const count=(source,part)=>source.split(part).length-1;
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const declarations=new RegExp('"('+keys.map(escape).join('|')+')"\\s*:','g');
const exactOnce=(source,part,label)=>{
  assert.equal(count(source,part),1,failure+' '+label);return source.indexOf(part);
};
function functionSlot(source,row,previous,next){
  const start=exactOnce(source,row.after,row.owner);
  const previousStart=exactOnce(source,'  function '+previous+'(',previous+' owner');
  const previousEnd=source.indexOf('\n  }\n',previousStart);
  const nextStart=exactOnce(source,next,'next owner');
  assert(previousEnd>previousStart&&start>=previousEnd+5&&start+row.after.length<=nextStart,failure+' function slot');
}

export function galleryNativeHistoricalSource(source,file){
  assert.equal(typeof source,'string',failure+' source');
  source=documentNaturalHistoricalSource(source,file);
  source=adminGuardCustomerCopyHistoricalSource(source,file);
  source=galleryNativeRuntimeHistoricalSource(source,file);
  if(!files.has(file))return source;
  const rows=fixture.records.filter(row=>row.file===file);
  if(file===portal){
    const signal=/freePromptGalleryTaxonomyLabel\s*\(|freePromptGalleryText\("feedback\.loading"|context\.freePromptGalleryReadState\s*===\s*"loading"/;
    if(!signal.test(source))return source;
    let prior=-1;
    for(const row of rows){
      const start=exactOnce(source,row.after,row.owner);
      assert(start>prior,failure+' source order');prior=start;
    }
    for(const owner of ['freePromptGalleryTaxonomyLabel','freePromptGalleryFilterFields','freePromptGalleryTags','renderFreePromptGallery']){
      exactOnce(source,'  function '+owner+'(',owner+' owner');
    }
    functionSlot(source,rows[0],'freePromptGalleryListingState','  function freePromptGalleryTags(');
    functionSlot(source,rows[1],'freePromptGalleryFilterFields','  function renderFreePromptGalleryCards(');
    functionSlot(source,rows[2],'renderFreePromptGallerySaveResult','  const VIETQR_BANKS = [');
  }else{
    const found=[...source.matchAll(declarations)];
    if(!found.length)return source;
    for(const key of keys)assert.equal(found.filter(match=>match[1]===key).length,3,failure+' declaration ownership');
    // Both proposals insert at the same verify call: taxonomy first, feedback second.
    const combined=rows[0].after.replace(rows[1].before,()=>rows[1].after);
    const start=exactOnce(source,combined,'complete ordered i18n blocks');
    exactOnce(source,'  verifyEqualKeysets();','verification anchor');
    const previous='  MESSAGES.zh["portal.form.requiredWarning"] = "请先填写必填项，然后继续。";';
    const previousStart=exactOnce(source,previous,'prior i18n slot');
    const nextStart=exactOnce(source,'  function deepFreeze(value) {','following i18n slot');
    assert(start>=previousStart+previous.length&&start+combined.length<=nextStart,failure+' i18n slot');
  }
  for(const row of [...rows].reverse()){
    exactOnce(source,row.after,'reverse exact record');
    source=source.replace(row.after,()=>row.before);
  }
  return source;
}

export function galleryNativeHistoricalSnapshot(entries,locale){
  assert(Array.isArray(entries)&&locales.includes(locale),failure+' snapshot input/locale');
  entries=documentNaturalHistoricalSnapshot(entries,locale);
  entries=adminGuardCustomerCopyHistoricalSnapshot(entries,locale);
  const owned=entries.filter(row=>row!=null&&keySet.has(row[0]));
  if(!owned.length)return entries;
  assert(entries.every(row=>Array.isArray(row)&&row.length===2),failure+' snapshot pair shape');
  assert.equal(owned.length,40,failure+' snapshot complete');
  assert.equal(new Set(owned.map(([key])=>key)).size,40,failure+' snapshot unique');
  assert.deepEqual(owned.map(([key])=>key),keys,failure+' snapshot insertion order');
  const approved=snapshots.get(locale);
  for(const[key,value]of owned)assert.equal(value,approved.get(key),failure+' snapshot exact locale value');
  return entries.filter(([key])=>!keySet.has(key));
}
