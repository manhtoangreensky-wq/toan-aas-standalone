import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
// Finite historical-comparator leaf only; current renderers keep full physical application sources.
const raw=fs.readFileSync(new URL("../fixtures/image-edit-customer-copy-reviewed.json",import.meta.url));
const fail="Unreviewed Image Edit customer copy",count=(source,part)=>source.split(part).length-1;
assert.equal(createHash("sha256").update(raw).digest("hex"),"7032192534419999f7528e3a6dbf08151b5db6ed96b3c49c7ecb300a6434007f",fail+" authority hash");
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,portal="static/portal/portal.js",i18n="static/portal/portal-i18n.js",css="static/portal/portal.css";
assert.equal(fixture.task,"IMAGE-EDIT-CUSTOMER-CLEANUP-20261119");assert.equal(fixture.base,"f8932643c1408d6565a0f1574f9bdd47ffac267b");assert.equal(edits.length,22);assert.ok(edits.every(edit=>edit.count===1));
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.specId,value.revision,value.conversation,value.rawSha256]),[
  ["IMAGE-EDIT-FIELD-CUSTOMER-COPY-20261119","R1","2de93bdb-93f6-406a-9a6e-69fde819c878","540e8f4a7281ee7f6e7918e8608f1b99a100508246d06a0c9dab28abb01e4b3d"],
  ["IMAGE-EDIT-PAGE-CUSTOMER-CLEANUP-20261119","R2","e9a2f3d9-3bac-4296-a74a-beb8430a8bb1","769b69918963117776470352ac566ee8fca335a6f895db451c58a43d9d1f3c9c"],
  ["IMAGE-EDIT-MOBILE-NAV-DENSITY-20261119","R1","ae13811a-add8-4f7e-8563-2e60282682c6","d2278e4adfb61732bdb72dd5432e1cb0d9b417e1310575fe307c2e917f762a5c"]]);
