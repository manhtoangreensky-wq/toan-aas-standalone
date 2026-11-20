import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {sharedSelectLabelsHistoricalSource,sharedSelectLabelsHistoricalSnapshot} from './shared-select-labels-snapshot.mjs';

// Finite historical leaf only. Current-source acceptance must read physical files.
const raw=fs.readFileSync(new URL('../fixtures/vault-action-feedback-reviewed.json',import.meta.url));
const fail='Unreviewed Vault action feedback',count=(source,part)=>source.split(part).length-1;
assert.equal(createHash('sha256').update(raw).digest('hex'),'488924a1ee5bcd7b49b53a4a366ba6a4e31f4df2eca0e518af8af9163e9c4801',fail+' authority');
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const integration='static/portal/integration.js',i18n='static/portal/portal-i18n.js';
assert.equal(fixture.task,'VAULT-ACTION-FEEDBACK-20261120');assert.equal(fixture.base,'e49427e5e35378c0fc8b41d68b772af88501f556');assert.equal(fixture.revision,'ROOT_REVIEWED_EXACT_R1');
assert.equal(edits.length,34);assert.equal(edits.reduce((sum,edit)=>sum+edit.count,0),36);
assert.ok(edits.every(edit=>[integration,i18n].includes(edit.file)&&[1,2].includes(edit.count)&&typeof edit.old==='string'&&edit.old.length>0&&typeof edit.new==='string'&&edit.new.length>0));
assert.equal(rows.length,35);assert.equal(new Set(keys).size,35);
assert.ok(rows.every(row=>row.length===4&&/^vaultFeedback\.[A-Za-z]+$/.test(row[0])&&row.slice(1).every(value=>typeof value==='string'&&value.length>0)));
assert.equal(rows.flatMap(row=>row.slice(1)).length,105);
assert.equal(fixture.applicationBaseline.length,151);assert.equal(new Set(fixture.applicationBaseline.map(pin=>pin.file)).size,151);
assert.deepEqual(fixture.applicationBaseline.filter(pin=>pin.changed).map(pin=>pin.file).sort(),[integration,i18n].sort());
assert.equal(fixture.applicationBaseline.filter(pin=>!pin.changed).length,149);
assert.ok(fixture.applicationBaseline.every(pin=>pin.changed===(pin.baselineLfSha256!==pin.candidateLfSha256)));
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.lane,value.model,value.resultRawSha256,value.expectedSha256,value.packetSha256,value.schemaSha256,value.records,value.replacementSites]),[
 ['read','gemini-3.8-flash-high','6e24c3f9bc2809e2c42d4a2d3c78e015c1495ed1506c5317a2979caf43bc995d','073a4dcbd6d6750cec01818a3006e48c8f85c8d0c021dfab2a8a26db69edf871','14ede2c29d3401d5500bba4d800ba8e5a5ad3f8d648ea53714b6d89558140988','5cdce52bf1050dde0c492ed8c0d055c91c867dd61d35573dedfb7504421c8ce7',3,3],
 ['readcopy','gemini-3.8-flash-high','27591c787b09d7ca07f804956fa88886001de1ccaeed51834f8be1b254a74389','3a57e5c95ee8260006f418a2863561980a61da1ba739e8aaeff628a2aaeb97fb','5a0e63cc91af19d0d4b7ac4c36c148efea84bc28b824a276ca192c7bacd48043','27a9b5227b47304698c5e991bef5df823177f4608b2058469326730b42606015',10,11],
 ['writecopy','gemini-3.8-flash-high','a106c5a5937bdb58a9171f682df8d953420f2e04d44803da83abc8ee15f4054d','7bf8df2bf50e7bb57f523708f718dd41868944bd75da5f630abd90e4c9e0ec33','1091d500a757e89e28222a98213404329cc2c6f07de75e4394dbd53c0152c92a','2490a25be948a4309453d0e933cc6ea6457b3e11f546c6a5b6df09b9efeece61',19,20],
 ['catalogue','gemini-3.8-flash-high','b7bf7dda5553c8fc6cff8fc191d866463d1de59168505faba8d01aa1e84b626b','8c932c54d930a47f507ffc17d0be5489bc75bc481f322ef83335536dc92d57ec','6c59d72c96ec049f770d4a8100ee0d9695b13fdfa433dfe814031a9078fe11d7','5285848802fd618e86ab0a74dc1217ce1b2e42e2be5cecd443b81bc04e0acf3d',2,2]
]);
assert.ok(fixture.sourceAuthorities.every(value=>value.proposalExact&&value.applicationWrites===0&&value.workerVerify==='NOT_RUN'&&value.runtimeAcceptance==='NOT_YET_VERIFIED'));
assert.equal(fixture.providerCalls,0);assert.equal(fixture.walletMutations,0);assert.equal(fixture.productionDataMutations,0);assert.equal(fixture.ownerCampaignStateOpened,false);
const integrationEdits=edits.filter(edit=>edit.file===integration),catalogue=edits.find(edit=>edit.file===i18n);
assert.equal(integrationEdits.length,33);assert.equal(edits.filter(edit=>edit.file===i18n).length,1);
const helperMarker='  function vaultFeedbackText(key, fallback) {',filterMarker='  function assetVaultFilterPayload(value) {';
const helper=integrationEdits.find(edit=>edit.new.startsWith(helperMarker));
assert.ok(helper);assert.equal(helper.old,filterMarker);assert.ok(helper.new.endsWith('\n\n'+filterMarker));
assert.equal(catalogue.old,'  verifyEqualKeysets();');assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];
assert.deepEqual(blocks.map(match=>match[1]),['vi','en','zh']);
for(const[locale,index]of [['vi',1],['en',2],['zh',3]])assert.deepEqual(Object.entries(JSON.parse(blocks.find(match=>match[1]===locale)[2])),rows.map(row=>[row[0],row[index]]));
const calls=source=>[...source.matchAll(/\b(vaultFeedback[A-Za-z0-9_]*)\s*\(/g)].map(match=>match[1]);
const keyReferences=source=>[
 ...source.matchAll(/\b(?:[A-Za-z_$][\w$]*\.)*(?:t|uiText)\(\s*["'](vaultFeedback[^"']*)["']/g),
 ...source.matchAll(/\[\s*["'](vaultFeedback[^"']*)["']\s*\]/g)
].map(match=>match[1]);
const declarations=source=>[...source.matchAll(/(?:["'](vaultFeedback[^"']*)["']|\b(vaultFeedback[A-Za-z0-9_.]*))\s*:/g)].map(match=>match[1]||match[2]);
const expectedCalls=integrationEdits.flatMap(edit=>Array.from({length:edit.count},()=>calls(edit.new)).flat());
const expectedReferences=integrationEdits.flatMap(edit=>Array.from({length:edit.count},()=>keyReferences(edit.new)).flat());
assert.equal(expectedCalls.length,40);assert.ok(expectedCalls.every(name=>name==='vaultFeedbackText'));
assert.deepEqual(expectedReferences,['vaultFeedback.']);
const owners={
 filter:[filterMarker,'  function assetVaultListOffset('],
 lifecycle:['  async function hydrateAssetVaultLifecycle(','  async function hydrateDocumentAssetReferences('],
 action:['  async function handleAction(','  function synchronizeScriptToScreenEpisodeFields(']
};
function ownerBounds(source,[marker,next]){
 assert.equal(count(source,marker),1,fail+' owner count');assert.equal(count(source,next),1,fail+' next owner count');
 const start=source.indexOf(marker),end=source.indexOf(next,start+marker.length);
 assert.ok(start>=0&&end>start,fail+' owner bounds');return[start,end];
}
function editOwner(edit){
 if(edit.old.startsWith(filterMarker)||edit.old.startsWith('    if (!ASSET_VAULT_LIST_STATES.has(state))'))return'filter';
 if(edit.old.startsWith('    if (!validVaultAssetId(selectedAssetId))')||edit.old.startsWith('      if (!lifecycle) throw new Error('))return'lifecycle';
 return'action';
}
function positions(source,part){
 const found=[];let at=source.indexOf(part);
 while(at>=0){found.push(at);at=source.indexOf(part,at+part.length);}
 return found;
}
function inverseExact(source,group){
 let result=source;
 for(const edit of [...group].reverse()){
  assert.equal(count(result,edit.new),edit.count,fail+' inverse fragment count');
  for(let at=0;at<edit.count;at++)result=result.replace(edit.new,()=>edit.old);
 }
 return result;
}
export function vaultActionFeedbackHistoricalSource(source,file){
 assert.equal(typeof source,'string',fail);
 source=sharedSelectLabelsHistoricalSource(source,file);
 if(file!==integration&&file!==i18n)return source;
 const foundCalls=calls(source),foundReferences=keyReferences(source),foundDeclarations=declarations(source);
 if(!foundCalls.length&&!foundReferences.length&&!foundDeclarations.length)return source;
 if(file===integration){
  for(const edit of integrationEdits)assert.equal(count(source,edit.new),edit.count,fail+' partial/mixed/changed/duplicate integration set');
  assert.deepEqual(foundCalls,expectedCalls,fail+' unknown/duplicate/missing prefixed calls');
  assert.deepEqual(foundReferences,expectedReferences,fail+' unknown prefixed keys');
  assert.equal(foundDeclarations.length,0,fail+' detached prefixed declarations');
  assert.equal(count(source,helperMarker),1,fail+' helper owner');
  assert.equal(source.indexOf(helper.new),source.indexOf(helperMarker),fail+' detached helper');
  const bounds=Object.fromEntries(Object.entries(owners).map(([name,markers])=>[name,ownerBounds(source,markers)]));
  for(const edit of integrationEdits){
   if(edit===helper)continue;
   const[start,end]=bounds[editOwner(edit)];
   for(const point of positions(source,edit.new))assert.ok(point>=start&&point+edit.new.length<=end,fail+' displaced integration fragment');
  }
  return inverseExact(source,integrationEdits);
 }
 assert.equal(foundCalls.length,0,fail+' unknown catalogue call');
 assert.equal(count(source,catalogue.new),1,fail+' partial/changed/duplicate catalogue');
 assert.equal(foundReferences.length,0,fail+' detached prefixed key reference');
 assert.deepEqual(foundDeclarations,[...keys,...keys,...keys],fail+' unknown/duplicate/reordered catalogue keys');
 assert.equal(count(source,catalogue.old),1,fail+' keyset owner');
 const freeze='  deepFreeze(MESSAGES);',point=source.indexOf(catalogue.new);
 assert.equal(count(source,freeze),1,fail+' freeze owner');assert.ok(point<source.indexOf(freeze),fail+' post-freeze catalogue');
 assert.ok(source.slice(point+catalogue.new.length).startsWith('\n\n  function deepFreeze(value) {'),fail+' detached catalogue');
 return inverseExact(source,[catalogue]);
}
export function vaultActionFeedbackHistoricalSnapshot(entries,locale){
 const index=['vi','en','zh'].indexOf(locale)+1;
 assert.ok(index>0,fail+' locale');assert.ok(Array.isArray(entries),fail+' entries');
 entries=sharedSelectLabelsHistoricalSnapshot(entries,locale);
 const owned=entries.filter(([key])=>typeof key==='string'&&key.startsWith('vaultFeedback'));
 if(!owned.length)return entries;
 assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+' partial/changed/duplicate/reordered/unknown catalogue rows');
 return entries.filter(([key])=>!keys.includes(key));
}
