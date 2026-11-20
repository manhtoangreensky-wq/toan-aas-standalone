import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {sharedSelectLabelsHistoricalSource} from './helpers/shared-select-labels-snapshot.mjs';
import {vaultActionFeedbackHistoricalSource as inverse,vaultActionFeedbackHistoricalSnapshot as snapshot} from './helpers/vault-action-feedback-snapshot.mjs';
import {vaultCustomerHistoricalSource as priorInverse,vaultCustomerHistoricalSnapshot as priorSnapshot} from './helpers/vault-customer-copy-snapshot.mjs';

Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),BASE='e49427e5e35378c0fc8b41d68b772af88501f556';
const raw=fs.readFileSync(new URL('./fixtures/vault-action-feedback-reviewed.json',import.meta.url)),fixture=JSON.parse(raw);
const edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const fail=/Unreviewed Vault action feedback/,hash=value=>createHash('sha256').update(value).digest('hex'),lf=value=>value.replace(/\r\n/g,'\n'),count=(source,part)=>source.split(part).length-1;
const integration='static/portal/integration.js',i18n='static/portal/portal-i18n.js',files=[integration,i18n];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6}))]));
// V07 is now historical: only the newer approved shared-select leaf normalizes inputs; its newest suite reads full physical sources.
const physical=Object.fromEntries(files.map(file=>[file,sharedSelectLabelsHistoricalSource(lf(fs.readFileSync(path.join(ROOT,file),'utf8')),file)]));
const candidate=Object.fromEntries(files.map(file=>{
 let source=before[file];
 for(const edit of edits.filter(value=>value.file===file)){
  assert.equal(count(source,edit.old),edit.count);
  for(let at=0;at<edit.count;at++)source=source.replace(edit.old,()=>edit.new);
 }
 return[file,source];
}));
const integrationEdits=edits.filter(edit=>edit.file===integration),catalogue=edits.find(edit=>edit.file===i18n);
const helper=integrationEdits.find(edit=>edit.new.startsWith('  function vaultFeedbackText('));
const chunk=catalogue.new.slice(0,-catalogue.old.length);

test('immutable exact R1 authority binds34records36sites35keys105values and four reviewed workers',()=>{
 assert.equal(hash(raw),'488924a1ee5bcd7b49b53a4a366ba6a4e31f4df2eca0e518af8af9163e9c4801');
 assert.equal(fixture.task,'VAULT-ACTION-FEEDBACK-20261120');assert.equal(fixture.base,BASE);assert.equal(fixture.revision,'ROOT_REVIEWED_EXACT_R1');
 assert.equal(edits.length,34);assert.equal(edits.reduce((sum,edit)=>sum+edit.count,0),36);
 assert.equal(rows.length,35);assert.equal(new Set(keys).size,35);
 assert.ok(rows.every(row=>row.length===4&&/^vaultFeedback\.[A-Za-z]+$/.test(row[0])&&row.slice(1).every(value=>typeof value==='string'&&value.length>0)));
 assert.equal(rows.flatMap(row=>row.slice(1)).length,105);
 assert.deepEqual(edits.reduce((out,edit)=>(out[edit.file]=(out[edit.file]||0)+1,out),{}),{[integration]:33,[i18n]:1});
 assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.lane,value.model,value.resultRawSha256,value.expectedSha256,value.packetSha256,value.schemaSha256,value.records,value.replacementSites]),[
  ['read','gemini-3.8-flash-high','6e24c3f9bc2809e2c42d4a2d3c78e015c1495ed1506c5317a2979caf43bc995d','073a4dcbd6d6750cec01818a3006e48c8f85c8d0c021dfab2a8a26db69edf871','14ede2c29d3401d5500bba4d800ba8e5a5ad3f8d648ea53714b6d89558140988','5cdce52bf1050dde0c492ed8c0d055c91c867dd61d35573dedfb7504421c8ce7',3,3],
  ['readcopy','gemini-3.8-flash-high','27591c787b09d7ca07f804956fa88886001de1ccaeed51834f8be1b254a74389','3a57e5c95ee8260006f418a2863561980a61da1ba739e8aaeff628a2aaeb97fb','5a0e63cc91af19d0d4b7ac4c36c148efea84bc28b824a276ca192c7bacd48043','27a9b5227b47304698c5e991bef5df823177f4608b2058469326730b42606015',10,11],
  ['writecopy','gemini-3.8-flash-high','a106c5a5937bdb58a9171f682df8d953420f2e04d44803da83abc8ee15f4054d','7bf8df2bf50e7bb57f523708f718dd41868944bd75da5f630abd90e4c9e0ec33','1091d500a757e89e28222a98213404329cc2c6f07de75e4394dbd53c0152c92a','2490a25be948a4309453d0e933cc6ea6457b3e11f546c6a5b6df09b9efeece61',19,20],
  ['catalogue','gemini-3.8-flash-high','b7bf7dda5553c8fc6cff8fc191d866463d1de59168505faba8d01aa1e84b626b','8c932c54d930a47f507ffc17d0be5489bc75bc481f322ef83335536dc92d57ec','6c59d72c96ec049f770d4a8100ee0d9695b13fdfa433dfe814031a9078fe11d7','5285848802fd618e86ab0a74dc1217ce1b2e42e2be5cecd443b81bc04e0acf3d',2,2]
 ]);
 assert.ok(fixture.sourceAuthorities.every(value=>value.proposalExact&&value.applicationWrites===0&&value.workerVerify==='NOT_RUN'&&value.runtimeAcceptance==='NOT_YET_VERIFIED'));
 assert.equal(fixture.providerCalls,0);assert.equal(fixture.walletMutations,0);assert.equal(fixture.productionDataMutations,0);assert.equal(fixture.ownerCampaignStateOpened,false);
});

