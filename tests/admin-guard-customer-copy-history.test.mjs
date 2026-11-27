import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
import {adminGuardCustomerCopyHistoricalSource as inverse,adminGuardCustomerCopyHistoricalSnapshot as snapshot} from './helpers/admin-guard-customer-copy-historical.mjs';

const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/admin-guard-customer-copy-history.json',import.meta.url),'utf8'));
const base='5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f';
const files=['static/portal/portal.js','static/portal/portal-i18n.js'];
const lf=value=>value.replace(/\r\n/g,'\n'),hash=value=>createHash('sha256').update(value).digest('hex');
const baseline=new Map(files.map(file=>[file,lf(execFileSync('git',['show',base+':'+file],{encoding:'utf8',maxBuffer:12e6}))]));
const current=new Map(files.map(file=>{
  let source=baseline.get(file);
  for(const row of fixture.records.filter(row=>row.file===file)){
    assert.equal(source.split(row.before).length,2,'Independent forward proposal anchor');
    source=source.replace(row.before,()=>row.after);
  }
  return[file,source];
}));
const owners=file=>fixture.owners.filter(row=>row.file===file);
const physical=file=>lf(fs.readFileSync(new URL('../'+file,import.meta.url),'utf8'));
const reject=(source,file)=>assert.throws(()=>inverse(source,file),/Unreviewed Admin guard customer copy history/);
function recordPiece(row){
  if(row.after==='')return fixture.owners.find(owner=>owner.file===row.file&&owner.name==='renderSupportAdminBase').after;
  return row.after;
}
function recordBefore(row){
  if(row.after==='')return fixture.owners.find(owner=>owner.file===row.file&&owner.name==='renderSupportAdminBase').before;
  return row.before;
}

