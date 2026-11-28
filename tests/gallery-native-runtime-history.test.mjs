import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {galleryNativeRuntimeHistoricalSource as inverse} from './helpers/gallery-native-runtime-historical.mjs';
import {authReturnHistoricalSource} from './helpers/auth-return-historical.mjs';
import {documentNaturalHistoricalSource} from './helpers/document-natural-copy-historical.mjs';

const base='29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef',integration='static/portal/integration.js';
const lf=value=>value.replace(/\r\n/g,'\n'),sha=value=>createHash('sha256').update(value).digest('hex');
const read=name=>JSON.parse(fs.readFileSync(new URL('./fixtures/'+name,import.meta.url),'utf8'));
const transport=read('gallery-native-transport-history.json'),backend=read('gallery-native-backend-history.json');
const files=[integration,'copyfast_free_prompt_gallery.py','copyfast_memory.py'];
const records=file=>file===integration?transport.records:backend.records.filter(row=>row.file===file);
const baseline=new Map(files.map(file=>[file,lf(execFileSync('git',['show',base+':'+file],{encoding:'utf8',maxBuffer:12e6}))]));
const physical=new Map(files.map(file=>[file,authReturnHistoricalSource(documentNaturalHistoricalSource(lf(fs.readFileSync(new URL('../'+file,import.meta.url),'utf8')),file),file)]));
const current=new Map(files.map(file=>{
  let source=baseline.get(file);
  for(const row of records(file)){
    assert.equal(source.split(row.before).length,2,'one independent BASE/proposal anchor');
    source=source.replace(row.before,()=>row.after);
  }
  return[file,source];
}));
const reject=(source,file)=>assert.throws(()=>inverse(source,file),/Unreviewed Gallery native runtime history/);
const reverseFrom=(file,index)=>{
  let source=current.get(file);
  const rows=records(file);
  for(let i=rows.length-1;i>index;i--)source=source.replace(rows[i].after,()=>rows[i].before);
  return source;
};
const prefix='/* UNKNOWN α 客户 25% */\r\n',suffix='\n# UNKNOWN CUSTOMER <b>literal</b>\r\n';

for(const file of files){
  test(file+': independently read immutable Git BASE is an exact no-op',()=>{
    assert.equal(inverse(baseline.get(file),file),baseline.get(file));
  });
  test(file+': full raw current source is exactly the approved proposal construction',()=>{
    assert.equal(sha(physical.get(file)),sha(current.get(file)));
  });
  test(file+': inverse of actual full source equals independently read immutable Git BASE',()=>{
    assert.ok(inverse(physical.get(file),file)===baseline.get(file));
  });
  test(file+': inverse is idempotent',()=>{
    const once=inverse(current.get(file),file);assert.equal(inverse(once,file),once);
  });
  test(file+': unknown prefix and suffix retain exact bytes',()=>{
    assert.ok(inverse(prefix+current.get(file)+suffix,file)===prefix+baseline.get(file)+suffix);
  });
  test(file+': unrelated interior delta remains visible instead of being masked',()=>{
    const anchor=file===integration?'  "use strict";':'from __future__ import annotations';
    const addition=anchor+'\n# UNKNOWN_INTERIOR 客户原文 25%';
    const source=current.get(file).replace(anchor,()=>addition);
    const expected=baseline.get(file).replace(anchor,()=>addition);
    assert.ok(inverse(source,file)===expected);
    assert.notEqual(sha(expected),sha(baseline.get(file)));
  });
  test(file+': older and arbitrary no-signal input retains identity/bytes',()=>{
    const source='unrelated customer text: α\r\n自由内容 25%\n';assert.equal(inverse(source,file),source);
  });
}