for(const file of files)test(file+': full physical source equals GitBASE+34finite edits and inverse preserves OLD NEW idempotence and outside bytes',()=>{
 assert.equal(physical[file],candidate[file],'Full physical acceptance must never consume a historical inverse');
 const pin=fixture.applicationBaseline.find(value=>value.file===file);
 assert.equal(hash(before[file]),pin.baselineLfSha256);assert.equal(hash(physical[file]),pin.candidateLfSha256);
 assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);assert.equal(inverse(inverse(physical[file],file),file),before[file]);
 const prefix='\r\n/* CUSTOMER Facebook TikTok media provider <b>&</b> */\r\nconst customerLabel = "vaultFeedback.customer label";\r\n',suffix='\r\n/* CUSTOMER Asset Vault private lifecycle original filename */\r\n';
 for(const source of [physical[file],before[file]])assert.equal(inverse(prefix+source+suffix,file),prefix+before[file]+suffix);
 assert.equal(inverse(prefix+suffix,file),prefix+suffix);assert.equal(inverse(physical[file],'customer/unrelated.txt'),physical[file]);
 assert.notEqual(inverse(physical[file]+suffix,file),before[file]);assert.ok(inverse(physical[file]+suffix,file).endsWith(suffix));
});

test('151full physical application pins protect149unchanged sources and exactly2reviewed source changes',()=>{
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(fixture.applicationBaseline.filter(pin=>pin.changed).length,2);
 assert.equal(fixture.applicationBaseline.filter(pin=>!pin.changed).length,149);
 for(const pin of fixture.applicationBaseline){
  const actual=sharedSelectLabelsHistoricalSource(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')),pin.file);
  assert.equal(hash(actual),pin.candidateLfSha256,pin.file);
  assert.equal(pin.changed,pin.baselineLfSha256!==pin.candidateLfSha256);
  if(!files.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256,pin.file);
 }
});

test('every integration record rejects partial mixed changed duplicate and detached exact fragments',()=>{
 const current=candidate[integration];
 for(const edit of integrationEdits){
  for(const malformed of [
   current.replace(edit.new,()=>edit.old),
   current.replace(edit.new,edit.new.replace('vaultFeedbackText','vaultFeedbackUNKNOWN')),
   current+'\n'+edit.new,
   current.replace(edit.new,'')+'\n'+edit.new
  ])assert.throws(()=>inverse(malformed,integration),fail);
 }
 assert.throws(()=>inverse(helper.new,integration),fail,'A detached helper is not a complete reviewed source');
});

test('integration owner and helper adjacency guards reject unknown calls keys and displaced owners',()=>{
 const current=candidate[integration];
 for(const marker of ['  function assetVaultFilterPayload(','  function assetVaultListOffset(','  async function hydrateAssetVaultLifecycle(','  async function hydrateDocumentAssetReferences(','  async function handleAction(','  function synchronizeScriptToScreenEpisodeFields(']){
  assert.throws(()=>inverse(current.replace(marker,marker.replace(/function \w+/,'function UNKNOWN_OWNER')),integration),fail);
 }
 for(const addition of [
  '\nvaultFeedbackText("unknown", "CUSTOMER <b>&</b>");',
  '\nvaultFeedbackUNKNOWN("unknown", "literal");',
  '\ni18n.t("vaultFeedback.unknown");',
  '\nvaultFeedbackText("uploaded", "Đã lưu tệp vào kho tệp.");'
 ])assert.throws(()=>inverse(current+addition,integration),fail);
 assert.throws(()=>inverse(current.replace(helper.new,helper.new.replace('\n\n  function assetVaultFilterPayload','\n/* detached */\n  function assetVaultFilterPayload')),integration),fail);
 const lifecycle=integrationEdits.find(edit=>edit.old.startsWith('      if (!lifecycle) throw new Error('));
 const displaced=current.replace(lifecycle.new,'').replace('  async function handleAction(event) {',lifecycle.new+'\n  async function handleAction(event) {');
 assert.throws(()=>inverse(displaced,integration),fail,'A known fragment outside its lifecycle owner must not be stripped');
});

test('catalogue requires all105exact declarations in order immediately at equal-keyset verification before freeze',()=>{
 const current=candidate[i18n],first=rows[0][0],second=rows[1][0],marker='@@VAULT_FEEDBACK_SWAP@@';
 for(const malformed of [
  current.replace(chunk,chunk.replace('"'+first+'":','"vaultFeedback.UNKNOWN":')),
  current.replace(chunk,chunk.replace(rows[0][1],'UNKNOWN_VALUE')),
  current+'\n'+catalogue.new,
  current.replace(chunk,'')+'\n'+chunk,
  current.replace(chunk,chunk.split('\n').reverse().join('\n')),
  current.replace(catalogue.new,catalogue.new+'\n/* detached */'),
  current.replace(chunk,chunk.replace(new RegExp('"'+first+'":"[^"]*",'),'')),
  current.replace('"'+first+'":',marker).replace('"'+second+'":','"'+first+'":').replace(marker,'"'+second+'":'),
  current.replace(chunk,'').replace('  deepFreeze(MESSAGES);','  deepFreeze(MESSAGES);\n'+chunk),
  current+'\nObject.assign(MESSAGES.vi, {"vaultFeedback.unknown":"literal"});',
  current+'\nObject.assign(MESSAGES.vi, {vaultFeedbackUNKNOWN:"literal"});',
  current+'\nMESSAGES.vi["vaultFeedback.unknown"] = "literal";',
  current+'\nvaultFeedbackText("unknown", "literal");'
 ])assert.throws(()=>inverse(malformed,i18n),fail);
 assert.equal(inverse(current.replace(chunk,''),i18n),before[i18n],'Entire absent new block is OLD');
});

for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){
 test(locale+': snapshot strips only35exact reviewed rows preserving all unrelated order values and identities',()=>{
  const first=Object.freeze(['CUSTOMER Facebook TikTok','literal <b>&</b>']),last=Object.freeze(['customer.vaultFeedback.unknown','Asset Vault private metadata']);
  const owned=rows.map(row=>Object.freeze([row[0],row[index]])),entries=Object.freeze([first,...owned,last]),prior=[first,last];
  const actual=snapshot(entries,locale);
  assert.deepEqual(actual,prior);assert.strictEqual(actual[0],first);assert.strictEqual(actual.at(-1),last);assert.strictEqual(snapshot(prior,locale),prior);
  assert.deepEqual(priorSnapshot(entries,locale),prior);
 });
 test(locale+': snapshot rejects partial changed duplicate reordered unknown and wrong-locale rows',()=>{
  const owned=rows.map(row=>[row[0],row[index]]);
  for(const malformed of [
   owned.slice(1),owned.slice(0,-1),[...owned,owned[0]],
   owned.map((entry,at)=>at===0?[entry[0],'UNKNOWN']:entry),
   [owned[1],owned[0],...owned.slice(2)],
   owned.map((entry,at)=>at===0?[entry[0]+'UNKNOWN',entry[1]]:entry),
   [...owned,['vaultFeedback.unknown','literal']],
   [...owned,['vaultFeedbackUNKNOWN','literal']],
   rows.map(row=>[row[0],row[index===1?2:1]])
  ])assert.throws(()=>snapshot(malformed,locale),fail);
 });
}

