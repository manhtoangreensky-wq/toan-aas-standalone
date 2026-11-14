import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {historyHistoricalSnapshot,historyHistoricalPortalSource} from './chat-history-snapshot.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-context-cards-turn-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
const hashes={vi:'9e393ede0e0baf0792e7adea30867ce04400a67b7b8bf59b4e36404698d47e6c',en:'5a02a40eb71600c6318236e29556f4126cacd05a1e06549be149d168f7d09cde',zh:'a74ceef8894a6569a34699b8fd1eb007349ecd4f1baae5b2faf569df7c506b08'};
assert.equal(keys.size,16);
export function cardsTurnHistoricalSnapshot(entries,locale){
  entries=historyHistoricalSnapshot(entries,locale);
  assert.ok(hashes[locale]);
  const scoped=entries.filter(([key])=>/^chat(?:ContextCards|TurnList)Ui/.test(key));
  if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,'Unreviewed Chat cards/turn copy: unknown key');
  assert.equal(added.length,16,'Unreviewed Chat cards/turn copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat cards/turn copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','6a51975654cfb30ae228bfef9064ac3141d53081:static/portal/portal.js'],{cwd:root,encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const spans=[
  ['  function renderChatWorkspaceDetail(page, context) {','\n  // Analytics Workspace','b76f3571fe51a6a390ffdf23eebd3221edc6f94e2f240272a0eff2d02dd37320'],
  ['  function renderChatContextKindOptions(value) {','  function chatWorkspaceTurnLabel(','68b07c970cad420d6223130ed2d369b4ff000486975c64658da5a039811aaa02']
];
export function cardsTurnHistoricalPortalSource(value){
  let source=historyHistoricalPortalSource(value).replace(/\r\n/g,'\n');
  for(const[start,end,expected]of spans){
    assert.equal(source.split(start).length-1,1,'Unreviewed Chat cards/turn source boundary');
    const a=source.indexOf(start),b=source.indexOf(end,a),oa=original.indexOf(start),ob=original.indexOf(end,oa);
    assert.ok(a>=0&&b>a&&oa>=0&&ob>oa,'Unreviewed Chat cards/turn source boundary');
    const part=source.slice(a,b),old=original.slice(oa,ob);
    // Older marker-free source stays byte-exact for the existing finite gates.
    const belongs=start.includes('renderChatContextKindOptions')||/chat(?:ContextCards|TurnList)Ui/.test(part);
    if(part!==old&&belongs){
      assert.equal(hash(part),expected,'Unreviewed Chat cards/turn source');
      source=source.slice(0,a)+old+source.slice(b);
    }
  }
  return source;
}
