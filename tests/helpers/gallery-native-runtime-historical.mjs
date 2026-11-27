// Exact finite runtime inverse for historical QA inputs; never app runtime.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {authReturnHistoricalSource} from './auth-return-historical.mjs';

const failure='Unreviewed Gallery native runtime history';
const base='29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef';
const integration='static/portal/integration.js';
const backendFiles=new Set(['copyfast_free_prompt_gallery.py','copyfast_memory.py']);
const sha=value=>createHash('sha256').update(value).digest('hex');
const require=(condition,label)=>assert.ok(condition,failure+': '+label);
const count=(source,part)=>source.split(part).length-1;
const once=(source,part,label)=>{
  require(typeof part==='string'&&part.length>0,'nonempty '+label);
  require(count(source,part)===1,'unique '+label);
  return source.indexOf(part);
};
const end=(source,start,closing,label)=>{
  const at=source.indexOf(closing,start);
  require(at>start,'closed '+label);
  return at+closing.length;
};
const lineStart=(source,index)=>index===0||source[index-1]==='\n';
const declaration=/^  (?:async )?function [A-Za-z_][A-Za-z0-9_]*\(/gm;
const pythonDeclaration=/^(?:async )?def [A-Za-z_][A-Za-z0-9_]*\(/gm;
const topLevelPython=/^(?:(?:async )?def |class |@)/gm;

function fixture(name,pin,expectedCount){
  const raw=fs.readFileSync(new URL('../fixtures/'+name,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  require(sha(raw)===pin,name+' fixture hash');
  const data=JSON.parse(raw);
  require(data.base_sha===base&&data.records.length===expectedCount,name+' BASE/count');
  for(const row of data.records){
    require(typeof row.before==='string'&&typeof row.after==='string',name+' record shape');
    require(sha(row.before)===row.before_lf_sha256,name+' before hash');
    require(sha(row.after)===row.after_lf_sha256,name+' after hash');
  }
  return data;
}
const transport=fixture('gallery-native-transport-history.json','70194054446d00266cd8d0c692d668588a29d4dcb23cdbf647e7c74cfd141d05',11);
const backend=fixture('gallery-native-backend-history.json','d6fedb7c38b7abec4cd138069dc5aa2634945aff7003b1b0039407c66fa5733f',7);
require(transport.file===integration&&transport.records.every(row=>row.file===integration),'integration targets');
require(backend.conversation_id==='bffacabe-abf0-40df-92c2-bdf9a9b6f0b3','backend conversation');
require(backend.records.every((row,index)=>backendFiles.has(row.file)&&row.proposal_record===index),'backend targets/order');

function transportSlot(source,row){
  const start=once(source,row.after,'approved after'),stop=start+row.after.length;
  const slot=row.slot,previous=once(source,slot.previous,'previous slot owner');
  const following=once(source,slot.following,'following slot owner');
  let lower;
  if(slot.kind==='function'){
    lower=end(source,previous,'\n  }\n','previous function');
  }else if(slot.kind==='action'){
    lower=end(source,previous,'\n      }\n','previous action');
    const owner=once(source,'  async function handleAction(event) {','handleAction owner');
    const ownerEnd=end(source,owner,'\n  }\n','handleAction');
    require(owner<start&&start<stop&&stop<ownerEnd,'action inside handleAction');
    once(source,row.after.split('\n')[0],'action branch');
  }else{
    require(slot.kind==='state','known transport slot kind');
    lower=previous+slot.previous.length;
    once(source,row.after.split('\n')[0],'state declaration');
  }
  require(lower<=start&&start<stop&&stop<=following,'transport record slot/order');
  for(const marker of row.after.matchAll(declaration))once(source,marker[0],'function declaration owner');
}

function backendSlot(source,row){
  const start=once(source,row.after,'approved backend after'),stop=start+row.after.length;
  const slot=row.slot,previous=once(source,slot.previous,'previous backend owner');
  require(lineStart(source,start)&&lineStart(source,previous),'backend top-level placement');
  let lower=previous+slot.previous.length;
  if(slot.kind==='import'){
    const owner=once(source,slot.owner,'locale import owner');
    require(lineStart(source,owner)&&owner>=start&&owner<stop,'top-level owned import');
  }else{
    require(['function','partial_function','final_function'].includes(slot.kind),'known backend slot kind');
    lower=end(source,previous,slot.previous_end,'previous backend body');
    const owner=once(source,slot.owner,'backend declaration owner');
    require(owner>=start&&owner<stop&&lineStart(source,owner),'backend owner inside record');
    for(const marker of row.after.matchAll(pythonDeclaration))once(source,marker[0],'Python declaration owner');
    // A complete record moved under an unrelated top-level owner is not its approved slot.
    require(![...source.slice(lower,start).matchAll(topLevelPython)].length,'no foreign owner in backend slot');
  }
  require(lower<=start,'backend previous boundary');
  if(slot.kind==='partial_function'){
    const remaining=source.slice(stop);
    const nextOwner=topLevelPython.exec(remaining)?.index??remaining.length;
    topLevelPython.lastIndex=0;
    const following=remaining.indexOf(slot.following);
    require(following>=0&&following<nextOwner,'backend same-function following boundary');
    require(count(remaining.slice(0,nextOwner),slot.following)===1,'unique local following boundary');
  }else if(slot.following!==null){
    const following=once(source,slot.following,'following backend owner');
    require(stop<=following,'backend following boundary');
  }
}

const transportSignals=/^[ \t]*(?:let freePromptGalleryLocaleOwner[ \t]*=|const freePromptGalleryActionEpochs[ \t]*=|const FREE_PROMPT_GALLERY_FEEDBACK_VI[ \t]*=)|freePromptGalleryCreateError\(|freePromptGalleryActiveLocale\(|function freePromptGalleryItemsPath\(filter, page, locale\)/m;
const backendSignals=/^from copyfast_gallery_locale import |gallery_locale_text\(|localized_gallery_item\(|gallery_taxonomy_label\(|^def _matches_native_taxonomy\(|lang: str \| None = Query\(None, pattern="\^\(vi\|en\|zh\)\$"\)/m;

export function galleryNativeRuntimeHistoricalSource(source,file){
  require(typeof source==='string','string source');
  source=authReturnHistoricalSource(source,file);
  if(file===integration){
    if(!transportSignals.test(source))return source;
    for(const row of [...transport.records].reverse()){
      transportSlot(source,row);
      source=source.replace(row.after,()=>row.before);
    }
    return source;
  }
  if(!backendFiles.has(file)||!backendSignals.test(source))return source;
  for(const row of backend.records.filter(row=>row.file===file).reverse()){
    backendSlot(source,row);
    source=source.replace(row.after,()=>row.before);
  }
  return source;
}
