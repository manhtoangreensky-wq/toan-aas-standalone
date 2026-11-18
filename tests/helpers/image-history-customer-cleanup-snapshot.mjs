import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
// Historical-comparator leaf only. Never normalize current rendering or current feature acceptance.
const fail="Unreviewed History customer cleanup",count=(source,part)=>source.split(part).length-1;
const pins=[
  ["ready-copy","4c4a2c9cf418331701f52195c092a150627375f6281bcfab0a470f14df8a3820","IMAGE-HISTORY-READY-COPY-20261118","5eee3247-8f69-48f6-8004-bfda7e287fac",8],
  ["customer-structure","2bd1a16e4bb9ff78f3344ec8f2b010ff7f23644ffb63ccf9f5f6f44f66d64673","IMAGE-HISTORY-CUSTOMER-STRUCTURE-20261118","de9c50e6-3cc8-4084-8225-a88c8d63ce01",2],
  ["outer-meta","6ecd6c9c47a0c24c0f7d059e28034f112019e4bd54f066437a063db4b27eca54","IMAGE-HISTORY-OUTER-META-20261119","98527f67-e77f-47a1-95aa-521c06aa2c58",5],
  ["refresh-feedback","d23dc6e3acd6365400205e60debad8564325d73b78af44c1253ecf8564c24d9a","IMAGE-HISTORY-REFRESH-FEEDBACK-20261119","11cba0b5-2678-4a9c-ae4e-cae51aa2479f",3],
  ["retry-label","48164df192a9a685a32159fc1819da97598be44f73ca48a2eb61b6f8d4ebcb6a","IMAGE-HISTORY-RETRY-LABEL-20261119","d524969c-a91f-409f-bc14-730f13405a9b",1]
];
const fixtures=pins.map(([name,sha,spec,conversation,total])=>{
  const raw=fs.readFileSync(new URL("../fixtures/image-history-"+name+"-reviewed.json",import.meta.url));
  assert.equal(createHash("sha256").update(raw).digest("hex"),sha,fail+" authority hash");
  const value=JSON.parse(raw);assert.equal(value.review.schemaValid,true);assert.equal(value.review.proposalExact,true);assert.equal(value.review.specId,spec);assert.equal(value.review.conversation,conversation);assert.equal(value.proposal.specId,spec);assert.equal(value.proposal.revision,"R1");assert.equal(value.proposal.changes.length,total);
  for(const edit of value.proposal.changes)assert.equal(edit.count,1);return value;
});
const edits=fixtures.flatMap(value=>value.proposal.changes);assert.equal(edits.length,19);
const FILES=["static/portal/portal-i18n.js","static/portal/portal.js","copyfast_pages.py","static/portal/integration.js"];
assert.deepEqual([...new Set(edits.map(edit=>edit.file))].sort(),[...FILES].sort());
const rowOrder=["history.intro.kicker","history.intro.title","history.intro.body","history.metric.count","history.results.title","history.results.description","history.retry","history.empty.title","history.empty.body"];
const rowEdit=edit=>edit.file===FILES[0]&&edit.old.trim().startsWith("[");
const rows=edits.filter(rowEdit).map(edit=>{const old=JSON.parse(edit.old.trim().replace(/,$/,"")),next=JSON.parse(edit.new.trim().replace(/,$/,""));assert.equal(old[0],next[0]);return{...edit,key:old[0],oldValues:old,nextValues:next};}).sort((a,b)=>rowOrder.indexOf(a.key)-rowOrder.indexOf(b.key));
assert.deepEqual(rows.map(row=>row.key),rowOrder);
function addition(edit){
  const prefix=edit.new.startsWith(edit.old),suffix=edit.new.endsWith(edit.old);
  if(!prefix&&!suffix)return null;assert.notEqual(prefix,suffix,fail+" ambiguous addition");
  const part=prefix?edit.new.slice(edit.old.length):edit.new.slice(0,-edit.old.length);assert.ok(part);return{...edit,part,prefix};
}
const additions=edits.map(addition).filter(Boolean),replacements=edits.filter(edit=>!addition(edit));
assert.equal(additions.length,8);assert.equal(replacements.length,11);
const appends=additions.filter(edit=>edit.file===FILES[0]);assert.equal(appends.length,2);
const catalogue={vi:[],en:[],zh:[]};
for(const edit of appends){
  const blocks=[...edit.part.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), \{\n([\s\S]*?)\n  \}\);/g)];
  assert.deepEqual(blocks.map(match=>match[1]),["vi","en","zh"]);
  for(const match of blocks)for(const line of match[2].split("\n")){
    const parsed=line.match(/^\s*(?:"([^"]+)"|([A-Za-z]\w*)):\s*("(?:[^"\\]|\\.)*"),?$/);assert.ok(parsed,fail+" static catalogue literal");
    catalogue[match[1]].push([parsed[1]||parsed[2],JSON.parse(parsed[3])]);
  }
}
const addedKeys=catalogue.vi.map(([key])=>key);assert.equal(addedKeys.length,5);assert.equal(new Set(addedKeys).size,5);
for(const locale of ["en","zh"])assert.deepEqual(catalogue[locale].map(([key])=>key),addedKeys);
const namespace=key=>key.startsWith("imageHistoryMetaUi")||key.startsWith("customerBridgeFeedback.imageHistory");
function owner(source,marker){
  assert.equal(count(source,marker),1,fail+" missing/duplicate owner");const start=source.indexOf(marker),next=source.indexOf("\n  function ",start+marker.length);
  assert.ok(next>start,fail+" owner boundary");return{start,end:next};
}
function inside(point,length,bounds){assert.ok(point>bounds.start&&point+length<bounds.end,fail+" detached owner chunk");}
function rowBounds(source){
  const marker="  const IMAGE_OPERATION_COPY_ROWS = [";assert.equal(count(source,marker),1,fail+" row owner");
  const start=source.indexOf(marker),end=source.indexOf("\n  ];",start);assert.ok(end>start,fail+" row owner end");return{start,end};
}
function sourceMarkers(source,file){
  if(file===FILES[0])return rows.some(row=>source.includes('["'+row.key+'",'))||addedKeys.some(key=>source.includes(key));
  if(file===FILES[1])return source.includes("imageHistoryMetaUi")||source.includes('<div class="portal-form-footer"><p>${safeText(t("boundary.item.three"');
  if(file===FILES[3])return ["imageHistoryRefreshed","imageHistoryRefreshFailed","imageHistoryAccessDenied"].some(key=>source.includes(key));
  return ["_PORTAL_SHELL_TITLES = {","_PORTAL_SHELL_DESCRIPTIONS = {"].some(marker=>{const start=source.indexOf(marker),end=source.indexOf("\n}",start);return start>=0&&end>start&&source.slice(start,end).includes('"/image/history":');});
}
export function historyCustomerCleanupHistoricalSource(source,file){
  assert.equal(typeof source,"string",fail);assert.ok(FILES.includes(file),fail+" file");
  const replaced=replacements.filter(edit=>edit.file===file),added=additions.filter(edit=>edit.file===file);
  if(!sourceMarkers(source,file)&&!replaced.some(edit=>count(source,edit.old)||count(source,edit.new))&&!added.some(edit=>count(source,edit.part)))return source;
  const phases=[...replaced.map(edit=>{const old=count(source,edit.old),next=count(source,edit.new);assert.ok((old===1&&next===0)||(old===0&&next===1),fail+" partial/unknown/duplicate replacement");return next;}),
    ...added.map(edit=>{const next=count(source,edit.part);assert.ok(next===0||next===1,fail+" duplicate addition");return next;})];
  assert.ok(phases.every(value=>value===0)||phases.every(value=>value===1),fail+" mixed/partial file");const next=phases[0]===1;
  if(file===FILES[0]){
    const bounds=rowBounds(source);let previous=bounds.start;
    for(const row of rows){const point=source.indexOf(next?row.new:row.old);inside(point,(next?row.new:row.old).length,bounds);assert.ok(point>previous,fail+" reordered row");previous=point;}
    if(next){const sequence=appends.map(edit=>edit.part).join("")+appends[0].old;assert.equal(count(source,sequence),1,fail+" detached/reordered appended catalogue");assert.ok(source.indexOf(sequence)>bounds.end,fail+" catalogue before row owner");}
  }else if(file===FILES[1]){
    const bounds=owner(source,"  function renderImageOperationHistory(");let previous=bounds.start;
    for(const edit of fixtures[1].proposal.changes){const text=next?edit.new:edit.old,point=source.indexOf(text);inside(point,text.length,bounds);assert.ok(point>previous,fail+" reordered History template");previous=point;}
    if(next)for(const[index,edit]of added.entries()){const point=source.indexOf(edit.part),bounds=owner(source,index===0?"  function localizedPageTitle(":"  function localizedPageDescription(");inside(point,edit.part.length,bounds);assert.equal(source.slice(point-edit.old.length,point),edit.old,fail+" detached metadata branch");}
  }else if(file===FILES[2]){
    if(next){let previous=-1;for(const edit of added){const point=source.indexOf(edit.part);assert.equal(count(source,edit.old),1,fail+" shell dictionary anchor");assert.equal(source.slice(point-edit.old.length,point),edit.old,fail+" detached shell dictionary");assert.ok(point>previous,fail+" reordered shell dictionaries");previous=point;}}
  }else if(next){
    const bounds=owner(source,"  function toast(message, type) {");let previous=bounds.start;
    for(const edit of added){const point=source.indexOf(edit.part);inside(point,edit.part.length,bounds);assert.equal(count(source,edit.old),1,fail+" map anchor");assert.equal(source.slice(point-edit.old.length,point),edit.old,fail+" detached toast map");assert.ok(point>previous,fail+" reordered toast maps");previous=point;}
  }
  if(!next)return source;let result=source;
  for(const edit of [...replaced].reverse())result=result.replace(edit.new,()=>edit.old);
  for(const edit of [...added].reverse())result=result.replace(edit.part,"");
  if(file===FILES[0]||file===FILES[1])assert.equal(result.includes("imageHistoryMetaUi"),false,fail+" unknown metadata namespace");
  if(file===FILES[0]||file===FILES[3])for(const key of ["imageHistoryRefreshed","imageHistoryRefreshFailed","imageHistoryAccessDenied"])assert.equal(result.includes(key),false,fail+" unknown feedback namespace");
  return result;
}
export function historyCustomerCleanupHistoricalSnapshot(entries,locale){
  const index=["vi","en","zh"].indexOf(locale)+1;assert.ok(index>0,fail+" locale");assert.ok(Array.isArray(entries),fail+" entries");
  const rowKeys=rows.map(row=>"imageOperationUi."+row.key),ownedRows=entries.filter(([key])=>rowKeys.includes(key)),ownedAdded=entries.filter(([key])=>namespace(key));
  if(!ownedRows.length&&!ownedAdded.length)return entries;
  assert.deepEqual(ownedRows.map(([key])=>key),rowKeys,fail+" missing/duplicate/reordered catalogue rows");
  const old=ownedRows.every(([,value],i)=>value===rows[i].oldValues[index]),next=ownedRows.every(([,value],i)=>value===rows[i].nextValues[index]);
  assert.ok(old||next,fail+" mixed/unknown catalogue values");
  if(old){assert.equal(ownedAdded.length,0,fail+" mixed old rows/new catalogue");return entries;}
  assert.deepEqual(ownedAdded,catalogue[locale],fail+" partial/unknown/duplicate/reordered additions");
  assert.ok(entries.indexOf(ownedRows.at(-1))<entries.indexOf(ownedAdded[0]),fail+" detached catalogue order");
  const prior=new Map(rows.map((row,i)=>[rowKeys[i],row.oldValues[index]]));
  return entries.filter(([key])=>!addedKeys.includes(key)).map(entry=>prior.has(entry[0])?[entry[0],prior.get(entry[0])]:entry);
}
