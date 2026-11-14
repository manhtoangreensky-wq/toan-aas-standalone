import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';

const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-cards-customer-copy-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi));
const hashes={vi:'cdc7f205d4715cc1cc4c43b100bf050981b6dc3621b09c035b104d2eb0452f5b',en:'b350e6202361143aa20105e1da1e2fbab84558b74ad56a211520ab8bebb217aa',zh:'a2d8ef008943e57c54d92752e423d1c3a9b5a3e942d32b9893a320db2f5bb76c'};
const hash=text=>createHash('sha256').update(text).digest('hex');
export function chatCardsHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const added=entries.filter(([key])=>keys.has(key));
  if(!added.length)return entries;
  assert.equal(added.length,20,'Unreviewed Chat cards copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat cards copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','398cea1c4f6f6f256c646fa382a78563e66b8939:static/portal/portal.js'],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const spans=[
  ['  function renderChatWorkspaceBoundary(context) {','  function renderChatWorkspaceCards(','af44a80c3b067a7d3910270fdb203c7936ac5166c9f6957cb796e9e187debe15'],
  ['  function renderChatWorkspaceCards(items, context) {','  function renderChatWorkspace(page, context) {','f13cc1bbcecfc2f43ba72f7ea76e898492367a8b58dafc80c06d39bbae7eb170']
];
// Restore only complete, hash-reviewed worker spans for historical scopes.
// No regex over arbitrary/customer text, no accepting an unknown new fragment.
export function chatCardsHistoricalPortalSource(value){
  let source=value.replace(/\r\n/g,'\n');
  for(const [start,end,expected]of spans){
    const a=source.indexOf(start),b=source.indexOf(end,a);
    const oa=original.indexOf(start),ob=original.indexOf(end,oa);
    assert.ok(a>=0&&b>a&&oa>=0&&ob>oa,'Unreviewed Chat cards source boundary');
    const current=source.slice(a,b),old=original.slice(oa,ob);
    if(current===old)continue;
    assert.equal(hash(current),expected,'Unreviewed Chat cards source');
    source=source.slice(0,a)+old+source.slice(b);
  }
  return source;
}
