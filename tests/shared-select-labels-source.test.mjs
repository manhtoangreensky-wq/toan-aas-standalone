import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {sharedSelectReminderTitleHistoricalSource} from './helpers/shared-select-reminder-title-snapshot.mjs';
import {sharedSelectLabelsHistoricalSource as inverse,sharedSelectLabelsHistoricalSnapshot as snapshot} from './helpers/shared-select-labels-snapshot.mjs';
import {vaultActionFeedbackHistoricalSource as priorInverse,vaultActionFeedbackHistoricalSnapshot as priorSnapshot} from './helpers/vault-action-feedback-snapshot.mjs';

Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),BASE='46423a6df9af67ac7ccabd88686d4cb42523a078';
const raw=fs.readFileSync(new URL('./fixtures/shared-select-labels-reviewed.json',import.meta.url)),fixture=JSON.parse(raw);
const edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const fail=/Unreviewed Shared select labels/,hash=value=>createHash('sha256').update(value).digest('hex'),lf=value=>value.replace(/\r\n/g,'\n'),count=(source,part)=>source.split(part).length-1;
const portal='static/portal/portal.js',i18n='static/portal/portal-i18n.js',files=[portal,i18n];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6}))]));
// Parent shared-select source comparison normalizes only the newer finite title
// prerequisite. Its separate newest source suite reads all physical bytes.
const physical=Object.fromEntries(files.map(file=>[file,sharedSelectReminderTitleHistoricalSource(lf(fs.readFileSync(path.join(ROOT,file),'utf8')),file)]));
const candidate=Object.fromEntries(files.map(file=>{
 let source=before[file];
 for(const edit of edits.filter(value=>value.file===file)){
  assert.equal(count(source,edit.old),1);source=source.replace(edit.old,()=>edit.new);
 }
 return[file,source];
}));
const expressions=edits.filter(edit=>edit.file===portal),catalogue=edits.find(edit=>edit.file===i18n),chunk=catalogue.new.slice(0,-catalogue.old.length);
const owner='  function renderFields(fields, enabled, context, fieldValues, idNamespace) {',nextOwner='  function statusMessage(page, status, context) {';

test('immutable three-worker R1A transport authority binds4records4keys12values and151source pins',()=>{
 assert.equal(hash(raw),'7cb67db3464cb45d3e0b243f388affb981fd4f5780e0ebb28105865885786817');
 assert.equal(fixture.task,'SHARED-SELECT-LABELS-20261120');assert.equal(fixture.base,BASE);assert.equal(fixture.revision,'ROOT_REVIEWED_EXACT_R1A_TRANSPORT_ONLY');
 assert.equal(edits.length,4);assert.ok(edits.every(edit=>edit.count===1));assert.equal(expressions.length,3);
 assert.deepEqual(edits.map(edit=>edit.file),[portal,portal,portal,i18n]);
 assert.deepEqual(rows,[
  ['sharedSelect.projectFallback','Dự án chưa đặt tên','Untitled project','未命名项目'],
  ['sharedSelect.noteFallback','Ghi chú chưa đặt tên','Untitled note','未命名笔记'],
  ['sharedSelect.voiceFallback','Giọng chưa đặt tên','Unnamed voice','未命名声音'],
  ['sharedSelect.voiceDefaultSuffix',' · Mặc định',' · Default',' · 默认']
 ]);
 assert.equal(new Set(keys).size,4);assert.equal(rows.flatMap(row=>row.slice(1)).length,12);
 assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.lane,value.model,value.transportRevision,value.resultRawSha256,value.packetSha256,value.schemaSha256,value.expectedSha256,value.records]),[
  ['projectnote','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','a4e2426f299641fc3dd31efd710d3b715e168e8070eae03832fffc78004a0078','09e1a3d2a96f17b1177ea4e68b65a1670d39a2f416d17f2687b6072acbca32cc','5285848802fd618e86ab0a74dc1217ce1b2e42e2be5cecd443b81bc04e0acf3d','a9dabbebf6c8e8752a2762a4c597e47b48a2a5018032aacf802441263f6da33f',2],
  ['voice','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','5bfd36db7979dafc89cd88f8d8c266ebd6aa513c8ff33799fbc5acb26cf4337e','32b695190ee816f69435cf85b73f985ebc7642362379f9c165f2244c001e551f','f7d0a54dc3666a8f1c7011e544d050398de509a466c1227d393e930333c99bc1','9089c8b8ffd08e1ba3346dd1ffd60b4bcee09db209a42c7359541b6b10f2e751',1],
  ['catalogue','gemini-3.8-flash-high','R1A_SCHEMA_ONLY','05c14c5b7874ff7507ac4675949f448ed1669cc12e54dc450d0ca0ba4a386f8a','e3b7b4c373bdb650a28ab428c2d5afe408f7c74ce967a3b709c45dc99d703448','f7d0a54dc3666a8f1c7011e544d050398de509a466c1227d393e930333c99bc1','18a125cea1e619aa16ab66dfda1081a4a0eecf1ebe982eeac79239fdaa3b4da7',1]
 ]);
 assert.ok(fixture.sourceAuthorities.every(value=>value.proposalExact&&value.workerVerify==='NOT_RUN'&&value.applicationWrites===0&&value.workerCodeFailures===0));
 assert.equal(fixture.applicationWrites,0);assert.equal(fixture.providerCalls,0);assert.equal(fixture.walletMutations,0);assert.equal(fixture.productionDataMutations,0);assert.equal(fixture.ownerCampaignStateOpened,false);
});