for(const file of files){
  test(file+': immutable Git BASE is a byte-exact no-op',()=>{
    assert.equal(inverse(baseline.get(file),file),baseline.get(file));
  });
  test(file+': exact22 proposal construction equals raw physical current source and pinned hash',()=>{
    const source=physical(file),metadata=fixture.application_sources.find(row=>row.file===file);
    assert.equal(hash(source),metadata.current_lf_sha256);
    assert.ok(source===current.get(file));
    assert.equal(hash(baseline.get(file)),metadata.base_lf_sha256);
  });
  test(file+': actual current inverse equals independently read Git BASE',()=>{
    assert.ok(inverse(physical(file),file)===baseline.get(file));
  });
  test(file+': projection is idempotent',()=>{
    const once=inverse(current.get(file),file);assert.equal(inverse(once,file),once);
  });
  test(file+': unknown prefix/suffix/customer bytes are preserved',()=>{
    const prefix='/* UNKNOWN α 客户 <b>literal</b> 25% */\r\n',suffix='\n/* ADMIN_SUPPORT_COPY_CUSTOM untouched */\r\n';
    assert.ok(inverse(prefix+current.get(file)+suffix,file)===prefix+baseline.get(file)+suffix);
  });
  test(file+': unrelated interior source mutation remains visible to historical pins',()=>{
    const anchor='  "use strict";',addition='\n  /* UNKNOWN_CUSTOMER_TEXT 客户原文 25% */';
    const actual=inverse(current.get(file).replace(anchor,anchor+addition),file);
    const expected=baseline.get(file).replace(anchor,anchor+addition);
    assert.ok(actual===expected);assert.notEqual(hash(actual),hash(baseline.get(file)));
  });
  test(file+': no-signal arbitrary source remains unchanged',()=>{
    const source='const customer = "ADMIN_SUPPORT_COPY_CUSTOM";\r\n客户文字';
    assert.equal(inverse(source,file),source);
  });
}
for(const[index,row]of fixture.records.entries()){
  const file=row.file,piece=recordPiece(row),label='record-'+index+' '+row.task;
  test(label+': individual old/new partial mixture fails closed',()=>{
    reject(current.get(file).replace(piece,()=>recordBefore(row)),file);
  });
  test(label+': changed approved copy/removal owner fails closed',()=>{
    const at=Math.floor(piece.length/2),changed=piece.slice(0,at)+'UNREVIEWED_BAD_COPY'+piece.slice(at+1);
    reject(current.get(file).replace(piece,()=>changed),file);
  });
  test(label+': deleting the approved record/owner fails closed',()=>{
    reject(current.get(file).replace(piece,''),file);
  });
  test(label+': duplicating an approved record/owner fails closed',()=>{
    reject(current.get(file)+'\n'+piece,file);
  });
  test(label+': detached record/owner fails closed',()=>{
    reject(piece+'\n'+current.get(file).replace(piece,''),file);
  });
}
for(const row of fixture.owners){
  const file=row.file,label=row.name;
  test(label+': foreign enclosing owner at the same approved slot fails closed',()=>{
    const wrapped='  function foreignAgcOwner() {\n'+row.after+'  }\n';
    reject(current.get(file).replace(row.after,()=>wrapped),file);
  });
  test(label+': contextual slot gap rejects a foreign enclosing conditional block',()=>{
    reject(current.get(file).replace(row.after,()=> '  if (foreignCondition) {\n'+row.after+'  }\n'),file);
  });
  test(label+': contextual slot gap preserves comments and quoted declaration-like text',()=>{
    const addition='  /* {\n  function foreignAgcOwner() {\n  const foreign = 1;\n  } */\r\n  "class foreign { }";\n';
    const expected=baseline.get(file).replace(row.before,()=>addition+row.before);
    assert.ok(inverse(current.get(file).replace(row.after,()=>addition+row.after),file)===expected);
  });
  test(label+': exact owner moved before its previous declaration fails slot guard',()=>{
    reject(row.after+'\n'+current.get(file).replace(row.after,''),file);
  });
  test(label+': previous owner identity cannot be altered',()=>{
    reject(current.get(file).replace(row.slot.previous,()=> 'BROKEN_OWNER'+row.slot.previous.slice(1)),file);
  });
  test(label+': following owner identity cannot be altered',()=>{
    reject(current.get(file).replace(row.slot.following,()=> 'BROKEN_OWNER'+row.slot.following.slice(1)),file);
  });
  test(label+': owner declaration cannot be duplicated independently',()=>{
    reject(current.get(file)+'\n'+row.slot.declaration,file);
  });
  test(label+': unknown edit inside a frozen owner is not masked',()=>{
    const changed=row.after.replace('\n','\n/* UNKNOWN_INSIDE_OWNER */\n');
    reject(current.get(file).replace(row.after,()=>changed),file);
  });
}
for(const row of fixture.owners.filter(row=>row.slot.kind==='function')){
  test(row.name+': contextual slot gap rejects owner nested before prior function closes',()=>{
    let source=current.get(row.file).replace(row.after,'');
    const previous=source.indexOf(row.slot.previous),close=source.indexOf('\n  }\n',previous);
    assert(close>previous);
    source=source.slice(0,close)+'\n'+row.after+source.slice(close);
    reject(source,row.file);
  });
}
for(const declaration of ['function foreignAgcOwner() {}','const foreignAgcOwner = 1;','let foreignAgcOwner = 1;','class foreignAgcOwner {}']){
  test('contextual slot gap rejects intervening top-level '+declaration.split(' ')[0]+' declaration',()=>{
    const row=fixture.owners[0];
    reject(current.get(row.file).replace(row.after,()=> '  '+declaration+'\n'+row.after),row.file);
  });
}
for(const file of files){
  const rows=owners(file);
  test(file+': reordered complete approved owners fail closed',()=>{
    const a=rows[0].after,b=rows[1].after;
    const changed=current.get(file).replace(a,'AGC_SWAP_SENTINEL').replace(b,()=>a).replace('AGC_SWAP_SENTINEL',()=>b);
    reject(changed,file);
  });
  test(file+': every incomplete forward proposal round fails closed',()=>{
    const records=fixture.records.filter(row=>row.file===file);
    let source=baseline.get(file);
    for(const row of records.slice(0,-1)){
      source=source.replace(row.before,()=>row.after);
      reject(source,file);
    }
  });
}
test('action guard condition mutation cannot be hidden by the historical projection',()=>{
  const file=files[0],row=fixture.owners.find(row=>row.name==='actionBlockReason');
  const changed=row.after.replace('context.session.authenticated !== true','context.session.authenticated === true');
  assert.notEqual(changed,row.after,'Must change an actual guard condition, not a test label');
  reject(current.get(file).replace(row.after,()=>changed),file);
});
test('Support removal cannot become an empty-string inverse or an arbitrary added boundary',()=>{
  const file=files[0],row=fixture.owners.find(row=>row.name==='renderSupportAdminBase');
  const changed=row.after.replace('</article>','<section>UNREVIEWED_BOUNDARY</section></article>');
  assert.notEqual(changed,row.after);
  reject(current.get(file).replace(row.after,()=>changed),file);
});
test('all22 original pairs and owner hashes retain exact source provenance',()=>{
  assert.equal(fixture.records.length,22);
  assert.deepEqual(fixture.provenance.map(row=>row.task),['AGC-ACTION','AGC-SUPPORT','AGC-OPERATIONS']);
  for(const row of [...fixture.records,...fixture.owners]){
    assert.equal(hash(row.before),row.before_lf_sha256);assert.equal(hash(row.after),row.after_lf_sha256);
  }
});
test('foreign filename never strips approved or malformed AGC source',()=>{
  const source=current.get(files[0]).replace('actionBlockReason','BROKEN',1);
  for(const file of ['portal.js','foreign','static/portal/integration.js'])assert.equal(inverse(source,file),source);
});
test('non-string input fails before target filtering',()=>{
  assert.throws(()=>inverse(null,files[0]),/string source/);
  assert.throws(()=>inverse(null,'foreign'),/string source/);
});

