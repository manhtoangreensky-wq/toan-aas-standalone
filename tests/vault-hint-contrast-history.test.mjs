import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {resizeSubtitleWrapHistoricalThemeSource as composed} from './helpers/image-resize-subtitle-wrap-snapshot.mjs';
import {vaultHintContrastHistoricalCss as newest} from './helpers/vault-hint-contrast-snapshot.mjs';
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),file='static/portal/portal-theme.css',BASE='5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5';
const lf=value=>value.replace(/\r\n/g,'\n'),hash=value=>createHash('sha256').update(value).digest('hex'),count=(value,part)=>value.split(part).length-1;
const authorityRaw=fs.readFileSync(new URL('./fixtures/vault-hint-contrast-reviewed.json',import.meta.url)),authority=JSON.parse(authorityRaw),edit=authority.canonicalChanges[0];
assert.equal(hash(authorityRaw),'c58f59c1da9f1fdeff9582d2d05917d87d92e67cdf91a685bb65037898d44f7b');
const wrapRaw=fs.readFileSync(new URL('./fixtures/image-resize-subtitle-wrap-reviewed.json',import.meta.url)),wrapFixture=JSON.parse(wrapRaw),wrap=wrapFixture.proposal.changes[0];
assert.equal(hash(wrapRaw),'48d3a038e51e355b15d24026d7585c09b42477634f424985f9e2c7176e6cfd50');
const base=lf(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:8e6})),current=lf(fs.readFileSync(path.join(ROOT,file),'utf8')),wrapAddition=wrap.new.slice(wrap.old.length);
assert.equal(count(base,wrap.new),1);const expected=base.replace(wrapAddition,'');
test('strict newest CSS leaf composes OLD/NEW idempotently while preserving unknown outside bytes and rejecting owned mutations',()=>{
 assert.equal(hash(base),authority.baselineLfSha256);assert.equal(hash(current),authority.candidateLfSha256);assert.equal(newest(current,file),base);assert.equal(composed(base),expected);assert.equal(composed(current),expected);assert.equal(composed(composed(current)),expected);
 const first='\r\n/* CUSTOMER media studio Facebook TikTok */\r\n',last='\r\n.customer-unknown { color: rebeccapurple; }\r\n';
 for(const value of [base,current])assert.equal(composed(first+value+last),first+expected+last);assert.ok(composed(current+last).endsWith(last));assert.notEqual(composed(current+last),expected);assert.equal(composed(first+last),first+last);
 assert.throws(()=>composed(current.replace(edit.new,edit.new.replace('color: var(--portal-ink);','color: red;'))),/Unreviewed Vault hint contrast/);
});
test('the original Resize wrapping typeof error is preserved before newest CSS composition',()=>{
 for(const value of [null,undefined,17,{}])assert.throws(()=>composed(value),/Unreviewed Resize subtitle wrapping/);
 assert.throws(()=>newest(null,file),/Unreviewed Vault hint contrast/);assert.equal(composed('/* marker-free OLD stylesheet */'),'/* marker-free OLD stylesheet */');
});
test('prior wrapping malformed-rule vectors keep their original error identity after exact newest-source staging',()=>{
 const historical=newest(current,file);assert.equal(historical,base);
 for(const malformed of [historical.replace(wrapAddition,wrapAddition.replace('white-space: normal;','white-space: nowrap;')),historical+'\n'+wrapAddition,historical.replace(wrap.new,wrap.old)+'\n'+wrapAddition]){
  assert.equal(newest(malformed,file),malformed,'Marker-free OLD style remains owned by its original comparator');assert.throws(()=>composed(malformed),/Unreviewed Resize subtitle wrapping/);
 }
});
