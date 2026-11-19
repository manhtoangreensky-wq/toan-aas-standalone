import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
// Finite newest historical leaf only. Current renderer/source acceptance must stay physical.
const raw=fs.readFileSync(new URL('../fixtures/vault-customer-copy-reviewed.json',import.meta.url));
const fail='Unreviewed Vault customer copy',count=(source,part)=>source.split(part).length-1;
assert.equal(createHash('sha256').update(raw).digest('hex'),'2b895f84f77c8656811c4e732506926a677dda1eb6aa824f854670e127e8228b',fail+' authority');
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const portal='static/portal/portal.js',i18n='static/portal/portal-i18n.js',pages='copyfast_pages.py';
assert.equal(fixture.task,'ASSET-VAULT-CUSTOMER-COPY-20261119');assert.equal(fixture.base,'5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5');assert.equal(fixture.revision,'ROOT_REVIEWED_R1');
assert.equal(edits.length,12);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,90);assert.equal(new Set(keys).size,90);assert.ok(keys.every(key=>/^vault(?:Fields|Cards|Lifecycle|Page)Ui[A-Za-z]+$/.test(key)));
assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.revision,value.conversation,value.resultRawSha256]),[
 ['fields','R1','8f41e3c7-b8b9-49a1-8878-6d1c19621cbc','c409cfe329a0623774b96d8ac5c640af9e7e7dbef20b7c49850ba20b2ade6fce'],
 ['cards','R1','add5be17-f2ff-4c35-a31c-a979c3a07fa4','94d5e476ebc649fa4c0642ff197decf3a43ec1a847289d6398adef5acc1703bb'],
 ['lifecycle','R1','4eebac00-cba8-45e9-bf16-8061ee2acc77','1ca65e6382258e3b89cc8265a9b807c4777c3a499b79f9d3df5e27dd870d44b5'],
 ['page','R1','2567927b-81b9-4d85-bdcd-930ad91a266d','76d9f78486d1d4d1bd0fe1cb4c50497dd0656e69ebbee09b981493a5fcb78792']]);
assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.applicationWrites===0&&value.verify==='NOT_RUN'));assert.equal(fixture.applicationWrites,0);
const one=prefix=>{const selected=edits.filter(edit=>edit.file===portal&&edit.old.startsWith(prefix));assert.equal(selected.length,1,fail+' canonical owner');return selected[0];};
const prefix=one('  function renderAssetVault('),cards=one('    const cards ='),suffix=one('    const lifecyclePanel =');
// The three disjoint worker slices are contiguous and admitted only as one complete main owner.
const main={file:portal,count:1,old:prefix.old+cards.old+suffix.old,new:prefix.new+cards.new+suffix.new};
const nextOwners={assetVaultFilterFields:'  function assetVaultFilterIsActive(',renderAssetVaultPagination:'  function vaultBytes(',assetVaultLifecyclePanel:'  function assetVaultFormFields(',assetVaultFormFields:'  function operationAssetReferencePublic(',renderAssetVault:'  // Web Support Desk deliberately keeps its data model and language separate\n  // from Bot ticket compatibility.  The browser only receives an owner- or\n  // staff-scoped projection from `/api/v1/support/cases*`; it never reads the\n  // Telegram ticket history or pretends to deliver a notification elsewhere.\n  const SUPPORT_CASE_STATES = Object.freeze('};
const functions=Object.keys(nextOwners).map(name=>{const edit=name==='renderAssetVault'?main:one('  function '+name+'(');assert.ok(edit.new.startsWith('  function '+name+'('));assert.ok(edit.old.endsWith('  }\n\n')&&edit.new.endsWith('  }\n\n'));return{...edit,name,marker:'  function '+name+'('};});
const metadata=edits.filter(edit=>edit.file===portal&&edit.old.startsWith('    if (path === ')),shell=edits.filter(edit=>edit.file===pages),catalogue=edits.find(edit=>edit.file===i18n);
assert.equal(metadata.length,2);assert.equal(shell.length,2);assert.ok(catalogue);for(const edit of [...metadata,...shell])assert.ok(edit.new.endsWith(edit.old));
assert.equal(catalogue.old,'  verifyEqualKeysets();');assert.ok(catalogue.new.endsWith(catalogue.old));
const blocks=[...catalogue.new.matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);/g)];assert.deepEqual(blocks.map(match=>match[1]),['vi','en','zh']);
for(const[locale,index]of [['vi',1],['en',2],['zh',3]])assert.deepEqual(Object.entries(JSON.parse(blocks.find(match=>match[1]===locale)[2])),rows.map(row=>[row[0],row[index]]));
function bounds(source,marker,endMarker){const start=source.indexOf(marker),end=source.indexOf(endMarker,start+marker.length);assert.equal(count(source,marker),1,fail+' metadata owner');assert.ok(start>=0&&end>start,fail+' metadata bounds');return[start,end];}
function exactAddition(source,edit,start,end){const addition=edit.new.slice(0,-edit.old.length),point=source.indexOf(edit.new);assert.equal(count(source,edit.new),1,fail+' changed/partial/detached addition');assert.equal(count(source,addition),1,fail+' duplicate addition');assert.ok(point>start&&point+edit.new.length<=end,fail+' wrong addition owner');}
function catalogKeys(source){return[...source.matchAll(/Object\.assign\(MESSAGES\.(?:vi|en|zh),\s*\{([\s\S]*?)\}\);/g)].flatMap(match=>[...match[1].matchAll(/(?:^|,|\n)\s*(?:"(vault[^"]*)"|'(vault[^']*)'|(vault[A-Za-z0-9_]*))\s*:/g)].map(value=>value[1]||value[2]||value[3]));}
export function vaultCustomerHistoricalSource(source,file){
 assert.equal(typeof source,'string',fail);
 if(file===portal){
  if(!/\buiText\(["']vault/.test(source))return source;
  assert.ok(functions.every(edit=>count(source,edit.new)===1&&count(source,edit.old)===0),fail+' partial/mixed/changed complete function set');let previous=-1;
  for(const edit of functions){assert.equal(count(source,edit.marker),1,fail+' function owner');const point=source.indexOf(edit.new);assert.equal(point,source.indexOf(edit.marker),fail+' detached owner');assert.ok(point>previous,fail+' reordered owners');previous=point;assert.equal(count(source,nextOwners[edit.name]),1,fail+' next owner count');assert.ok(source.slice(point+edit.new.length).startsWith(nextOwners[edit.name]),fail+' immediate next owner');}
  const calls=text=>[...text.matchAll(/\buiText\(["'](vault[^"']*)["']/g)].map(match=>match[1]);assert.deepEqual(calls(source).sort(),[...functions,...metadata].flatMap(edit=>calls(edit.new)).sort(),fail+' unknown/duplicate/missing owned calls');
  for(const edit of metadata){const title=edit.old.includes('Title'),owner=title?'localizedPageTitle':'localizedPageDescription',end=title?'documentTitle':'initials';exactAddition(source,edit,...bounds(source,'  function '+owner+'(','  function '+end+'('));}
  let result=source;for(const edit of [...functions,...metadata].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 if(file===i18n){
  const found=catalogKeys(source),next=count(source,catalogue.new);if(!found.length){assert.equal(next,0,fail+' absent catalog');return source;}
  assert.equal(next,1,fail+' partial/changed/duplicate catalog');assert.equal(found.length,270,fail+' partial/unknown catalog');for(const key of keys)assert.equal(found.filter(value=>value===key).length,3,fail+' catalog key count');assert.ok(found.every(key=>keys.includes(key)),fail+' unknown prefixed key');
  const point=source.indexOf(catalogue.new),freeze='  deepFreeze(MESSAGES);';assert.equal(count(source,catalogue.old),1,fail+' keyset owner');assert.equal(count(source,freeze),1,fail+' freeze owner');assert.ok(point<source.indexOf(freeze),fail+' post-freeze catalog');assert.ok(source.slice(point+catalogue.new.length).startsWith('\n\n  function deepFreeze(value) {'),fail+' detached catalog');return source.replace(catalogue.new,()=>catalogue.old);
 }
 if(file===pages){
  const found=[...source.matchAll(/^    ["']\/asset-vault["']:\s*\{/gm)];if(!found.length)return source;assert.equal(found.length,2,fail+' partial/duplicate shell entries');let previous=-1;
  for(const edit of shell){const title=!edit.old.includes('\n'),[start,end]=title?bounds(source,'_PORTAL_SHELL_TITLES = {','\n_PORTAL_SHELL_DESCRIPTIONS = {'):bounds(source,'_PORTAL_SHELL_DESCRIPTIONS = {','\ndef _safe_portal_build_id(');exactAddition(source,edit,start,end);const point=source.indexOf(edit.new);assert.ok(point>previous,fail+' reordered shell entries');previous=point;}
  let result=source;for(const edit of [...shell].reverse())result=result.replace(edit.new,()=>edit.old);return result;
 }
 return source;
}
export function vaultCustomerHistoricalSnapshot(entries,locale){
 const index=['vi','en','zh'].indexOf(locale)+1;assert.ok(index>0,fail+' locale');assert.ok(Array.isArray(entries),fail+' entries');
 const owned=entries.filter(([key])=>typeof key==='string'&&key.startsWith('vault'));if(!owned.length)return entries;
 assert.deepEqual(owned,rows.map(row=>[row[0],row[index]]),fail+' partial/changed/unknown/duplicate/reordered catalog');return entries.filter(([key])=>!keys.includes(key));
}
