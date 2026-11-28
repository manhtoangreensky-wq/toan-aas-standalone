import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {documentNaturalHistoricalSource} from './helpers/document-natural-copy-historical.mjs';
import {galleryNativeHistoricalSource as inverse,galleryNativeHistoricalSnapshot as snapshot} from './helpers/gallery-native-historical.mjs';
import {adminGuardCustomerCopyHistoricalSource} from './helpers/admin-guard-customer-copy-historical.mjs';

const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/gallery-native-history.json',import.meta.url),'utf8'));
const base='29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef',portal='static/portal/portal.js',i18n='static/portal/portal-i18n.js';
const files=[portal,i18n],lf=value=>value.replace(/\r\n/g,'\n');
const hash=value=>createHash('sha256').update(value).digest('hex');
const baseline=new Map(files.map(file=>[file,lf(execFileSync('git',['show',base+':'+file],{encoding:'utf8',maxBuffer:10000000}))]));
const current=new Map(files.map(file=>{
  let source=baseline.get(file);
  for(const row of fixture.records.filter(row=>row.file===file)){
    assert.equal(source.split(row.before).length,2,'Proposal must have one real BASE anchor');
    source=source.replace(row.before,()=>row.after);
  }
  return[file,source];
}));
const part=row=>row.file===i18n?row.after.slice(0,-row.before.length):row.after;
const reject=(source,file)=>assert.throws(()=>inverse(source,file),/Unreviewed Gallery native history/);
const combine=fixture.records[2].after.replace(fixture.records[4].before,()=>fixture.records[4].after);

for(const file of files){
  test(file+': independently read git BASE is a byte-exact no-op',()=>{
    const source=baseline.get(file);assert.equal(inverse(source,file),source);
  });
  test(file+': exact five-edit construction reverses to independently read git BASE',()=>{
    assert.ok(inverse(current.get(file),file)===baseline.get(file),'Inverse did not restore git BASE bytes');
  });
  test(file+': current raw app matches exactly five owned edits, not an expanded mask',()=>{
    const source=adminGuardCustomerCopyHistoricalSource(documentNaturalHistoricalSource(lf(fs.readFileSync(new URL('../'+file,import.meta.url),'utf8')),file),file);
    const metadata=fixture.application_sources.find(row=>row.file===file);
    assert.equal(hash(source),metadata.five_edit_lf_sha256);
    assert.ok(inverse(source,file)===baseline.get(file));
  });
  test(file+': arbitrary prefix/suffix including unknown fake-prefix labels survive unchanged',()=>{
    const prefix='/* UNKNOWN α\\r\\n freePromptGallery.taxonomy.fake */\r\n';
    const suffix='\n/* unrelated feedback.custom="客户自有文字" */\r\n';
    assert.ok(inverse(prefix+current.get(file)+suffix,file)===prefix+baseline.get(file)+suffix);
  });
  test(file+': unrelated interior delta remains visible to the historical pin',()=>{
    const source=current.get(file).replace('  "use strict";','  "use strict";\n  /* UNRELATED_DELTA 25% */');
    const expected=baseline.get(file).replace('  "use strict";','  "use strict";\n  /* UNRELATED_DELTA 25% */');
    assert.ok(inverse(source,file)===expected);
    assert.notEqual(hash(inverse(source,file)),hash(baseline.get(file)));
  });
  test(file+': inverse is idempotent',()=>{
    const once=inverse(current.get(file),file);assert.equal(inverse(once,file),once);
  });
  test(file+': no owned signals means foreign source remains a no-op',()=>{
    const source='const custom = "freePromptGallery.taxonomy.fake";\n';
    assert.equal(inverse(source,file),source);
  });
}
for(const[rowIndex,row]of fixture.records.entries()){
  test('record-'+rowIndex+': partial application throws, never quietly strips remaining owned deltas',()=>{
    reject(current.get(row.file).replace(part(row),row.file===i18n?'':row.before),row.file);
  });
  test('record-'+rowIndex+': changed bytes inside an owned function/block throw',()=>{
    const owned=part(row),changed=owned.replace('freePromptGallery','unreviewedGallery');
    assert.notEqual(changed,owned);reject(current.get(row.file).replace(owned,changed),row.file);
  });
  test('record-'+rowIndex+': duplicate exact owned record throws',()=>{
    reject(current.get(row.file)+'\n'+part(row),row.file);
  });
}
for(const file of files){
  test(file+': reordered complete records throw',()=>{
    const rows=fixture.records.filter(row=>row.file===file),a=part(rows[0]),b=part(rows[1]);
    const changed=current.get(file).replace(a,'GSC_SWAP_MARKER').replace(b,a).replace('GSC_SWAP_MARKER',b);
    reject(changed,file);
  });
  test(file+': detached complete record outside its source slot throws',()=>{
    const owned=file===portal?fixture.records[0].after:combine;
    reject(current.get(file).replace(owned,'')+'\n'+owned,file);
  });
}
test('portal: helper detached from its filter owner throws',()=>{
  reject(current.get(portal).replace('  function freePromptGalleryFilterFields(catalog) {','  function detachedFilter(catalog) {'),portal);
});
test('portal: render loading condition moved to a foreign function throws',()=>{
  reject(current.get(portal).replace('  function renderFreePromptGallery(page, context) {','  function foreignRender(page, context) {'),portal);
});
test('portal: helper nested inside its prior owner is not accepted as a valid slot',()=>{
  const owned=fixture.records[0].after;let source=current.get(portal).replace(owned,'');
  const prior=source.indexOf('  function freePromptGalleryListingState('),end=source.indexOf('\n  }\n',prior);
  source=source.slice(0,end)+'\n'+owned+source.slice(end);reject(source,portal);
});
test('portal: changed prior ownership anchor throws',()=>{
  reject(current.get(portal).replace('  function renderFreePromptGallerySaveResult(','  function detachedSaveResult('),portal);
});
test('i18n: complete labels assigned to a foreign locale owner throw',()=>{
  reject(current.get(i18n).replace(part(fixture.records[4]),part(fixture.records[4]).replace('MESSAGES.vi','MESSAGES.fr')),i18n);
});
test('i18n: separated insertion blocks are not directly anchored and throw',()=>{
  reject(current.get(i18n).replace(part(fixture.records[4]),'/* detached block */\n'+part(fixture.records[4])),i18n);
});
test('i18n: changed verification anchor throws',()=>{
  reject(current.get(i18n).replace('  verifyEqualKeysets();','  verifyOtherKeysets();'),i18n);
});
test('i18n: changed block slot anchor throws',()=>{
  reject(current.get(i18n).replace('  function deepFreeze(value) {','  function detachedFreeze(value) {'),i18n);
});
test('foreign filenames are no-ops even when an owned record is malformed',()=>{
  const source=current.get(portal).replace('freePromptGalleryTaxonomyLabel','BROKEN');
  for(const file of ['portal.js','static/portal/integration.js','foreign'])assert.equal(inverse(source,file),source);
});

