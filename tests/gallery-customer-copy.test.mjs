import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {galleryNativeHistoricalSource,galleryNativeHistoricalSnapshot} from "./helpers/gallery-native-historical.mjs";
import {galleryFiles,physicalGallerySources,galleryRendererFromSources,galleryContext,galleryAssertNormalized,
  galleryKnownDescription,galleryKnownInstruction,galleryCustomer,galleryEscape as esc} from "./helpers/gallery-customer-copy-render.mjs";
const base="bf95e4017717622d694cbef02fde07799a823a8a",physical=physicalGallerySources();
const before=Object.fromEntries(galleryFiles.map(file=>[file,execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n")]));
const current=await galleryRendererFromSources(physical),baseline=await galleryRendererFromSources(before);
const fixtureRaw=fs.readFileSync(new URL("./fixtures/gallery-customer-copy.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(fixtureRaw).digest("hex"),"c376690961cee3c23c17d0c4479f311b93e16bfcc8fda9d6abf6d6f07264e1ef");
const fixture=JSON.parse(fixtureRaw);
const amendmentRaw=fs.readFileSync(new URL("./fixtures/gallery-readability.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(amendmentRaw).digest("hex"),"3cfbd7b2618e05a11d91179d0b12d6be37d911e2d85ad495738defb0e00ab68f");
const amendment=JSON.parse(amendmentRaw);
const locales=["vi","en","zh"],states=["guarded","empty","list","detail","saved"];
const controls=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(row=>row[0].replace(/ data-portal-confirm="[^"]*"/g,""));
const technical=/\b(?:CSRF|Core Bridge|PayOS|runtime|endpoint|snapshot|signed|request|canonical)\b/i;
const rows=new Map();
for(const locale of locales)for(const state of states){
  const raw=galleryContext(state),snapshot=JSON.stringify(raw),row=current(locale,"/free-prompt-gallery",raw),old=baseline(locale,"/free-prompt-gallery",raw);
  assert.equal(JSON.stringify(raw),snapshot);galleryAssertNormalized(row,state);galleryAssertNormalized(old,state);
  rows.set(locale+":"+state,{row,old,raw});
  test(`Gallery ${locale}/${state} uses customer-facing fixed chrome and no technical explanation tiles`,()=>{
    assert.doesNotMatch(row.text,technical);
    if(locale!=="en")assert.doesNotMatch(row.title,/\b(?:Prompt|Gallery|Web)\b/i);
    assert.doesNotMatch(row.html,/portal-content-prompt-pack-guard-list/);
    for(const card of row.html.matchAll(/<article class="portal-card portal-card-pad portal-prompt-library-card">([\s\S]*?)<\/article>/g)){
      assert.doesNotMatch(card[1],/class="portal-form-note"/,"No repeated per-card explanation remains");
    }
    assert.equal(row.pageDescription,row.messages[locale]["freePromptGallery.intro.body"]);
    if(!["detail","saved"].includes(state))assert.equal((row.html.match(/class="portal-card portal-card-pad portal-content-prompt-pack-result"/g)||[]).length,0);
  });
  test(`Gallery ${locale}/${state} preserves every actionable control, normalized data and customer content`,()=>{
    assert.deepEqual(controls(row.html),controls(old.html));
    assert.deepEqual(JSON.parse(JSON.stringify(row.context.freePromptGalleryCatalog)),JSON.parse(JSON.stringify(old.context.freePromptGalleryCatalog)));
    assert.deepEqual(JSON.parse(JSON.stringify(row.context.freePromptGalleryListing)),JSON.parse(JSON.stringify(old.context.freePromptGalleryListing)));
    assert.deepEqual(JSON.parse(JSON.stringify(row.context.freePromptGalleryDetail)),JSON.parse(JSON.stringify(old.context.freePromptGalleryDetail)));
    assert.deepEqual(JSON.parse(JSON.stringify(row.context.freePromptGallerySaveResult)),JSON.parse(JSON.stringify(old.context.freePromptGallerySaveResult)));
    if(["list","detail","saved"].includes(state))assert(row.html.includes(esc(galleryCustomer.title)));
    if(["detail","saved"].includes(state))assert(row.html.includes(esc(galleryCustomer.prompt)));
    assert(!row.html.includes("<script>not executable</script>"));
  });
}
for(const locale of locales){
  const{row}=rows.get(locale+":detail");
  test(`Gallery ${locale} replaces only the two known Web static explanation strings`,()=>{
    assert.equal(row.sourceText(galleryKnownDescription),row.messages[locale]["freePromptGallery.intro.body"]);
    assert.equal(row.sourceText(galleryKnownInstruction),row.messages[locale]["freePromptGallery.detail.body"]);
    for(const value of["CUSTOMER_COPY_INSTRUCTION <safe>","CUSTOMER_DESCRIPTION <safe>",galleryKnownDescription+" ",galleryKnownInstruction+"!",'__proto__']){
      assert.equal(row.sourceText(value),value);
    }
    const custom=current(locale,"/free-prompt-gallery",galleryContext("detail",{known:false}));
    galleryAssertNormalized(custom,"detail");
    assert(custom.html.includes(esc("CUSTOMER_DESCRIPTION <safe>")));
    assert(custom.html.includes(esc("CUSTOMER_COPY_INSTRUCTION <safe>")));
  });
  for(const priority of["low","normal","important","urgent"])test(`Gallery ${locale} displays ${priority} by the existing Memory label, not the stored enum`,()=>{
    const saved=current(locale,"/free-prompt-gallery",galleryContext("saved",{priority}));
    galleryAssertNormalized(saved,"saved");assert.equal(saved.context.freePromptGallerySaveResult.note.priority,priority);
    const key=Object.keys(saved.messages[locale]).find(key=>key==="memory.priority."+priority);
    assert(key,"Existing Memory priority key must be identified independently");
    assert(saved.html.includes(esc(saved.messages[locale][key])));
  });
  test(`Gallery ${locale} never shows a saved note for a mismatched selection or invalid receipt`,()=>{
    const raw=galleryContext("saved").freePromptGallerySaveResult;
    assert.equal(row.savedPreview(raw,"different_prompt"),"");
    for(const bad of[{...raw,note:{...raw.note,priority:"UNKNOWN"}},{...raw,note:{...raw.note,state:"archived"}},{}]){
      assert.equal(row.savedPreview(bad,"sample_one"),"");
    }
  });
}
for(const row of fixture.copyRows)for(const locale of locales)test(`Gallery reviewed copy ${locale}/${row.key} is present in the real dictionary`,()=>{
  assert.equal(rows.get(locale+":list").row.messages[locale][row.key],row.after[locale]);
});
for(const locale of locales)test(`Gallery ${locale} leaves every unrelated fixed message and key unchanged`,()=>{
  const {row,old}=rows.get(locale+":list"),owned=new Set(fixture.copyRows.map(copy=>copy.key));
  const historical=messages=>galleryNativeHistoricalSnapshot(Object.entries(messages),locale);
  const outside=messages=>historical(messages).filter(([key])=>!owned.has(key));
  assert.deepEqual(outside(row.messages[locale]),outside(old.messages[locale]));
  assert.deepEqual(historical(row.messages[locale]).map(([key])=>key),historical(old.messages[locale]).map(([key])=>key));
});
for(const pin of fixture.applicationSources)test("physical "+pin.file+" equals BASE plus only approved Gallery records",()=>{
  let expected=before[pin.file];
  for(const row of fixture.records.filter(row=>row.file===pin.file)){
    assert.equal(expected.split(row.old).length-1,1);expected=expected.replace(row.old,()=>row.new);
  }
  assert.equal(createHash("sha256").update(expected).digest("hex"),pin.afterLfSha256,"Original GPC pin remains immutable");
  if(pin.file===amendment.portalRecord.file){
    const row=amendment.portalRecord;assert.equal(expected.split(row.old).length-1,1);
    expected=expected.replace(row.old,()=>row.new);
  }
  assert.equal(galleryNativeHistoricalSource(physical[pin.file],pin.file)===expected,true,"No bytes outside GPC plus its frozen count amendment");
});