for(const file of files){
  const rows=records(file);
  for(const[index,row]of rows.entries()){
    const stage=index===0?current.get(file):reverseFrom(file,index),label=file+' record-'+index;
    test(label+': deleting the exact owned record fails closed',()=>{
      reject(stage.replace(row.after,''),file);
    });
    test(label+': reverting only one record fails closed',()=>{
      reject(stage.replace(row.after,()=>row.before),file);
    });
    test(label+': changed bytes inside the approved record fail closed',()=>{
      reject(stage.replace(row.after,()=>row.after.replace('\n','\n/* UNREVIEWED_IN_OWNED_RECORD */\n')),file);
    });
    test(label+': changed owned token cannot be silently normalized away',()=>{
      const at=Math.floor(row.after.length/2),changed=row.after.slice(0,at)+'UNREVIEWED'+row.after.slice(at+1);
      reject(stage.replace(row.after,()=>changed),file);
    });
    test(label+': duplicate exact record fails closed',()=>{
      reject(stage+'\n'+row.after,file);
    });
    test(label+': detached record before its owner fails closed',()=>{
      reject(row.after+'\n'+stage.replace(row.after,''),file);
    });
    test(label+': foreign previous slot owner fails closed',()=>{
      reject(stage.replace(row.slot.previous,()=> 'UNREVIEWED_OWNER'+row.slot.previous.slice(1)),file);
    });
  }
}

for(const file of files){
  const rows=records(file);
  for(let i=1;i<rows.length;i++){
    test(file+': partial proposal round ending at '+i+' fails closed',()=>{
      let source=baseline.get(file);
      for(const row of rows.slice(0,i))source=source.replace(row.before,()=>row.after);
      reject(source,file);
    });
  }
}
test('integration: complete R1A, R2 and first cache rounds are not accepted as final',()=>{
  for(const count of [7,9,10]){
    let source=baseline.get(integration);
    for(const row of transport.records.slice(0,count))source=source.replace(row.before,()=>row.after);
    reject(source,integration);
  }
});
test('backend fixture records retain server proposal provenance and independent before/after hashes',()=>{
  assert.equal(backend.base_sha,base);
  assert.equal(backend.conversation_id,'bffacabe-abf0-40df-92c2-bdf9a9b6f0b3');
  assert.equal(backend.proposal,'gsc-server-code-r1a/result.raw.json');
  assert.equal(backend.records.length,7);
  for(const[rowIndex,row]of backend.records.entries()){
    assert.equal(row.proposal_record,rowIndex);
    assert.equal(sha(row.before),row.before_lf_sha256);
    assert.equal(sha(row.after),row.after_lf_sha256);
  }
});
test('foreign filenames are no-ops even when owned runtime records are malformed',()=>{
  const source=physical.get(integration).replace('freePromptGalleryLocaleOwner','BROKEN_OWNER');
  for(const file of ['foreign','integration.js','static/portal/portal.js','copyfast_gallery_locale.py']){
    assert.equal(inverse(source,file),source);
  }
});
test('backend: imports moved into a foreign function are not an approved top-level import slot',()=>{
  const row=backend.records[0],file=row.file;
  const source=current.get(file).replace(row.after,'')+'\ndef detached():\n    '+row.after;
  reject(source,file);
});
test('backend: complete record nested before the end of its prior body fails closed',()=>{
  const row=backend.records[5],file=row.file;
  let source=current.get(file).replace(row.after,'');
  source=source.replace(row.slot.previous_end,()=>row.after+'\n'+row.slot.previous_end);
  reject(source,file);
});
test('backend: exact partial save record moved under an unrelated top-level owner fails closed',()=>{
  const row=backend.records[6],file=row.file;
  let source=current.get(file).replace(row.after,'');
  const following=source.indexOf(row.slot.following,source.indexOf('async def create_note('));
  source=source.slice(0,following)+'def unrelated_owner():\n'+row.after+'\n'+source.slice(following);
  reject(source,file);
});
test('runtime inverse rejects non-string input for every supported target',()=>{
  for(const file of files)assert.throws(()=>inverse(null,file),/string source/);
});
