import fs from 'node:fs';
import {mediaCollectionHistoricalSnapshot} from "./media-collection-locale-snapshot.mjs";
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {sharedSelectReminderTitleHistoricalSource} from './shared-select-reminder-title-snapshot.mjs';

// Finite historical comparison only; newest acceptance reads complete physical sources.
const raw=fs.readFileSync(new URL('../fixtures/shared-select-labels-reviewed.json',import.meta.url));
const fail='Unreviewed Shared select labels',count=(source,part)=>source.split(part).length-1;
assert.equal(createHash('sha256').update(raw).digest('hex'),'7cb67db3464cb45d3e0b243f388affb981fd4f5780e0ebb28105865885786817',fail+' authority');
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const portal='static/portal/portal.js',i18n='static/portal/portal-i18n.js';
assert.equal(fixture.task,'SHARED-SELECT-LABELS-20261120');assert.equal(fixture.base,'46423a6df9af67ac7ccabd88686d4cb42523a078');assert.equal(fixture.revision,'ROOT_REVIEWED_EXACT_R1A_TRANSPORT_ONLY');
assert.equal(edits.length,4);assert.ok(edits.every(edit=>edit.count===1&&typeof edit.old==='string'&&edit.old.length>0&&typeof edit.new==='string'&&edit.new.length>0));
assert.deepEqual(edits.map(edit=>edit.file),[portal,portal,portal,i18n]);
assert.deepEqual(keys,['sharedSelect.projectFallback','sharedSelect.noteFallback','sharedSelect.voiceFallback','sharedSelect.voiceDefaultSuffix']);
assert.equal(new Set(keys).size,4);assert.ok(rows.every(row=>row.length===4&&row.slice(1).every(value=>typeof value==='string'&&value.length>0)));assert.equal(rows.flatMap(row=>row.slice(1)).length,12);
assert.equal(fixture.applicationBaseline.length,151);assert.equal(new Set(fixture.applicationBaseline.map(pin=>pin.file)).size,151);
assert.deepEqual(fixture.applicationBaseline.filter(pin=>pin.changed).map(pin=>pin.file).sort(),[portal,i18n].sort());
assert.equal(fixture.applicationBaseline.filter(pin=>!pin.changed).length,149);
assert.ok(fixture.applicationBaseline.every(pin=>pin.changed===(pin.baselineLfSha256!==pin.candidateLfSha256)));
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.lane,value.model,value.transportRevision,value.resultRawSha256,value.packetSha256,value.schemaSha256,value.expectedSha256,value.records]),[
 ['projectnote','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','a4e2426f299641fc3dd31efd710d3b715e168e8070eae03832fffc78004a0078','09e1a3d2a96f17b1177ea4e68b65a1670d39a2f416d17f2687b6072acbca32cc','5285848802fd618e86ab0a74dc1217ce1b2e42e2be5cecd443b81bc04e0acf3d','a9dabbebf6c8e8752a2762a4c597e47b48a2a5018032aacf802441263f6da33f',2],
 ['voice','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','5bfd36db7979dafc89cd88f8d8c266ebd6aa513c8ff33799fbc5acb26cf4337e','32b695190ee816f69435cf85b73f985ebc7642362379f9c165f2244c001e551f','f7d0a54dc3666a8f1c7011e544d050398de509a466c1227d393e930333c99bc1','9089c8b8ffd08e1ba3346dd1ffd60b4bcee09db209a42c7359541b6b10f2e751',1],
 ['catalogue','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','05c14c5b7874ff7507ac4675949f448ed1669cc12e54dc450d0ca0ba4a386f8a','e3b7b4c373bdb650a28ab428c2d5afe408f7c74ce967a3b709c45dc99d703448','f7d0a54dc3666a8f1c7011e544d050398de509a466c1227d393e930333c99bc1','18a125cea1e619aa16ab66dfda1081a4a0eecf1ebe982eeac79239fdaa3b4da7',1]
]);
assert.ok(fixture.sourceAuthorities.every(value=>value.proposalExact&&value.workerVerify==='NOT_RUN'&&value.applicationWrites===0&&value.workerCodeFailures===0));
assert.equal(fixture.applicationWrites,0);assert.equal(fixture.providerCalls,0);assert.equal(fixture.walletMutations,0);assert.equal(fixture.productionDataMutations,0);assert.equal(fixture.ownerCampaignStateOpened,false);
const expressions=edits.filter(edit=>edit.file===portal),catalogue=edits.find(edit=>edit.file===i18n);
const owner='  function renderFields(fields, enabled, context, fieldValues, idNamespace) {',nextOwner='  function statusMessage(page, status, context) {';
const lookups=source=>[...source.matchAll(/\b(?:[A-Za-z_$][\w$]*\.)*(?:uiText|t)\(\s*["'](sharedSelect[^"']*)["']/g)].map(match=>match[1]);
const prefixedCalls=source=>[...source.matchAll(/\b(sharedSelect[A-Za-z0-9_]*)\s*\(/g)].map(match=>match[1]);
const declarations=source=>[...source.matchAll(/(?:["'](sharedSelect[^"']*)["']|\b(sharedSelect[A-Za-z0-9_.]*))\s*:/g)].map(match=>match[1]||match[2]);
const accessors=source=>[
 ...source.matchAll(/\[\s*["'](sharedSelect[^"']*)["']\s*\]/g),
 ...source.matchAll(/\bMESSAGES\.(?:vi|en|zh)\.(sharedSelect[A-Za-z0-9_]*)\s*=/g)
].map(match=>match[1]);
assert.deepEqual(expressions.flatMap(edit=>lookups(edit.new)),keys);
assert.equal(catalogue.old,'  verifyEqualKeysets();');assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];
assert.deepEqual(blocks.map(match=>match[1]),['vi','en','zh']);
for(const[locale,index]of [['vi',1],['en',2],['zh',3]])assert.deepEqual(Object.entries(JSON.parse(blocks.find(match=>match[1]===locale)[2])),rows.map(row=>[row[0],row[index]]));
function inverseExact(source,group){
 let result=source;
 for(const edit of [...group].reverse()){
  assert.equal(count(result,edit.new),1,fail+' inverse fragment count');
  result=result.replace(edit.new,()=>edit.old);
 }
 return result;
}
export function sharedSelectLabelsHistoricalSource(source,file){
 assert.equal(typeof source,'string',fail);
 source=sharedSelectReminderTitleHistoricalSource(source,file);
 if(file!==portal&&file!==i18n)return source;
 const foundLookups=lookups(source),foundCalls=prefixedCalls(source),foundDeclarations=declarations(source),foundAccessors=accessors(source);
 if(!foundLookups.length&&!foundCalls.length&&!foundDeclarations.length&&!foundAccessors.length)return source;
 assert.equal(foundCalls.length,0,fail+' unknown prefixed calls');assert.equal(foundAccessors.length,0,fail+' unknown prefixed key access');
 if(file===portal){
  for(const edit of expressions){
   assert.equal(count(source,edit.new),1,fail+' partial/mixed/changed/duplicate expression set');
   assert.equal(count(source,edit.old),0,fail+' mixed OLD expression');
  }
  assert.deepEqual(foundLookups,[keys[2],keys[3],keys[0],keys[1]],fail+' unknown/duplicate/reordered owned calls');
  assert.equal(foundDeclarations.length,0,fail+' detached prefixed declarations');
  assert.equal(count(source,owner),1,fail+' renderFields owner');assert.equal(count(source,nextOwner),1,fail+' statusMessage next owner');
  const start=source.indexOf(owner),end=source.indexOf(nextOwner,start+owner.length);
  assert.ok(start>=0&&end>start,fail+' owner bounds');
  assert.ok(source.slice(start,end).endsWith('    }).join("")}</div>`;\n  }\n\n'),fail+' incomplete renderFields owner');
  for(const edit of expressions){const point=source.indexOf(edit.new);assert.ok(point>start&&point+edit.new.length<end,fail+' displaced expression');}
  return inverseExact(source,expressions);
 }
 assert.equal(foundLookups.length,0,fail+' unknown catalogue lookup');
 assert.equal(count(source,catalogue.new),1,fail+' partial/changed/duplicate catalogue');
 assert.deepEqual(foundDeclarations,[...keys,...keys,...keys],fail+' unknown/duplicate/reordered catalogue keys');
 assert.equal(count(source,catalogue.old),1,fail+' keyset owner');
 const freeze='  deepFreeze(MESSAGES);',point=source.indexOf(catalogue.new);
 assert.equal(count(source,freeze),1,fail+' freeze owner');assert.ok(point<source.indexOf(freeze),fail+' post-freeze catalogue');
 assert.ok(source.slice(point+catalogue.new.length).startsWith('\n\n  function deepFreeze(value) {'),fail+' detached catalogue');
 return inverseExact(source,[catalogue]);
}
export function sharedSelectLabelsHistoricalSnapshot(entries,locale){
 const index=['vi','en','zh'].indexOf(locale)+1;
 assert.ok(index>0,fail+' locale');assert.ok(Array.isArray(entries),fail+' entries');
 assert.ok(entries.every(entry=>Array.isArray(entry)&&entry.length===2),fail+' entry shape');
 entries=mediaCollectionHistoricalSnapshot(entries,locale);
 const owned=entries.filter(([key])=>typeof key==='string'&&key.startsWith('sharedSelect'));
 if(!owned.length)return entries;
 assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+' partial/changed/duplicate/reordered/unknown catalogue rows');
 return entries.filter(([key])=>!keys.includes(key));
}
