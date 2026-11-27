import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {authReturnHistoricalSource as inverse} from './helpers/auth-return-historical.mjs';

const base='fc9aef439d8fe7ecb00a2c68a167dad501f54eb9';
const raw=fs.readFileSync(new URL('./fixtures/auth-return-history.json',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const fixture=JSON.parse(raw),sha=value=>createHash('sha256').update(value).digest('hex');
const fail=/Unreviewed auth return history/,prefix='/* CUSTOMER 自由 α 25% */\r\n',suffix='\r\n/* 客户 <b>& literal */';
test('fixture binds only two approved complete helper pairs and their immutable hashes',()=>{
  assert.equal(sha(raw),'97a8aad3f4b8a0251a80222c7e5af4fe27b1b49e6d1cbfd2dd4f6d19797dfae3');
  assert.equal(fixture.base_sha,base);
  assert.deepEqual(fixture.records.map(row=>row.file),['static/portal/portal-auth.js','static/portal/integration.js']);
  for(const row of fixture.records){
    assert.equal(sha(row.before),row.before_sha256);assert.equal(sha(row.after),row.after_sha256);
  }
});
for(const row of fixture.records){
  const original=execFileSync('git',['show',base+':'+row.file],{encoding:'utf8',maxBuffer:12e6}).replace(/\r\n/g,'\n');
  const current=fs.readFileSync(new URL('../'+row.file,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  test(row.file+': independently read BASE plus exactly one proposal is the current raw source',()=>{
    assert.equal(original.split(row.before).length,2);
    assert.equal(current,original.replace(row.before,()=>row.after));
    assert.equal(inverse(current,row.file),original);
    assert.equal(inverse(original,row.file),original);
    assert.equal(inverse(inverse(current,row.file),row.file),original);
  });
  for(const ending of ['\n','\r\n']){
    const eol=value=>value.replace(/\n/g,ending),source=eol(current),before=eol(original),after=eol(row.after);
    test(row.file+': '+JSON.stringify(ending)+' preserves unknown outside bytes and checkout encoding',()=>{
      assert.equal(inverse(prefix+source+suffix,row.file),prefix+before+suffix);
      const marker=eol(row.previous),delta='\r\n    /* UNKNOWN_INTERIOR 客户文本 25% */';
      assert.equal(inverse(source.replace(marker,()=>marker+delta),row.file),before.replace(marker,()=>marker+delta));
      assert.equal(inverse(source,'foreign.js'),source);
      assert.equal(inverse(prefix+suffix,row.file),prefix+suffix);
    });
    for(const[index,line]of after.split(ending).entries()){
      if(!line.trim())continue;
      test(row.file+': '+JSON.stringify(ending)+' rejects altered helper line '+index,()=>{
        const changed=line.replace(/\S/,'X');
        assert.notEqual(changed,line);
        assert.throws(()=>inverse(source.replace(after,()=>after.replace(line,()=>changed)),row.file),fail);
      });
    }
    const malformed={
      duplicate:source+ending+after,
      moved:after+source.replace(after,''),
      detached:after,
      partial:source.replace(after,()=>after.slice(0,Math.floor(after.length/2))),
      mixed:source+eol(row.before),
      previous:source.replace(row.previous,()=>row.previous.replace('randomKey','unknownOwner')),
      following:source.replace(row.following,()=>row.following.replace(/function \w+/,'function unknownOwner')),
      foreignOwner:source.replace(after,()=>eol('  function unknownOwner() {}\n')+after),
      crossed:source.replace(after,'')+after,
      inline:source.replace(after,()=> '/* displaced */'+after)
    };
    for(const[name,value]of Object.entries(malformed)){
      test(row.file+': '+JSON.stringify(ending)+' rejects '+name,()=>assert.throws(()=>inverse(value,row.file),fail));
    }
  }
}
test('wrong targets and no-signal historical input retain exact identity; nonstrings fail closed',()=>{
  for(const file of ['foreign','portal-auth.js','static/portal/portal.js']){
    assert.equal(inverse(raw,file),raw);
  }
  for(const row of fixture.records){
    assert.equal(inverse('/* old unrelated α\r\n */',row.file),'/* old unrelated α\r\n */');
    assert.throws(()=>inverse(null,row.file),fail);
  }
});