const labels={
  vi:['Bán hàng','Mạng xã hội','Đang tải thư viện câu lệnh…','Đã sao chép câu lệnh.'],
  en:['Sales','Social media','Loading the Prompt Library…','Prompt copied.'],
  zh:['销售','社交媒体','正在加载提示词库…','已复制提示词。']
};
for(const locale of ['vi','en','zh']){
  const approved=fixture.snapshots[locale];
  test('snapshot-'+locale+': exact owned additions from real proposal blocks have independent native literal labels',()=>{
    const messages={vi:{},en:{},zh:{}},context=vm.createContext({MESSAGES:messages,verifyEqualKeysets(){}});
    for(const row of fixture.records.filter(row=>row.file===i18n))vm.runInContext(row.after,context);
    const actual=messages[locale];
    assert.deepEqual(['freePromptGallery.taxonomy.goal.sell','freePromptGallery.taxonomy.platform.social','freePromptGallery.feedback.loading','freePromptGallery.feedback.copied'].map(key=>actual[key]),labels[locale]);
    const legacy=['legacy.existing','客户原文 25%'];
    assert.deepEqual(snapshot([legacy,...Object.entries(actual)],locale),[legacy]);
  });
  test('snapshot-'+locale+': unknown pairs preserve identity/order/bytes and frozen input is never mutated',()=>{
    const left=Object.freeze(['freePromptGallery.taxonomy.fake','α\r\n25%']);
    const middle=Object.freeze(['freePromptGallery.feedback.custom',{text:'CUSTOMER_UNCHANGED'}]);
    const right=Object.freeze(['other.foreign','<b>literal</b>']);
    const pairs=approved.map(pair=>Object.freeze([...pair]));
    const input=Object.freeze([left,...pairs.slice(0,16),middle,...pairs.slice(16),right]);
    const before=JSON.stringify(input),result=snapshot(input,locale);
    assert.deepEqual(result,[left,middle,right]);assert.equal(result[0],left);assert.equal(result[1],middle);assert.equal(result[2],right);
    assert.equal(JSON.stringify(input),before);assert.equal(snapshot(result,locale),result);
  });
  test('snapshot-'+locale+': no owned keys returns the original array identity',()=>{
    const pairs=[['freePromptGallery.feedback.notOwned','KEEP'],['other.key','UNCHANGED']];
    assert.equal(snapshot(pairs,locale),pairs);
  });
  test('snapshot-'+locale+': partial set throws',()=>{
    assert.throws(()=>snapshot(approved.slice(0,-1),locale),/snapshot complete/);
  });
  test('snapshot-'+locale+': changed locale value throws',()=>{
    const pairs=approved.map(pair=>[...pair]);pairs[0][1]+=' UNREVIEWED';
    assert.throws(()=>snapshot(pairs,locale),/exact locale value/);
  });
  test('snapshot-'+locale+': duplicate throws',()=>{
    assert.throws(()=>snapshot([...approved,approved[0]],locale),/snapshot complete|snapshot unique/);
  });
  test('snapshot-'+locale+': reordered complete set throws',()=>{
    const pairs=[...approved];[pairs[0],pairs[1]]=[pairs[1],pairs[0]];
    assert.throws(()=>snapshot(pairs,locale),/insertion order/);
  });
  test('snapshot-'+locale+': malformed owned pair shape throws before removing keys',()=>{
    const pairs=approved.map(pair=>[...pair]);pairs[0].push('EXTRA');
    assert.throws(()=>snapshot(pairs,locale),/pair shape/);
    pairs[0]={0:approved[0][0],1:approved[0][1]};assert.throws(()=>snapshot(pairs,locale),/pair shape/);
  });
  test('snapshot-'+locale+': another supported locale cannot silently remove these labels',()=>{
    assert.throws(()=>snapshot(approved,locale==='vi'?'en':'vi'),/exact locale value/);
  });
}
test('snapshot: foreign locale is rejected, including when there are no owned keys',()=>{
  assert.throws(()=>snapshot(fixture.snapshots.vi,'fr'),/input\/locale/);
  assert.throws(()=>snapshot([],'fr'),/input\/locale/);
});
