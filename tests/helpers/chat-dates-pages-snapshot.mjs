import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const keys=new Set(['chatPagesUiAria','chatPagesUiSummary','chatPagesUiPrevious','chatPagesUiNext']);
const hashes={vi:'95316d9045e02b8720eefcfb267fccebc56cc423ed0987eb1baeb591c0bc17d2',en:'adb874b32ff8a64f7c1c4fa6bf551f973f9d220e2b87f4fddc9b371a48b8d99a',zh:'2f0c41525df9bc22d05a9404249b148cd9acb0dff1d831f160987a4d8e046d7b'};
const hash=value=>createHash('sha256').update(value).digest('hex');
export function datePagesHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const added=entries.filter(([key])=>keys.has(key));if(!added.length)return entries;
  assert.equal(added.length,4,'Unreviewed Chat dates/pages copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat dates/pages copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','7e30dd95d2d5652281f9462a73f7ba08b7801f59:static/portal/portal.js'],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const spans=[
  ['  function renderChatWorkspaceCards(items, context) {','  function renderChatWorkspace(page, context) {','b249d9fe72603b1f86aa8eef07df86defb6ff52c74ac573e0114178c8bd6cf35'],
  ['  function renderChatWorkspacePagination(listing, enabled) {','  function renderChatWorkspaceTags(','bf18f964b2e3e705c958ac4e21303b894fe84e6c2d5cda073ccd1068b54f486e']
];
// Normalize only complete, hash-reviewed spans for older test scopes.
export function datePagesHistoricalPortalSource(value){
  let source=value.replace(/\r\n/g,'\n');
  for(const [start,end,expected]of spans){
    const a=source.indexOf(start),b=source.indexOf(end,a),oa=original.indexOf(start),ob=original.indexOf(end,oa);
    assert.ok(a>=0&&b>a&&oa>=0&&ob>oa,'Unreviewed Chat dates/pages source boundary');
    const current=source.slice(a,b),old=original.slice(oa,ob);
    if(current===old)continue;
    assert.equal(hash(current),expected,'Unreviewed Chat dates/pages source');
    source=source.slice(0,a)+old+source.slice(b);
  }
  return source;
}