for(const file of files)test(file+': whole physical source equals GitBASE plus4exact records while finite inverse preserves OLD NEW and all outside bytes',()=>{
 assert.equal(physical[file],candidate[file],'Current acceptance may not consume the historical inverse');
 const pin=fixture.applicationBaseline.find(value=>value.file===file);
 assert.equal(hash(before[file]),pin.baselineLfSha256);assert.equal(hash(physical[file]),pin.candidateLfSha256);
 assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);
 assert.equal(inverse(inverse(physical[file],file),file),before[file]);
 const prefix='\r\n/* CUSTOMER Facebook TikTok <b>&</b> */\r\nconst customerLabel = "sharedSelect.customer text";\r\n',suffix='\r\n/* CUSTOMER original name and whitespace are untouched */\r\n';
 for(const source of [before[file],physical[file]])assert.equal(inverse(prefix+source+suffix,file),prefix+before[file]+suffix);
 assert.equal(inverse(prefix+suffix,file),prefix+suffix);assert.equal(inverse(physical[file],'customer/unrelated.txt'),physical[file]);
 assert.notEqual(inverse(physical[file]+suffix,file),before[file]);assert.ok(inverse(physical[file]+suffix,file).endsWith(suffix));
});

test('151physical application hashes require exactly2reviewed files and149protected sources without projection',()=>{
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(new Set(fixture.applicationBaseline.map(pin=>pin.file)).size,151);
 assert.deepEqual(fixture.applicationBaseline.filter(pin=>pin.changed).map(pin=>pin.file).sort(),[portal,i18n].sort());
 assert.equal(fixture.applicationBaseline.filter(pin=>!pin.changed).length,149);
 for(const pin of fixture.applicationBaseline){
  assert.equal(hash(sharedSelectReminderTitleHistoricalSource(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')),pin.file)),pin.candidateLfSha256,pin.file);
  assert.equal(pin.changed,pin.baselineLfSha256!==pin.candidateLfSha256);
  if(!files.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256,pin.file);
 }
});

test('each reviewed selector expression rejects missing mixed changed duplicate detached or displaced source',()=>{
 const current=candidate[portal];
 for(const edit of expressions){
  for(const malformed of [
   current.replace(edit.new,''),
   current.replace(edit.new,()=>edit.old),
   current.replace(edit.new,edit.new.replace('uiText(','uiTextUNKNOWN(')),
   current+'\n'+edit.new,
   current.replace(edit.new,'')+'\n'+edit.new,
   current.replace(edit.new,'').replace(owner,edit.new+'\n'+owner),
   current.replace(edit.new,'').replace(nextOwner,nextOwner+'\n'+edit.new)
  ])assert.throws(()=>inverse(malformed,portal),fail);
  assert.throws(()=>inverse(edit.new,portal),fail,'A detached reviewed expression is not a complete renderFields owner');
  assert.throws(()=>inverse(before[portal].replace(edit.old,()=>edit.new),portal),fail,'One NEW expression cannot admit a mixed set');
 }
});

test('complete renderFields boundary order and owned key allowlist cannot be bypassed',()=>{
 const current=candidate[portal],a=expressions[0],b=expressions[1],marker='@@SHARED_SELECT_SWAP@@';
 for(const malformed of [
  current.replace(owner,owner.replace('renderFields','UNKNOWN_OWNER')),
  current.replace(nextOwner,nextOwner.replace('statusMessage','UNKNOWN_NEXT')),
  current.replace('    }).join("")}</div>`;\n  }\n\n'+nextOwner,'    }).join("")}</div>`;\n  /* missing owner close */\n\n'+nextOwner),
  current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),
  current+'\nuiText("sharedSelect.unknown", "literal");',
  current+'\nuiText("sharedSelect.projectFallback", "Dự án chưa đặt tên");',
  current+'\nsharedSelectUnknown("literal");',
  current+'\ni18n.t("sharedSelect.unknown");',
  current+'\nMESSAGES.vi["sharedSelect.unknown"] = "literal";',
  current+'\nObject.assign(MESSAGES.vi, {sharedSelectUNKNOWN:"literal"});'
 ])assert.throws(()=>inverse(malformed,portal),fail);
});

test('the whole catalogue block rejects partial changed duplicate reordered unknown detached or post-freeze input',()=>{
 const current=candidate[i18n],first=keys[0],second=keys[1],marker='@@SHARED_SELECT_KEY_SWAP@@';
 for(const malformed of [
  current.replace(chunk,chunk.replace('"'+first+'":','"sharedSelect.unknown":')),
  current.replace(chunk,chunk.replace(rows[0][1],'UNKNOWN_VALUE')),
  current.replace(chunk,chunk.replace(new RegExp('"'+first+'":"[^"]*",'),'')),
  current+'\n'+catalogue.new,
  current.replace(chunk,'')+'\n'+chunk,
  current.replace(chunk,chunk.split('\n').reverse().join('\n')),
  current.replace(catalogue.new,catalogue.new+'\n/* detached */'),
  current.replace('"'+first+'":',marker).replace('"'+second+'":','"'+first+'":').replace(marker,'"'+second+'":'),
  current.replace(chunk,'').replace('  deepFreeze(MESSAGES);','  deepFreeze(MESSAGES);\n'+chunk),
  current.replace('  verifyEqualKeysets();','  verifyEqualKeysets();\n  verifyEqualKeysets();'),
  current+'\nObject.assign(MESSAGES.en, {"sharedSelect.unknown":"literal"});',
  current+'\nObject.assign(MESSAGES.vi, {sharedSelectUNKNOWN:"literal"});',
  current+'\nMESSAGES.vi["sharedSelect.unknown"] = "literal";',
  current+'\nuiText("sharedSelect.unknown", "literal");',
  current+'\nsharedSelectUnknown("literal");'
 ])assert.throws(()=>inverse(malformed,i18n),fail);
 assert.equal(inverse(current.replace(chunk,''),i18n),before[i18n],'The entire absent addition is legitimate OLD source');
 assert.throws(()=>inverse(catalogue.new,i18n),fail,'A detached catalogue lacks its complete verification/freeze owner');
});

for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){
 test(locale+': finite snapshot removes only4exact rows preserving unrelated order values and entry identities',()=>{
  const first=Object.freeze(['CUSTOMER Facebook TikTok','literal <b>&</b>']),middle=Object.freeze(['customer.sharedSelect','do not translate']),last=Object.freeze([42,'literal numeric customer key']);
  const owned=rows.map(row=>Object.freeze([row[0],row[index]])),entries=Object.freeze([first,...owned.slice(0,2),middle,...owned.slice(2),last]),prior=[first,middle,last];
  const actual=snapshot(entries,locale);
  assert.deepEqual(actual,prior);for(let at=0;at<prior.length;at++)assert.strictEqual(actual[at],prior[at]);
  assert.strictEqual(snapshot(prior,locale),prior);assert.deepEqual(priorSnapshot(entries,locale),prior);
 });
 test(locale+': snapshot rejects missing changed duplicate reordered unknown and wrong-locale rows',()=>{
  const owned=rows.map(row=>[row[0],row[index]]);
  for(const malformed of [
   owned.slice(1),owned.slice(0,-1),[...owned,owned[0]],
   owned.map((entry,at)=>at===0?[entry[0],'UNKNOWN']:entry),
   [owned[1],owned[0],...owned.slice(2)],
   [...owned,['sharedSelect.unknown','literal']],
   [...owned,['sharedSelectUNKNOWN','literal']],
   rows.map(row=>[row[0],row[index===1?2:1]])
  ])assert.throws(()=>snapshot(malformed,locale),fail);
 });
}

test('strict guards precede composition and retain the prior Vault error identities',()=>{
 for(const value of [null,undefined,17,{},[]])assert.throws(()=>inverse(value,portal),fail);
 assert.throws(()=>inverse(null,'customer/unrelated.txt'),fail);
 for(const locale of ['fr','',null,undefined,1,{}])assert.throws(()=>snapshot([],locale),fail);
 for(const entries of [null,undefined,17,{},[null],[['key']]])assert.throws(()=>snapshot(entries,'vi'),fail);
 assert.throws(()=>priorInverse(null,portal),/Unreviewed Vault action feedback/);
 assert.throws(()=>priorSnapshot([],'fr'),/Unreviewed Vault action feedback/);
 assert.throws(()=>priorSnapshot(null,'vi'),/Unreviewed Vault action feedback/);
 assert.equal(priorInverse(physical[portal],portal),before[portal],'The prior file guard runs only after the newest portal leaf');
 const oldFixture=JSON.parse(fs.readFileSync(new URL('./fixtures/vault-action-feedback-reviewed.json',import.meta.url)));
 const oldCatalogue=oldFixture.canonicalChanges.find(edit=>edit.file===i18n),legacy=before[i18n].replace(oldCatalogue.new,()=>oldCatalogue.old);
 assert.equal(count(before[i18n],oldCatalogue.new),1);assert.equal(priorInverse(physical[i18n],i18n),legacy);
 const malformed=before[i18n].replace(oldCatalogue.new,oldCatalogue.new.replace(oldFixture.rows[0][1],'UNKNOWN_PRIOR_VALUE'));
 assert.notEqual(malformed,before[i18n]);assert.equal(inverse(malformed,i18n),malformed);
 assert.throws(()=>priorInverse(malformed,i18n),/Unreviewed Vault action feedback/);
});

test('actual full catalogue initializes all4new keys12values before freezing equal VI EN ZH dictionaries',()=>{
 const document={title:'',documentElement:{lang:'vi',setAttribute(){}}},window={document,navigator:{language:'vi'},dispatchEvent(){},CustomEvent:function(){}};
 vm.runInContext(physical[i18n],vm.createContext({window,document,Intl,Date,Number,String,Object,Array,Set,Map,Math,RegExp}));
 const messages=window.TOANAASI18n.messages;
 for(const[locale,index]of [['vi',1],['en',2],['zh',3]]){
  assert.equal(Object.isFrozen(messages[locale]),true);
  assert.deepEqual(Object.entries(messages[locale]).filter(([key])=>key.startsWith('sharedSelect')),rows.map(row=>[row[0],row[index]]));
 }
 assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.en).sort());assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.zh).sort());
 assert.ok(physical[i18n].indexOf(catalogue.new)<physical[i18n].indexOf('  deepFreeze(MESSAGES);'));
});