const approved=JSON.parse(fs.readFileSync(new URL('./fixtures/admin-guard-customer-copy.json',import.meta.url),'utf8'));
const ownedKeys=new Set([
  ...approved.support.map(([key])=>'adminSupport.'+key),
  ...approved.operations.map(([key])=>'adminOperations.'+key),
  ...approved.action.map(([key])=>'actionBlockReason.'+key)
]);
const dictionaries=script=>{
  const context=vm.createContext({});vm.runInContext(script,context);
  return context.TOANAASI18n.messages;
};
const oldMessages=dictionaries(baseline.get(files[1])),newMessages=dictionaries(physical(files[1]));
for(const locale of ['vi','en','zh']){
  const oldEntries=Object.entries(oldMessages[locale]),entries=Object.entries(newMessages[locale]);
  const owned=entries.filter(([key])=>ownedKeys.has(key));
  test('snapshot-'+locale+': actual full dictionary returns the independently executed Git BASE dictionary',()=>{
    assert.equal(owned.length,31);assert.equal(oldEntries.filter(([key])=>ownedKeys.has(key)).length,19);
    assert.deepEqual(snapshot(entries,locale),oldEntries);
  });
  test('snapshot-'+locale+': exact old input and twice-projected input retain array identity',()=>{
    assert.equal(snapshot(oldEntries,locale),oldEntries);
    const once=snapshot(entries,locale);assert.equal(snapshot(once,locale),once);
  });
  test('snapshot-'+locale+': unknown customer pairs keep identity/order and frozen input is not mutated',()=>{
    const first=Object.freeze(['actionBlockReason.customer',{text:'客户原文 <safe> 25%'}]);
    const last=Object.freeze(['adminSupport.foreign','α\r\nUNCHANGED']);
    const input=Object.freeze([first,...entries.map(row=>Object.freeze([...row])),last]);
    const before=JSON.stringify(input),result=snapshot(input,locale);
    assert.deepEqual(result,[first,...oldEntries,last]);assert.equal(result[0],first);
    assert.equal(result.at(-1),last);assert.equal(JSON.stringify(input),before);
  });
  test('snapshot-'+locale+': missing owned addition fails instead of partially stripping keys',()=>{
    assert.throws(()=>snapshot(entries.filter(([key])=>key!=='actionBlockReason.telegramUnavailable'),locale),/snapshot complete\/order/);
  });
  test('snapshot-'+locale+': mixed old/new values fail closed',()=>{
    const key='adminSupport.guard.body',mixed=entries.map(row=>row[0]===key?[key,oldMessages[locale][key]]:row);
    assert.throws(()=>snapshot(mixed,locale),/exact locale value/);
  });
  test('snapshot-'+locale+': changed unknown value of an owned old row fails closed',()=>{
    const changed=oldEntries.map(row=>row[0]==='adminSupport.guard.body'?[row[0],'UNREVIEWED']:row);
    assert.throws(()=>snapshot(changed,locale),/exact locale value/);
  });
  test('snapshot-'+locale+': duplicated owned key fails closed',()=>{
    assert.throws(()=>snapshot([...entries,owned[0]],locale),/snapshot unique/);
  });
  test('snapshot-'+locale+': reordered owned rows fail closed',()=>{
    const rows=[...entries],a=rows.indexOf(owned[0]),b=rows.indexOf(owned[1]);
    [rows[a],rows[b]]=[rows[b],rows[a]];
    assert.throws(()=>snapshot(rows,locale),/snapshot complete\/order/);
  });
  test('snapshot-'+locale+': malformed pair fails before normalization',()=>{
    const rows=entries.map(row=>row===owned[0]?[...row,'EXTRA']:row);
    assert.throws(()=>snapshot(rows,locale),/snapshot pair shape/);
  });
  test('snapshot-'+locale+': foreign locale values cannot be accepted',()=>{
    assert.throws(()=>snapshot(entries,locale==='vi'?'en':'vi'),/exact locale value/);
  });
  test('snapshot-'+locale+': arbitrary unknown-only snapshot stays unchanged',()=>{
    const rows=[['actionBlockReason.customer','UNCHANGED'],['adminOperations.custom',{text:'25%'}]];
    assert.equal(snapshot(rows,locale),rows);
  });
}
test('snapshot: unsupported locale fails even for empty input',()=>{
  assert.throws(()=>snapshot([],'fr'),/snapshot input\/locale/);
});