test('new strict source locale and array guards preserve old wrapper failure identities first',()=>{
 assert.throws(()=>inverse(null,integration),fail);assert.throws(()=>inverse(3,'customer/unrelated.txt'),fail);
 assert.throws(()=>snapshot([],'fr'),fail);assert.throws(()=>snapshot(null,'vi'),fail);assert.throws(()=>snapshot({},'vi'),fail);
 assert.throws(()=>priorInverse(null,integration),/Unreviewed Vault customer copy/);
 assert.throws(()=>priorSnapshot([],'fr'),/Unreviewed Vault customer copy/);
 assert.throws(()=>priorSnapshot(null,'vi'),/Unreviewed Vault customer copy/);
 const old=before[i18n],priorFixture=JSON.parse(fs.readFileSync(new URL('./fixtures/vault-customer-copy-reviewed.json',import.meta.url)));
 const priorCatalogue=priorFixture.canonicalChanges.find(edit=>edit.file===i18n);
 const malformed=old.replace(priorCatalogue.new,priorCatalogue.new.replace(priorFixture.rows[0][1],'UNKNOWN_PRIOR_VALUE'));
 assert.notEqual(malformed,old);assert.equal(inverse(malformed,i18n),malformed);
 assert.throws(()=>priorInverse(malformed,i18n),/Unreviewed Vault customer copy/);
});

test('full physical catalogue initializes35reviewed values in every frozen locale with equal keysets',()=>{
 const document={title:'',documentElement:{lang:'vi',setAttribute(){}}},window={document,navigator:{language:'vi'},dispatchEvent(){},CustomEvent:function(){}};
 vm.runInContext(physical[i18n],vm.createContext({window,document,Intl,Date,Number,String,Object,Array,Set,Map,Math,RegExp}));
 const messages=window.TOANAASI18n.messages;
 for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){
  assert.equal(Object.isFrozen(messages[locale]),true);
  assert.deepEqual(Object.entries(messages[locale]).filter(([key])=>key.startsWith('vaultFeedback')),rows.map(row=>[row[0],row[index]]));
 }
 assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.en).sort());assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.zh).sort());
 assert.ok(physical[i18n].indexOf(catalogue.new)<physical[i18n].indexOf('  deepFreeze(MESSAGES);'));
});
