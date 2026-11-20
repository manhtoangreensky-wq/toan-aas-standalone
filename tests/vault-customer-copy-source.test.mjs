import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {vaultActionFeedbackHistoricalSource} from './helpers/vault-action-feedback-snapshot.mjs';
import {vaultHintContrastHistoricalCss} from './helpers/vault-hint-contrast-snapshot.mjs';
import {vaultCustomerHistoricalSource as inverse,vaultCustomerHistoricalSnapshot as snapshot} from './helpers/vault-customer-copy-snapshot.mjs';
import {documentOcrCustomerHistoricalSource as priorInverse,documentOcrCustomerHistoricalSnapshot as priorSnapshot} from './helpers/document-ocr-customer-copy-snapshot.mjs';
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),BASE='5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5';
const raw=fs.readFileSync(new URL('./fixtures/vault-customer-copy-reviewed.json',import.meta.url)),fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const fail=/Unreviewed Vault customer copy/,hash=x=>createHash('sha256').update(x).digest('hex'),lf=x=>x.replace(/\r\n/g,'\n'),count=(s,p)=>s.split(p).length-1;
const files=['static/portal/portal.js','static/portal/portal-i18n.js','copyfast_pages.py'];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6}))]));
const physical=Object.fromEntries(files.map(file=>[file,vaultActionFeedbackHistoricalSource(lf(fs.readFileSync(path.join(ROOT,file),'utf8')),file)]));
const candidate=Object.fromEntries(files.map(file=>{let source=before[file];for(const edit of edits.filter(row=>row.file===file)){assert.equal(count(source,edit.old),1);source=source.replace(edit.old,()=>edit.new);}return[file,source];}));
const prefix=edits.find(edit=>edit.old.startsWith('  function renderAssetVault(')),cards=edits.find(edit=>edit.old.startsWith('    const cards =')),suffix=edits.find(edit=>edit.old.startsWith('    const lifecyclePanel ='));
const main={file:files[0],old:prefix.old+cards.old+suffix.old,new:prefix.new+cards.new+suffix.new};
const functionNames=['assetVaultFilterFields','renderAssetVaultPagination','assetVaultLifecyclePanel','assetVaultFormFields','renderAssetVault'];
const functions=functionNames.map(name=>({...(name==='renderAssetVault'?main:edits.find(edit=>edit.old.startsWith('  function '+name+'('))),name}));
const metadata=edits.filter(edit=>edit.file===files[0]&&edit.old.startsWith('    if (path === ')),shell=edits.filter(edit=>edit.file===files[2]),catalogue=edits.find(edit=>edit.file===files[1]);
test('immutable four-worker R1 authority binds12exact changes90rows and no application or runtime-output claim',()=>{
 assert.equal(hash(raw),'2b895f84f77c8656811c4e732506926a677dda1eb6aa824f854670e127e8228b');assert.equal(fixture.task,'ASSET-VAULT-CUSTOMER-COPY-20261119');assert.equal(fixture.base,BASE);assert.equal(fixture.revision,'ROOT_REVIEWED_R1');assert.equal(edits.length,12);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,90);assert.equal(new Set(keys).size,90);
 assert.deepEqual(edits.reduce((out,edit)=>(out[edit.file]=(out[edit.file]||0)+1,out),{}),{[files[0]]:9,[files[2]]:2,[files[1]]:1});
 assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.specId,value.revision,value.conversation,value.packetSha256,value.resultRawSha256]),[
  ['fields','ASSET-VAULT-FIELDS-20261119','R1','8f41e3c7-b8b9-49a1-8878-6d1c19621cbc','8ab6865d2b4ed730143d40f564b977dd435d89be116676b506b6d429eb5c0c78','c409cfe329a0623774b96d8ac5c640af9e7e7dbef20b7c49850ba20b2ade6fce'],
  ['cards','ASSET-VAULT-CARDS-20261119','R1','add5be17-f2ff-4c35-a31c-a979c3a07fa4','a2c8e4b9ff1375b4ba71270c4f68a180409d7a1ca95fd6d00544b63a4d536c5c','94d5e476ebc649fa4c0642ff197decf3a43ec1a847289d6398adef5acc1703bb'],
  ['lifecycle','ASSET-VAULT-LIFECYCLE-20261119','R1','4eebac00-cba8-45e9-bf16-8061ee2acc77','517f21ed6686a846403785bcc2737ad7a2931f762874c205d0a622518a6d5f15','1ca65e6382258e3b89cc8265a9b807c4777c3a499b79f9d3df5e27dd870d44b5'],
  ['page','ASSET-VAULT-PAGE-20261119','R1','2567927b-81b9-4d85-bdcd-930ad91a266d','64493e4931fbd6c91c22ff9bba5203d6a1f284df1d26d676c99cc122e2711ed8','76d9f78486d1d4d1bd0fe1cb4c50497dd0656e69ebbee09b981493a5fcb78792']]);
 assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.verify==='NOT_RUN'&&value.applicationWrites===0));assert.equal(fixture.applicationWrites,0);assert.equal(fixture.engineRuntimeReadiness,'NOT_TESTED');assert.equal(fixture.finalOutput,'NOT_TESTED');
});
for(const file of files)test(file+': independent actual physical source equals BASE+12exact and inverse OLD/NEW/idempotence preserves outside bytes',()=>{
 assert.equal(physical[file],candidate[file],'Full actual source acceptance does not consume any inverse');const pin=fixture.applicationBaseline.find(row=>row.file===file);assert.equal(hash(before[file]),pin.baselineLfSha256);assert.equal(hash(physical[file]),pin.candidateLfSha256);
 assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);assert.equal(inverse(inverse(physical[file],file),file),before[file]);
 const first='\r\n/* CUSTOMER media studio provider Facebook TikTok <b>&</b> */\r\n',last='\r\n/* CUSTOMER Asset Vault lifecycle private original filename */\r\n';for(const source of [physical[file],before[file]])assert.equal(inverse(first+source+last,file),first+before[file]+last);
 assert.equal(inverse(first+last,file),first+last);assert.ok(inverse(physical[file]+last,file).endsWith(last));assert.notEqual(inverse(physical[file]+last,file),before[file]);assert.equal(inverse(physical[file],'customer/unrelated.txt'),physical[file]);
});
test('151actual current candidate pins preserve148protected files and exactly3changed sources without projection',()=>{
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(fixture.applicationBaseline.filter(row=>row.changed).length,3);for(const pin of fixture.applicationBaseline){assert.equal(hash(vaultHintContrastHistoricalCss(vaultActionFeedbackHistoricalSource(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')),pin.file),pin.file)),pin.candidateLfSha256,pin.file);assert.equal(pin.changed,pin.baselineLfSha256!==pin.candidateLfSha256);if(!files.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256);}
});
test('five complete Vault owners including contiguous main slices reject partial changed mixed duplicate detached reordered and next-owner faults',()=>{
 const file=files[0],current=candidate[file],nextOwners={assetVaultFilterFields:'  function assetVaultFilterIsActive(',renderAssetVaultPagination:'  function vaultBytes(',assetVaultLifecyclePanel:'  function assetVaultFormFields(',assetVaultFormFields:'  function operationAssetReferencePublic(',renderAssetVault:'  const SUPPORT_CASE_STATES = Object.freeze('};
 for(const edit of functions){assert.equal(count(current,edit.new),1);const next=nextOwners[edit.name];for(const malformed of [current.replace(edit.new,''),current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace('vault','vaultUNKNOWN')),current+'\n'+edit.new,current.replace(edit.new,'')+'\n'+edit.new,current.replace(next,next.replace(/assetVault|vaultBytes|operationAssetReferencePublic|SUPPORT_CASE_STATES/,'UNKNOWN_NEXT')),current.replace(edit.new,edit.new.replace('  function '+edit.name+'(','  function UNKNOWN_OWNER('))])assert.throws(()=>inverse(malformed,file),fail);}
 for(const edit of [prefix,cards,suffix])for(const malformed of [current.replace(edit.new,''),current.replace(edit.new,()=>edit.old),current+'\n'+edit.new])assert.throws(()=>inverse(malformed,file),fail);
 assert.throws(()=>inverse(current+'\nuiText("vaultUnknown.extra", "literal");',file),fail);
 const[a,b]=functions,marker='@@VAULT_OWNER_SWAP@@';assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);assert.throws(()=>inverse(current.replace(cards.new,'')+cards.new,file),fail);assert.equal(inverse('/* older unowned portal */',file),'/* older unowned portal */');
});
test('two exact JS metadata additions reject partial changed duplicate detached and wrong-owner source',()=>{
 const file=files[0],current=candidate[file];for(const edit of metadata){const extra=edit.new.slice(0,-edit.old.length);for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace('vaultPageUi','vaultPageUNKNOWN')),current+'\n'+edit.new,current.replace(edit.new,'')+'\n'+edit.new,current.replace(edit.new,extra+'\n/* detached */\n'+edit.old)])assert.throws(()=>inverse(malformed,file),fail);}
 for(const owner of ['localizedPageTitle','localizedPageDescription'])assert.throws(()=>inverse(current.replace('  function '+owner+'(','  function UNKNOWN_METADATA_OWNER('),file),fail);
});
test('two shell entries reject partial changed duplicate detached reordered and wrong dictionary ownership',()=>{
 const file=files[2],current=candidate[file];for(const edit of shell)for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace('/asset-vault','/asset-vault-UNKNOWN')),current+'\n'+edit.new,current.replace(edit.new,'')+'\n'+edit.new,current.replace(edit.new,edit.new.slice(0,-edit.old.length)+'\n# detached\n'+edit.old)])assert.throws(()=>inverse(malformed,file),fail);
 const[a,b]=shell,marker='@@VAULT_SHELL_SWAP@@';assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);for(const owner of ['_PORTAL_SHELL_TITLES = {','_PORTAL_SHELL_DESCRIPTIONS = {'])assert.throws(()=>inverse(current.replace(owner,'UNKNOWN_SHELL = {'),file),fail);
});
test('270exact catalog declarations reject partial unknown changed duplicate detached reordered post-keyset or post-freeze source',()=>{
 const file=files[1],current=candidate[file],chunk=catalogue.new.slice(0,-catalogue.old.length),first=rows[0][0],second=rows[1][0],marker='@@VAULT_KEY_SWAP@@';
 for(const malformed of [current.replace(chunk,chunk.replace('"'+first+'":','"vaultUNKNOWN":')),current.replace(chunk,chunk.replace(rows[0][1],'UNKNOWN_VALUE')),current+'\n'+catalogue.new,current.replace(chunk,'')+'\n'+chunk,current.replace(chunk,chunk.split('\n').reverse().join('\n')),current.replace(catalogue.new,catalogue.new+'\n/* detached */')])assert.throws(()=>inverse(malformed,file),fail);
 assert.throws(()=>inverse(current.replace('"'+first+'":',marker).replace('"'+second+'":','"'+first+'":').replace(marker,'"'+second+'":'),file),fail);assert.throws(()=>inverse(current.replace(chunk,chunk.replace(new RegExp('"'+first+'":"[^"]*",'),'')),file),fail);assert.equal(inverse(current.replace(chunk,''),file),before[file]);
 assert.throws(()=>inverse(current+'\nObject.assign(MESSAGES.vi, {"vaultUnknown.extra":"literal"});',file),fail);
});
for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){
 test(locale+': snapshot removes only90exact owned entries and preserves unrelated customer order values and identities',()=>{
  const first=Object.freeze(['CUSTOMER Facebook TikTok','media studio provider']),last=Object.freeze(['customer.vaultUnknown','literal <b>&</b>']),owned=rows.map(row=>Object.freeze([row[0],row[index]])),entries=Object.freeze([first,...owned,last]),prior=[first,last];assert.deepEqual(snapshot(entries,locale),prior);assert.strictEqual(snapshot(entries,locale)[0],first);assert.strictEqual(snapshot(entries,locale).at(-1),last);assert.strictEqual(snapshot(prior,locale),prior);assert.deepEqual(priorSnapshot(entries,locale),prior);
 });
 test(locale+': snapshot rejects partial changed duplicated reordered and unknown owned prefix keys',()=>{
  const owned=rows.map(row=>[row[0],row[index]]);for(const malformed of [owned.slice(1),owned.slice(0,-1),[...owned,owned[0]],owned.map((row,i)=>i===0?[row[0],'UNKNOWN']:row),[owned[1],owned[0],...owned.slice(2)],owned.map((row,i)=>i===0?[row[0]+'UNKNOWN',row[1]]:row),[...owned,['vaultUNKNOWN','literal']],[...owned,['vaultUnknown.extra','literal']]])assert.throws(()=>snapshot(malformed,locale),fail);
 });
}
test('original OCR type/locale guard identities precede the newest Vault leaf',()=>{
 assert.throws(()=>inverse(null,files[0]),fail);assert.throws(()=>snapshot([],'fr'),fail);assert.throws(()=>snapshot(null,'vi'),fail);assert.throws(()=>priorInverse(null,files[0]),/Unreviewed Document OCR customer copy/);assert.throws(()=>priorSnapshot([],'fr'),/Unreviewed Document OCR customer copy/);assert.throws(()=>priorSnapshot(null,'vi'),/Unreviewed Document OCR customer copy/);
});
test('marker-free OLD OCR malformed owner and next-owner source passes newest leaf and retains original OCR error',()=>{
 const file=files[0],legacy=before[file],ocr=JSON.parse(fs.readFileSync(new URL('./fixtures/document-ocr-customer-copy-reviewed.json',import.meta.url))),edit=ocr.canonicalChanges.find(row=>row.old.startsWith('  function imageOcrFormFields('));assert.ok(edit);
 for(const malformed of [legacy.replace(edit.new,''),legacy.replace('  function pdfToImagesFormFields(','  function UNKNOWN_PRIOR_NEXT(')]){assert.notEqual(malformed,legacy);assert.doesNotMatch(malformed,/\buiText\(["']vault/);assert.equal(inverse(malformed,file),malformed);assert.throws(()=>priorInverse(malformed,file),/Unreviewed Document OCR customer copy/);}
});
test('actual complete locale dictionaries initialize90reviewed values before freeze and retain equal keysets',()=>{
 const document={title:'',documentElement:{lang:'vi',setAttribute(){}}},window={document,navigator:{language:'vi'},dispatchEvent(){},CustomEvent:function(){}};vm.runInContext(physical[files[1]],vm.createContext({window,document,Intl,Date,Number,String,Object,Array,Set,Map,Math,RegExp}));const messages=window.TOANAASI18n.messages;
 for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){assert.equal(Object.isFrozen(messages[locale]),true);for(const row of rows)assert.equal(messages[locale][row[0]],row[index]);}assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.en).sort());assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.zh).sort());
});