assert.equal(fixture.sourceAuthorities[0].proposalExact,true);assert.equal(fixture.sourceAuthorities[1].correctionExact,true);assert.equal(fixture.sourceAuthorities[1].proposalWholeTargetExact,true);assert.equal(fixture.sourceAuthorities[1].sameFragmentFailures,1);assert.equal(fixture.sourceAuthorities[1].r1NewAndEightRowsPreserved,true);assert.equal(fixture.sourceAuthorities[2].proposalExact,true);
assert.equal(fixture.workerApplicationTakeover,false);assert.equal(fixture.rootApplicationCodeAuthored,false);
const pageEdits=edits.filter(edit=>edit.file===portal),styleEdits=edits.filter(edit=>edit.file===css),rowEdits=edits.filter(edit=>edit.file===i18n);
assert.equal(pageEdits.length,1);assert.equal(styleEdits.length,1);assert.equal(rowEdits.length,20);assert.equal(fixture.fieldsRows.length,12);assert.equal(fixture.pageRows.length,8);assert.deepEqual(fixture.mobileCss,styleEdits);
const ordered=[...fixture.pageRows,...fixture.fieldsRows],keys=ordered.map(row=>row[0]),catalogKeys=keys.map(key=>"imageOperationUi."+key);
assert.equal(new Set(keys).size,20);
const rows=rowEdits.map(edit=>{
  const old=JSON.parse(edit.old.trim().replace(/,$/,"")),next=JSON.parse(edit.new.trim().replace(/,$/,""));
  assert.equal(old.length,4);assert.equal(next.length,4);assert.equal(old[0],next[0]);assert.deepEqual(next,ordered.find(row=>row[0]===next[0]));
  return{...edit,key:old[0],oldRow:old,newRow:next};
}).sort((a,b)=>keys.indexOf(a.key)-keys.indexOf(b.key));
assert.deepEqual(rows.map(row=>row.key),keys);
const page=pageEdits[0],style=styleEdits[0],owner="  function renderImageEnhance(",nextOwner="  function renderImageUpscale(";
assert.ok([page.old,page.new].every(text=>text.startsWith(owner)&&text.endsWith("  }\n\n")));assert.ok(style.new.startsWith(style.old));
const block=style.new.slice(style.old.length),styleMarker="/* Compact only the manual image editor's mobile workspace navigation. */";
assert.ok(block.startsWith("\n"+styleMarker+"\n@media (max-width: 700px) {"));assert.ok(block.endsWith("\n}\n"));
const scopedLines=text=>[...text.matchAll(/^[ \t]*(\.portal-image-enhance \.portal-image-create-[^\n]*)/gm)].map(match=>match[1]);
assert.equal(scopedLines(block).length,9);
function rowDeclarations(source){
  return [...source.matchAll(/^[ \t]*\[\s*"([^"]+)"\s*,[^\n]*/gm)].filter(match=>keys.includes(match[1]));
}
export function imageEditCustomerHistoricalSource(source,file){
  assert.equal(typeof source,"string",fail);
  if(file===portal){
    const old=count(source,page.old),next=count(source,page.new);
    if(!source.includes(owner)&&!source.includes(nextOwner)&&!old&&!next)return source;
    assert.equal(count(source,owner),1,fail+" missing/duplicate function owner");assert.equal(count(source,nextOwner),1,fail+" next owner count");
    assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/changed/duplicate complete function");
    const chunk=next?page.new:page.old,start=source.indexOf(chunk);assert.equal(start,source.indexOf(owner),fail+" detached complete function");
    assert.ok(source.slice(start+chunk.length).startsWith(nextOwner),fail+" immediate next owner");
    return next?source.replace(page.new,()=>page.old):source;
  }
  if(file===i18n){
    const found=rowDeclarations(source);if(!found.length)return source;
    const marker="  const IMAGE_OPERATION_COPY_ROWS = [",start=source.indexOf(marker),end=source.indexOf("\n  ];",start);
    assert.equal(count(source,marker),1,fail+" catalogue owner");assert.ok(end>start,fail+" catalogue boundary");
    const tail='\n  ];\n  ["vi", "en", "zh"].forEach((locale, index) => {\n    IMAGE_OPERATION_COPY_ROWS.forEach((row) => { MESSAGES[locale][`imageOperationUi.${row[0]}`] = row[index + 1]; });\n  });';
    assert.ok(source.slice(end).startsWith(tail),fail+" attached catalogue close/consumer");
    assert.equal(found.length,20,fail+" partial/duplicate row declarations");assert.deepEqual(found.map(match=>match[1]),keys,fail+" unknown/reordered row keys");
    const phases=rows.map(edit=>[count(source,edit.old),count(source,edit.new)]),old=phases.every(([a,b])=>a===1&&b===0),next=phases.every(([a,b])=>a===0&&b===1);
    assert.ok(old||next,fail+" partial/mixed/changed rows");let previous=start;
    for(const edit of rows){const text=next?edit.new:edit.old,point=source.indexOf(text);assert.ok(point>previous&&point+text.length<end,fail+" detached/reordered row");previous=point;}
    if(old)return source;let result=source;for(const edit of rows)result=result.replace(edit.new,()=>edit.old);return result;
  }
  if(file===css){
    const found=scopedLines(source),next=count(source,block);
    if(!found.length&&!source.includes(styleMarker)){assert.equal(next,0,fail+" missing CSS owner");return source;}
    assert.equal(next,1,fail+" partial/changed/duplicate CSS block");assert.equal(count(source,styleMarker),1,fail+" CSS owner count");
    assert.deepEqual(found,scopedLines(block),fail+" unknown/duplicate/reordered scoped CSS");assert.equal(count(source,style.old),1,fail+" CSS prior anchor");assert.equal(count(source,style.new),1,fail+" detached CSS block");
    return source.replace(style.new,()=>style.old);
  }
  return source;
}
export function imageEditCustomerHistoricalSnapshot(entries,locale){
  const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");assert.ok(Array.isArray(entries),fail+" entries");
  const owned=entries.filter(([key])=>catalogKeys.includes(key));if(!owned.length)return entries;
  assert.deepEqual(owned.map(([key])=>key),catalogKeys,fail+" partial/duplicate/reordered catalogue");
  // Equal OLD/NEW EN/ZH cells are neutral; the entire changed set must still have one coherent phase.
  const old=owned.every(([,value],at)=>value===rows[at].oldRow[index]),next=owned.every(([,value],at)=>value===rows[at].newRow[index]);
  assert.ok(old||next,fail+" mixed/unknown catalogue values");if(old)return entries;
  const prior=new Map(rows.map((row,at)=>[catalogKeys[at],row.oldRow[index]]));
  return entries.map(entry=>prior.has(entry[0])?[entry[0],prior.get(entry[0])]:entry);
}
